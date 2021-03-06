#coding: utf-8
from ..extensions import redis_store, user_datastore
import APITaxi_models as models
from APITaxi_utils import influx_db
from APITaxi_utils.pager import pager
from datetime import datetime, timedelta
from time import mktime, time
from flask import current_app
from itertools import compress
from ..extensions import celery
from celery import Task
from influxdb.exceptions import InfluxDBClientError


class cache(Task):
    abstract=True

    def __init__(store_active_taxis):
        store_active_taxis.insee_zupc_dict = dict()

def get_taxis_ids_operators(frequency):
    bound = time() - (models.Taxi._ACTIVITY_TIMEOUT + frequency * 60)
    if frequency <= models.taxis.TaxiRedis._DISPONIBILITY_DURATION:
        for gen_taxi_ids_operator in pager(redis_store.zrangebyscore(
            current_app.config['REDIS_TIMESTAMPS'], bound, time()), page_size=100):
            yield list([t.decode('utf-8') for t in gen_taxi_ids_operator])
    else:
        taxis = []
        for g_keys in pager(redis_store.keys("taxi:*"), page_size=100):
            keys = list(g_keys)
            pipe = redis_store.pipeline()
            for k in keys:
                pipe.hgetall(k)
            for k, v in [v for v in zip(keys, pipe.execute()) if v[1] is not None]:
                for operator, taxi in v.items():
                    if float(taxi.decode('utf-8').split(" ")[0]) >= bound:
                        taxi_id_operator = "{}:{}".format(k[5:].decode('utf-8'), operator.decode('utf-8'))
                        taxis.append(taxi_id_operator)
                if len(taxis) >= 100:
                    yield taxis
                    taxis = []
        if taxis:
            yield taxis

@celery.task(name='store_active_taxis', base=cache)
def store_active_taxis(frequency):
    now = datetime.utcnow()
    map_operateur_insee_nb_active = dict()
    map_operateur_nb_active = dict()
    map_insee_nb_active = dict()
    active_taxis = set()
    prefixed_taxi_ids = []
    convert = lambda d: mktime(d.timetuple())
    hidden_operator = current_app.config.get('HIDDEN_OPERATOR', 'testing_operator')
    for taxi_ids_operator in get_taxis_ids_operators(frequency):
        taxis = dict()
        for tm in models.RawTaxi.get([t.split(':')[0] for t in taxi_ids_operator]):
            for t in tm:
                taxis[t['taxi_id']+':'+t['u_email']] = t
        for taxi_id_operator in taxi_ids_operator:
            taxi_id, operator = taxi_id_operator.split(':')
            if operator == hidden_operator:
                continue
            active_taxis.add(taxi_id)
            taxi_db = taxis.get(taxi_id_operator, None)
            if taxi_db is None:
                current_app.logger.debug('Taxi: {}, not found in database'.format(
                    taxi_id_operator))
                continue
            if 'ads_insee' not in taxi_db:
                current_app.logger.debug('Taxi: {} is invalid'.format(taxi_id))
                continue
#This a cache for insee to zupc.
            if not taxi_db['ads_insee'] in store_active_taxis.insee_zupc_dict:
                zupc = models.ZUPC.query.get(taxi_db['ads_zupc_id'])
                if not zupc:
                    current_app.logger.debug('Unable to find zupc: {}'.format(
                        taxi_db['ads_zupc_id']))
                    continue
                zupc = zupc.parent
                store_active_taxis.insee_zupc_dict[zupc.insee] = zupc
                store_active_taxis.insee_zupc_dict[taxi_db['ads_insee']] = zupc
            else:
                zupc = store_active_taxis.insee_zupc_dict[taxi_db['ads_insee']]
            map_insee_nb_active.setdefault(zupc.insee, set()).add(taxi_id)
            if operator not in map_operateur_insee_nb_active:
                u = user_datastore.find_user(email=operator)
                if not u:
                    current_app.logger.debug('User: {} not found'.format(operator))
                    continue
                map_operateur_insee_nb_active[operator] = dict()
            map_operateur_insee_nb_active[operator].setdefault(zupc.insee, set()).add(taxi_id)
            map_operateur_nb_active.setdefault(operator, set()).add(taxi_id)

    map_operateur_insee_nb_available = dict()
    map_operateur_nb_available = dict()

    available_ids = set()
    for operator, insee_taxi_ids in map_operateur_insee_nb_active.items():
        for insee, taxis_ids in insee_taxi_ids.items():
            for ids in pager(taxis_ids, page_size=100):
                pipe = redis_store.pipeline()
                for id_ in ids:
                    pipe.zscore(current_app.config['REDIS_TIMESTAMPS'],
                                   id_+':'+operator)
                res = compress(ids, pipe.execute())
                map_operateur_insee_nb_available.setdefault(operator, dict()).setdefault(
                    insee, set()).union(set(res))
                available_ids.union(set(res))

    for operateur, taxis_ids in map_operateur_nb_active.items():
        map_operateur_nb_active.setdefault(operateur, set()).union(
            set([t+':'+operateur for t in taxis_ids]).intersection(available_ids
                )
        )


    client = influx_db.get_client(current_app.config['INFLUXDB_TAXIS_DB'])
    to_insert = []
    bucket_size = 100
    def insert(operator, zupc, active, available=False):
        measurement_name = "nb_taxis_every_{}".format(frequency)
        if available:
            measurement_name += '_available'
        to_insert.append({
                    "measurement": measurement_name,
                    "tags": {
                        "operator": operator,
                        "zupc": zupc
                    },
                    "time": now.strftime('%Y%m%dT%H:%M:%SZ'),
                    "fields": {
                        "value": len(active)
                    }
                }
        )
        if len(to_insert) == 100:
            if client:
                try:
                    client.write_points(to_insert)
                except InfluxDBClientError as e:
                    current_app.logger.error(e)
            else:
                current_app.logger.error("No influx db client")

            to_insert[:] = []

    for operator, zupc_active in map_operateur_insee_nb_active.items():
        for zupc, active in zupc_active.items():
            insert(operator, zupc, active)

    for zupc, active in map_insee_nb_active.items():
        insert("", zupc, active)

    for operateur, active in map_operateur_nb_active.items():
        insert(operateur, "", active)

    insert("", "", active_taxis)

    for operator, zupc_available in map_operateur_insee_nb_active.items():
        for zupc, available in zupc_active.items():
            insert(operator, zupc, available, True)

    for zupc, available in map_insee_nb_active.items():
        insert("", zupc, available, True)

    if len(to_insert) > 0:
        if client:
            client.write_points(to_insert)

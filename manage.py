# -*- coding: utf8 -*-
from APITaxi import manager, app, db
from flask.ext.migrate import Migrate, MigrateCommand
from flask.ext.script.commands import ShowUrls
from APITaxi.commands import *

migrate = Migrate(app, db)
manager.add_command('db', MigrateCommand)
manager.add_command('urls', ShowUrls)

if __name__ == '__main__':
    manager.run()

"""Rename conducteur to driver

Revision ID: 44090569867
Revises: 7d563dd0c13
Create Date: 2015-04-23 15:41:36.152860

"""

# revision identifiers, used by Alembic.
revision = '44090569867'
down_revision = '7d563dd0c13'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('driver',
    sa.Column('added_at', sa.DateTime(), nullable=True),
    sa.Column('added_via', sa.Enum('form', 'api', name='sources_driver'), nullable=False),
    sa.Column('source', sa.String(length=255), nullable=False),
    sa.Column('last_update_at', sa.DateTime(), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nom', sa.String(length=255), nullable=False),
    sa.Column('prenom', sa.String(length=255), nullable=False),
    sa.Column('date_naissance', sa.Date(), nullable=True),
    sa.Column('carte_pro', sa.String(), nullable=False),
    sa.Column('departement_id', sa.Integer(), nullable=True),
    sa.Column('added_by', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['added_by'], ['user.id'], ),
    sa.ForeignKeyConstraint(['departement_id'], ['departement.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.execute('drop table conducteur cascade')
    op.add_column('taxi', sa.Column('driver_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'taxi', 'driver', ['driver_id'], ['id'])
    op.drop_column('taxi', 'conducteur_id')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('taxi', sa.Column('conducteur_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'taxi', type_='foreignkey')
    op.create_foreign_key(u'taxi_conducteur_id_fkey', 'taxi', 'conducteur', ['conducteur_id'], ['id'])
    op.drop_column('taxi', 'driver_id')
    op.create_table('conducteur',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('nom', sa.VARCHAR(length=255), autoincrement=False, nullable=False),
    sa.Column('prenom', sa.VARCHAR(length=255), autoincrement=False, nullable=False),
    sa.Column('date_naissance', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('carte_pro', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('added_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('added_by', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('added_via', postgresql.ENUM(u'form', u'api', name='via'), autoincrement=False, nullable=True),
    sa.Column('last_update_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('source', sa.VARCHAR(length=255), autoincrement=False, nullable=False),
    sa.Column('departement_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['added_by'], [u'user.id'], name=u'conducteur_added_by_fkey'),
    sa.ForeignKeyConstraint(['departement_id'], [u'departement.id'], name=u'conducteur_departement_id_fkey'),
    sa.PrimaryKeyConstraint('id', name=u'conducteur_pkey')
    )
    op.drop_table('driver')
    ### end Alembic commands ###

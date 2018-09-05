# Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""split volume_mapping table

Revision ID: 33cdd98bb9b2
Revises: 35cb52c5553f
Create Date: 2018-09-22 22:24:35.745666

"""

# revision identifiers, used by Alembic.
revision = '33cdd98bb9b2'
down_revision = '35cb52c5553f'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy import dialects


def MediumText():
    return sa.Text().with_variant(dialects.mysql.MEDIUMTEXT(), 'mysql')


VOLUME_MAPPING_TABLE = sa.Table(
    'volume_mapping', sa.MetaData(),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('uuid', sa.String(36), primary_key=True, nullable=False),
    sa.Column('project_id', sa.String(length=255), nullable=True),
    sa.Column('user_id', sa.String(length=255), nullable=True),
    sa.Column('cinder_volume_id', sa.String(36), nullable=True),
    sa.Column('volume_provider', sa.String(36), nullable=False),
    sa.Column('connection_info', MediumText(), nullable=True),
    sa.Column('volume_id', sa.Integer(), nullable=True),
    sa.Column('host', sa.String(length=255), nullable=True),
    sa.Column('auto_remove', sa.Boolean(), default=False, nullable=True),
    sa.Column('contents', MediumText(), nullable=True))


VOLUME_TABLE = sa.Table(
    'volume', sa.MetaData(),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
    sa.Column('uuid', sa.String(36), nullable=False),
    sa.Column('project_id', sa.String(length=255), nullable=True),
    sa.Column('user_id', sa.String(length=255), nullable=True),
    sa.Column('cinder_volume_id', sa.String(36), nullable=True),
    sa.Column('volume_provider', sa.String(36), nullable=False),
    sa.Column('connection_info', MediumText(), nullable=True),
    sa.Column('host', sa.String(length=255), nullable=True),
    sa.Column('auto_remove', sa.Boolean(), default=False, nullable=True),
    sa.Column('contents', MediumText(), nullable=True))


def create_volume_table():
    op.create_table(
        'volume',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(length=255), nullable=True),
        sa.Column('user_id', sa.String(length=255), nullable=True),
        sa.Column('cinder_volume_id', sa.String(36), nullable=True),
        sa.Column('volume_provider', sa.String(36), nullable=False),
        sa.Column('connection_info', MediumText(), nullable=True),
        sa.Column('host', sa.String(length=255), nullable=True),
        sa.Column('auto_remove', sa.Boolean(), default=False, nullable=True),
        sa.Column('contents', MediumText(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid', name='uniq_volume0uuid'),
    )


def update_existing_records():
    op.add_column('volume_mapping',
                  sa.Column('volume_id', sa.Integer(),
                            nullable=True))

    # perform data migration between tables
    session = sa.orm.Session(bind=op.get_bind())
    with session.begin(subtransactions=True):
        for row in session.query(VOLUME_MAPPING_TABLE):
            res = session.execute(
                VOLUME_TABLE.insert().values(
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                    uuid=row.uuid,
                    project_id=row.project_id,
                    user_id=row.user_id,
                    cinder_volume_id=row.cinder_volume_id,
                    volume_provider=row.volume_provider,
                    connection_info=row.connection_info,
                    host=row.host)
            )
            session.execute(
                VOLUME_MAPPING_TABLE.update().values(
                    volume_id=res.inserted_primary_key[0]).where(
                        VOLUME_MAPPING_TABLE.c.id == row.id)
            )
    # this commit is necessary to allow further operations
    session.commit()

    op.alter_column('volume_mapping', 'volume_id',
                    nullable=False,
                    existing_type=sa.Integer(), existing_nullable=True,
                    existing_server_default=False)
    # add the constraint now that everything is populated on that table
    op.create_foreign_key(
        constraint_name=None, source_table='volume_mapping',
        referent_table='volume',
        local_cols=['volume_id'], remote_cols=['id'],
        ondelete='CASCADE')


def update_volume_mapping_table():
    op.drop_column('volume_mapping', 'cinder_volume_id')
    op.drop_column('volume_mapping', 'volume_provider')
    op.drop_column('volume_mapping', 'connection_info')
    op.drop_column('volume_mapping', 'contents')
    op.drop_column('volume_mapping', 'auto_remove')
    op.drop_column('volume_mapping', 'host')


def upgrade():
    create_volume_table()
    update_existing_records()
    update_volume_mapping_table()

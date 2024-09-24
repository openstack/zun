# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""add rp_uuid to compute_node

Revision ID: d502ce8fb705
Revises: b2bda272f4dd
Create Date: 2019-08-25 15:27:06.626340

"""

# revision identifiers, used by Alembic.
revision = 'd502ce8fb705'
down_revision = 'b2bda272f4dd'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


COMPUTE_NODE_TABLE = sa.Table(
    'compute_node', sa.MetaData(),
    sa.Column('uuid', sa.String(36), primary_key=True, nullable=False),
    sa.Column('rp_uuid', sa.String(36), nullable=True))


def upgrade():
    op.add_column('compute_node',
                  sa.Column('rp_uuid', sa.String(length=36), nullable=True))
    op.create_unique_constraint('uniq_compute_node0rp_uuid',
                                'compute_node', ['rp_uuid'])

    # perform data migration between tables
    with sa.orm.Session(bind=op.get_bind()) as session:
        for row in session.query(COMPUTE_NODE_TABLE):
            session.execute(
                COMPUTE_NODE_TABLE.update().values(
                    rp_uuid=row.uuid).where(
                        COMPUTE_NODE_TABLE.c.uuid == row.uuid)
            )
        # this commit is necessary to allow further operations
        session.commit()

    op.alter_column('compute_node', 'rp_uuid',
                    nullable=False,
                    existing_type=sa.String(length=36),
                    existing_nullable=True,
                    existing_server_default=False)

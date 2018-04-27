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

"""empty message

Revision ID: 3298c6a5c3d9
Revises: 271c7f45982d
Create Date: 2018-04-28 06:32:26.493248

"""

# revision identifiers, used by Alembic.
revision = '3298c6a5c3d9'
down_revision = '271c7f45982d'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'network',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.String(length=255), nullable=True),
        sa.Column('user_id', sa.String(length=255), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('uuid', sa.String(length=36), nullable=True),
        sa.Column('network_id', sa.String(length=255), nullable=True),
        sa.Column('neutron_net_id', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid', name='uniq_network0uuid'),
        sa.UniqueConstraint('neutron_net_id',
                            name='uniq_network0neutron_net_id'),
        mysql_charset='utf8',
        mysql_engine='InnoDB'
        )

#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""add host to ZunNetwork

Revision ID: 3f2b36231bee
Revises: f979327df44b
Create Date: 2023-12-18 10:47:27.164812

"""

# revision identifiers, used by Alembic.
revision = '3f2b36231bee'
down_revision = 'f979327df44b'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('network',
                  sa.Column('host', sa.String(length=255), nullable=True))
    op.drop_constraint(constraint_name='uniq_network0neutron_net_id',
                       table_name='network', type_='unique')
    op.create_unique_constraint(
        constraint_name='uniq_network0neutron_net_id_host',
        table_name='network', columns=['neutron_net_id', 'host'])

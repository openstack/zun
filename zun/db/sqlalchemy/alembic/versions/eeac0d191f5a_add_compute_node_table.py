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

"""add compute node table

Revision ID: eeac0d191f5a
Revises: 8192905fd835
Create Date: 2017-02-28 21:32:58.122924

"""

# revision identifiers, used by Alembic.
revision = 'eeac0d191f5a'
down_revision = '8192905fd835'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

from zun.db.sqlalchemy import models


def upgrade():
    op.create_table(
        'compute_node',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('hostname', sa.String(length=255), nullable=False),
        sa.Column('numa_topology', models.JSONEncodedDict(), nullable=True),
        sa.PrimaryKeyConstraint('uuid'),
    )

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Add memory info to compute node

Revision ID: 53a8b515057e
Revises: eeac0d191f5a
Create Date: 2017-04-13 10:12:41.088202

"""

# revision identifiers, used by Alembic.
revision = '53a8b515057e'
down_revision = 'eeac0d191f5a'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('compute_node',
                  sa.Column('mem_total', sa.Integer(), nullable=False))
    op.add_column('compute_node',
                  sa.Column('mem_free', sa.Integer(), nullable=False))
    op.add_column('compute_node',
                  sa.Column('mem_available', sa.Integer(), nullable=False))

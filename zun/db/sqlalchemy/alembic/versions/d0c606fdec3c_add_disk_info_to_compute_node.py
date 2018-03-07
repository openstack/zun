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

"""add disk total and used to compute node

Revision ID: d0c606fdec3c
Revises: 3f49fa520409
Create Date: 2018-03-06 18:44:27.630273

"""

# revision identifiers, used by Alembic.
revision = 'd0c606fdec3c'
down_revision = '3f49fa520409'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    with op.batch_alter_table('compute_node', schema=None) as batch_op:
        batch_op.add_column(sa.Column('disk_total',
                                      sa.Integer(), nullable=False))
        batch_op.add_column(sa.Column('disk_used',
                                      sa.Integer(), nullable=False))

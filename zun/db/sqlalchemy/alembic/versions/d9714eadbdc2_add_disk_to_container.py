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

"""add disk to container

Revision ID: d9714eadbdc2
Revises: 71f8b4cf1dbf
Create Date: 2018-01-30 13:47:11.871600

"""

# revision identifiers, used by Alembic.
revision = 'd9714eadbdc2'
down_revision = '71f8b4cf1dbf'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    with op.batch_alter_table('container', schema=None) as batch_op:
        batch_op.add_column(sa.Column('disk', sa.Integer(), nullable=True))

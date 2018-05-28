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


"""Add quota usage

Revision ID: 012a730926e8
Revises: 3298c6a5c3d9
Create Date: 2018-05-30 21:23:17.659203

"""

# revision identifiers, used by Alembic.
revision = '012a730926e8'
down_revision = '3298c6a5c3d9'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'quota_usages',
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.String(length=255), index=True),
        sa.Column('resource', sa.String(length=255), nullable=False),
        sa.Column('in_use', sa.Integer, nullable=False),
        sa.Column('reserved', sa.Integer, nullable=False),
        sa.Column('until_refresh', sa.Integer),
        mysql_engine='InnoDB'
    )

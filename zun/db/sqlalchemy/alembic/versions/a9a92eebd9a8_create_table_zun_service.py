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


"""create_table_zun_service

Revision ID: a9a92eebd9a8
Revises:
Create Date: 2016-05-27 10:53:10.367610

"""

# revision identifiers, used by Alembic.
revision = 'a9a92eebd9a8'
down_revision = None
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'zun_service',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('report_count', sa.Integer(), nullable=False),
        sa.Column('host', sa.String(length=255), nullable=True),
        sa.Column('binary', sa.String(length=255), nullable=True),
        sa.Column('disabled', sa.Boolean(), nullable=True),
        sa.Column('disabled_reason', sa.String(length=255), nullable=True),
        sa.Column('last_seen_up', sa.DateTime(), nullable=True),
        sa.Column('forced_down', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('host', 'binary',
                            name='uniq_zun_service0host0binary')
    )

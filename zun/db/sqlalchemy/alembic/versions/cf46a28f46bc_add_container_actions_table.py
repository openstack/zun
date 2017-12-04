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

"""add container_actions table

Revision ID: cf46a28f46bc
Revises: f046346d1d87
Create Date: 2017-12-01 10:47:00.192171

"""

# revision identifiers, used by Alembic.
revision = 'cf46a28f46bc'
down_revision = 'd2affd5b4172'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'container_actions',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=255), nullable=True),
        sa.Column('container_uuid', sa.String(length=36), nullable=False),
        sa.Column('request_id', sa.String(length=255), nullable=True),
        sa.Column('user_id', sa.String(length=255), nullable=True),
        sa.Column('project_id', sa.String(length=255), nullable=True),
        sa.Column('start_time', sa.DateTime(), nullable=True),
        sa.Column('finish_time', sa.DateTime(), nullable=True),
        sa.Column('message', sa.String(length=255), nullable=True),
        sa.Index('container_uuid_idx', 'container_uuid'),
        sa.Index('request_id_idx', 'request_id'),
        sa.ForeignKeyConstraint(['container_uuid'], ['container.uuid'], ),
        sa.PrimaryKeyConstraint('id')
    )

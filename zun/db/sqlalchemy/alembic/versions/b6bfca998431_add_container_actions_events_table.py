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

"""add container_actions_events table

Revision ID: b6bfca998431
Revises: cf46a28f46bc
Create Date: 2017-12-01 10:53:38.106686

"""

# revision identifiers, used by Alembic.
revision = 'b6bfca998431'
down_revision = 'cf46a28f46bc'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'container_actions_events',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event', sa.String(length=255), nullable=True),
        sa.Column('action_id', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.DateTime(), nullable=True),
        sa.Column('finish_time', sa.DateTime(), nullable=True),
        sa.Column('result', sa.String(length=255), nullable=True),
        sa.Column('traceback', sa.Text(), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['action_id'], ['container_actions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

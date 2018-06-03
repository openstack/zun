# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""create exec_instance table

Revision ID: 26896d5f9053
Revises: 012a730926e8
Create Date: 2018-06-03 17:24:33.192354

"""

# revision identifiers, used by Alembic.
revision = '26896d5f9053'
down_revision = '012a730926e8'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'exec_instance',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('container_id', sa.Integer(), nullable=False),
        sa.Column('exec_id', sa.String(255), nullable=False),
        sa.Column('token', sa.String(255), nullable=True),
        sa.Column('url', sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['container_id'], ['container.id'],
                                ondelete='CASCADE'),
        sa.UniqueConstraint('container_id', 'exec_id',
                            name='uniq_exec_instance0container_id_exec_id'),
    )

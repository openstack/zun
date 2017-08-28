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

"""create volume_mapping table

Revision ID: 10d65e285a59
Revises: 945569b3669f
Create Date: 2017-08-25 22:42:18.814016

"""

# revision identifiers, used by Alembic.
revision = '10d65e285a59'
down_revision = '945569b3669f'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy import dialects


def MediumText():
    return sa.Text().with_variant(dialects.mysql.MEDIUMTEXT(), 'mysql')


def upgrade():
    op.create_table(
        'volume_mapping',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(length=255), nullable=True),
        sa.Column('user_id', sa.String(length=255), nullable=True),
        sa.Column('volume_id', sa.String(36), nullable=False),
        sa.Column('volume_provider', sa.String(36), nullable=False),
        sa.Column('container_uuid', sa.String(36), nullable=False),
        sa.Column('container_path', sa.String(length=255), nullable=True),
        sa.Column('connection_info', MediumText(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid', name='uniq_volume0uuid'),
    )

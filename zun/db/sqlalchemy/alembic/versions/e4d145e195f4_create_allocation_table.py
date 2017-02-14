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

"""Create allocation table

Revision ID: e4d145e195f4
Revises: 09f196622a3f
Create Date: 2017-02-12 21:50:19.742699

"""

# revision identifiers, used by Alembic.
revision = 'e4d145e195f4'
down_revision = '09f196622a3f'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

import zun


def upgrade():
    op.create_table(
        'allocation',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('resource_provider_id', sa.Integer(), nullable=False),
        sa.Column('consumer_id', sa.String(36), nullable=False),
        sa.Column('resource_class_id', sa.Integer(), nullable=False),
        sa.Column('used', sa.Integer(), nullable=False),
        sa.Column('is_nested', sa.Integer(), nullable=False),
        sa.Column('blob', zun.db.sqlalchemy.models.JSONEncodedList(),
                  nullable=True),
        sa.Index('allocation_resource_provider_class_used_idx',
                 'resource_provider_id', 'resource_class_id', 'used'),
        sa.Index('allocation_consumer_id_idx', 'consumer_id'),
        sa.Index('allocation_resource_class_id_idx', 'resource_class_id'),
        sa.PrimaryKeyConstraint('id'),
    )

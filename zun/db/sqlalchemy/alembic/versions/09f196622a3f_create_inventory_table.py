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

"""create inventory table

Revision ID: 09f196622a3f
Revises: 7975b7f0f792
Create Date: 2017-02-12 12:37:57.799877

"""

# revision identifiers, used by Alembic.
revision = '09f196622a3f'
down_revision = '7975b7f0f792'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

import zun


def upgrade():
    op.create_table(
        'inventory',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('resource_provider_id', sa.Integer(), nullable=False),
        sa.Column('resource_class_id', sa.Integer(), nullable=False),
        sa.Column('total', sa.Integer(), nullable=False),
        sa.Column('reserved', sa.Integer(), nullable=False),
        sa.Column('min_unit', sa.Integer(), nullable=False),
        sa.Column('max_unit', sa.Integer(), nullable=False),
        sa.Column('step_size', sa.Integer(), nullable=False),
        sa.Column('allocation_ratio', sa.Float(), nullable=False),
        sa.Column('is_nested', sa.Integer(), nullable=False),
        sa.Column('blob', zun.db.sqlalchemy.models.JSONEncodedList(),
                  nullable=True),
        sa.Index('inventory_resource_provider_id_idx',
                 'resource_provider_id'),
        sa.Index('inventory_resource_provider_resource_class_idx',
                 'resource_provider_id', 'resource_class_id'),
        sa.Index('inventory_resource_class_id_idx',
                 'resource_class_id'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'resource_provider_id', 'resource_class_id',
            name='uniq_inventory0resource_provider_resource_class'),
    )

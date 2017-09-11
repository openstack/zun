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

"""add pci device

Revision ID: 37bce72463e3
Revises: 10d65e285a59
Create Date: 2017-09-08 10:18:48.658980

"""

# revision identifiers, used by Alembic.
revision = '37bce72463e3'
down_revision = '10d65e285a59'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'pci_device',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', sa.String(length=36)),
        sa.Column('compute_node_uuid', sa.String(length=36), nullable=False),
        sa.Column('address', sa.String(length=12), nullable=False),
        sa.Column('vendor_id', sa.String(length=4), nullable=False),
        sa.Column('product_id', sa.String(length=4), nullable=False),
        sa.Column('dev_type', sa.String(length=8), nullable=False),
        sa.Column('dev_id', sa.String(255)),
        sa.Column('label', sa.String(255), nullable=False),
        sa.Column('status', sa.String(36), nullable=False),
        sa.Column('request_id', sa.String(36), nullable=False),
        sa.Column('extra_info', sa.Text()),
        sa.Column('container_uuid', sa.String(36)),
        sa.Column('numa_node', sa.Integer(), nullable=True),
        sa.Column('parent_addr', sa.String(12), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('compute_node_uuid', 'address',
                            name='uniq_pci_device0compute_node_uuid0address'),
        sa.Index('ix_pci_device_compute_node_uuid', 'compute_node_uuid'),
        sa.Index('ix_pci_device_container_uuid', 'container_uuid'),
        sa.Index('ix_pci_device_compute_node_uuid_parent_addr',
                 'compute_node_uuid', 'parent_addr'),
    )

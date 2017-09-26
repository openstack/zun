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

"""add timestamp to pci device

Revision ID: f046346d1d87
Revises: ff7b9665d504
Create Date: 2017-10-09 15:30:34.922130

"""

# revision identifiers, used by Alembic.
revision = 'f046346d1d87'
down_revision = 'ff7b9665d504'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('pci_device',
                  sa.Column('created_at', sa.DateTime(), nullable=True))
    op.add_column('pci_device',
                  sa.Column('updated_at', sa.DateTime(), nullable=True))
    op.drop_column('pci_device', 'request_id')
    op.add_column('pci_device', sa.Column('request_id', sa.String(36),
                                          nullable=True))

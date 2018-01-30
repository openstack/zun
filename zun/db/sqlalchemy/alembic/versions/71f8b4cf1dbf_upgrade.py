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

"""upgrade

Revision ID: 71f8b4cf1dbf
Revises: 10c9668a816d
Create Date: 2018-01-29 09:09:32.297389

"""

# revision identifiers, used by Alembic.
revision = '71f8b4cf1dbf'
down_revision = '10c9668a816d'
branch_labels = None
depends_on = None

from alembic import op
from sqlalchemy.dialects import mysql


def upgrade():
    with op.batch_alter_table('capsule', schema=None) as batch_op:
        batch_op.create_unique_constraint('uniq_capsule0uuid', ['uuid'])
        batch_op.drop_column('message')

    with op.batch_alter_table('container_actions', schema=None) as batch_op:
        batch_op.create_foreign_key(
            None, 'container', ['container_uuid'], ['uuid'])

    with op.batch_alter_table('pci_device', schema=None) as batch_op:
        batch_op.create_foreign_key(
            None, 'compute_node', ['compute_node_uuid'], ['uuid'])

    with op.batch_alter_table('volume_mapping', schema=None) as batch_op:
        batch_op.alter_column('container_uuid',
                              existing_type=mysql.VARCHAR(length=36),
                              nullable=True)
        batch_op.create_foreign_key(
            None, 'container', ['container_uuid'], ['uuid'])

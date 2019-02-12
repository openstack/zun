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

"""add registry_id to container

Revision ID: 1bc34e18180b
Revises: 5ffc1cabe6b4
Create Date: 2019-01-06 21:45:57.505152

"""

# revision identifiers, used by Alembic.
revision = '1bc34e18180b'
down_revision = '5ffc1cabe6b4'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('container',
                  sa.Column('registry_id', sa.Integer(),
                            nullable=True))
    op.create_foreign_key(
        None, 'container', 'registry', ['registry_id'], ['id'])

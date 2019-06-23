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

"""add tty to container

Revision ID: b2bda272f4dd
Revises: 157a0595e13e
Create Date: 2019-06-23 21:22:18.324322

"""

# revision identifiers, used by Alembic.
revision = 'b2bda272f4dd'
down_revision = '157a0595e13e'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('container',
                  sa.Column('tty', sa.Boolean(), nullable=True))

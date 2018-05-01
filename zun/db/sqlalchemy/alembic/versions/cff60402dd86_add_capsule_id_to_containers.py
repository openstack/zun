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

"""add capsule_id to containers

Revision ID: cff60402dd86
Revises: 2b045cb595db
Create Date: 2018-04-29 21:27:00.722445

"""

# revision identifiers, used by Alembic.
revision = 'cff60402dd86'
down_revision = '2b045cb595db'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('container',
                  sa.Column('capsule_id', sa.Integer(),
                            nullable=True))

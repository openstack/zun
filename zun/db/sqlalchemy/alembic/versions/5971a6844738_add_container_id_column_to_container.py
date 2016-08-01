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

"""add container_id column to container

Revision ID: 5971a6844738
Revises: 9fe371393a24
Create Date: 2016-08-05 17:38:05.231740

"""

# revision identifiers, used by Alembic.
revision = '5971a6844738'
down_revision = '9fe371393a24'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('container',
                  sa.Column('container_id', sa.String(length=255),
                            nullable=True))

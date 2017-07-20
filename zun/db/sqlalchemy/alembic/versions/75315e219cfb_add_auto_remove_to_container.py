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

"""Add auto_remove to container

Revision ID: 75315e219cfb
Revises: 648c25faa0be
Create Date: 2017-06-30 22:10:22.261595

"""

# revision identifiers, used by Alembic.
revision = '75315e219cfb'
down_revision = '648c25faa0be'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('container',
                  sa.Column('auto_remove', sa.Boolean(),
                            nullable=True))

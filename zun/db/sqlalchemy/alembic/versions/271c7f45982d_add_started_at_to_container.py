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

from alembic import op
import sqlalchemy as sa
"""add started_at to containers

Revision ID: 271c7f45982d
Revises: cff60402dd86
Create Date: 2018-05-03 11:27:00.722445

"""

# revision identifiers, used by Alembic.
revision = '271c7f45982d'
down_revision = 'cff60402dd86'
branch_labels = None
depends_on = None



def upgrade():
    op.add_column('container',
                  sa.Column('started_at', sa.DateTime(),
                            nullable=True))

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


"""add privileged to container

Revision ID: 105626c4f972
Revises: 3e80bbfd8da7
Create Date: 2018-07-26 15:05:10.567715

"""

# revision identifiers, used by Alembic.
revision = '105626c4f972'
down_revision = '3e80bbfd8da7'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('container',
                  sa.Column('privileged', sa.Boolean(),
                            nullable=True))

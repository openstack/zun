# Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""add tty stdin_open

Revision ID: d1ef05fd92c8
Revises: ad43a2179cf2
Create Date: 2016-11-09 09:40:59.839380

"""

# revision identifiers, used by Alembic.
revision = 'd1ef05fd92c8'
down_revision = 'ad43a2179cf2'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('container',
                  sa.Column('tty', sa.Boolean,
                            nullable=True))
    op.add_column('container',
                  sa.Column('stdin_open', sa.Boolean,
                            nullable=True))

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

"""combine tty and stdin_open

Revision ID: ce9944b346cb
Revises: 4bf34495d060
Create Date: 2017-04-21 12:24:50.201662

"""

# revision identifiers, used by Alembic.
revision = 'ce9944b346cb'
down_revision = '4bf34495d060'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    with op.batch_alter_table('container', schema=None) as batch_op:
        batch_op.add_column(sa.Column('interactive', sa.Boolean(),
                                      nullable=True))
        batch_op.drop_column('tty')
        batch_op.drop_column('stdin_open')

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


"""Insert status_reason to Container table

Revision ID: c5565cbaa3de
Revises: 72c6947c6636
Create Date: 2016-10-28 06:51:12.146721

"""

# revision identifiers, used by Alembic.
revision = 'c5565cbaa3de'
down_revision = '72c6947c6636'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('container',
                  sa.Column('status_reason', sa.Text(),
                            nullable=True))

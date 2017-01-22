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


"""add_status_detail

Revision ID: ad43a2179cf2
Revises: bbcfa910a8a5
Create Date: 2017-01-17 03:14:50.739446

"""

# revision identifiers, used by Alembic.
revision = 'ad43a2179cf2'
down_revision = 'bbcfa910a8a5'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('container', sa.Column('status_detail',
                  sa.String(length=50), nullable=True))

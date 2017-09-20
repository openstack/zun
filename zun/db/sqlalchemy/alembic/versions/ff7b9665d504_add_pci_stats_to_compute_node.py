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

"""add pci stats to compute node

Revision ID: ff7b9665d504
Revises: fc27c7415d9c
Create Date: 2017-09-26 13:49:11.470002

"""

# revision identifiers, used by Alembic.
revision = 'ff7b9665d504'
down_revision = 'fc27c7415d9c'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('compute_node',
                  sa.Column('pci_stats', sa.Text()))

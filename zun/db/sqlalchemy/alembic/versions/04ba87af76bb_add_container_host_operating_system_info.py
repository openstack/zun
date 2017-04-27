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

"""Add container host operating system info

Revision ID: 04ba87af76bb
Revises: 8c3d80e18eb5
Create Date: 2017-04-26 17:37:09.544598

"""

# revision identifiers, used by Alembic.
revision = '04ba87af76bb'
down_revision = '8c3d80e18eb5'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('compute_node',
                  sa.Column('architecture', sa.String(32), nullable=True))
    op.add_column('compute_node',
                  sa.Column('os_type', sa.String(32), nullable=True))
    op.add_column('compute_node',
                  sa.Column('os', sa.String(64), nullable=True))
    op.add_column('compute_node',
                  sa.Column('kernel_version',
                            sa.String(128), nullable=True))

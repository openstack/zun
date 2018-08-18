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

"""add host to image

Revision ID: a019998b09b5
Revises: a9c9fb54274a
Create Date: 2018-08-17 13:49:11.470002

"""

# revision identifiers, used by Alembic.
revision = 'a019998b09b5'
down_revision = 'a9c9fb54274a'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('image',
                  sa.Column('host', sa.String(length=255), nullable=True))
    op.drop_constraint(constraint_name='uniq_image0repotag',
                       table_name='image', type_='unique')
    op.create_unique_constraint(constraint_name='uniq_image0repotaghost',
                                table_name='image',
                                columns=['repo', 'tag', 'host'])

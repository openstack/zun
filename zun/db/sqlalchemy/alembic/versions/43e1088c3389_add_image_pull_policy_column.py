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

"""add image_pull_policy column

Revision ID: 43e1088c3389
Revises: c5565cbaa3de
Create Date: 2016-11-17 09:26:22.756296

"""

# revision identifiers, used by Alembic.
revision = '43e1088c3389'
down_revision = 'c5565cbaa3de'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('container',
                  sa.Column('image_pull_policy', sa.Text(),
                            nullable=True))

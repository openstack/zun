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

"""add_contents_to_volume_mapping_table

Revision ID: a9c9fb54274a
Revises: bc56b9932dd9
Create Date: 2018-08-10 02:49:27.524151

"""

# revision identifiers, used by Alembic.
revision = 'a9c9fb54274a'
down_revision = 'bc56b9932dd9'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def MediumText():
    return sa.Text().with_variant(sa.dialects.mysql.MEDIUMTEXT(), 'mysql')


def upgrade():
    op.add_column('volume_mapping',
                  sa.Column('contents', MediumText(), nullable=True))
    op.alter_column('volume_mapping', 'volume_id',
                    existing_type=sa.String(36),
                    nullable=True)

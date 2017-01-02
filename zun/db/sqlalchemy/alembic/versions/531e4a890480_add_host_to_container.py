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

"""add host to container

Revision ID: 531e4a890480
Revises: 4a0c4f7a4a33
Create Date: 2017-01-01 11:20:14.964792

"""

# revision identifiers, used by Alembic.
revision = '531e4a890480'
down_revision = '4a0c4f7a4a33'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('container',
                  sa.Column('host', sa.String(length=255),
                            nullable=True))

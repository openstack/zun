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

from alembic import op
import sqlalchemy as sa
"""add runtime column

Revision ID: 945569b3669f
Revises: a251f1f61217
Create Date: 2017-08-04 09:10:47.810568

"""

# revision identifiers, used by Alembic.
revision = '945569b3669f'
down_revision = 'a251f1f61217'
branch_labels = None
depends_on = None



def upgrade():
    op.add_column('container',
                  sa.Column('runtime', sa.String(32), nullable=True))

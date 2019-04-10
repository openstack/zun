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


from alembic import op
import sqlalchemy as sa
"""add host to volume mapping

Revision ID: f746cd28bcac
Revises: 2fb377a5a519
Create Date: 2018-08-03 10:53:45.920787

"""

# revision identifiers, used by Alembic.
revision = 'f746cd28bcac'
down_revision = '2fb377a5a519'
branch_labels = None
depends_on = None



def upgrade():
    op.add_column('volume_mapping',
                  sa.Column('host', sa.String(length=255), nullable=True))

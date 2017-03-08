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

"""add_restart_policy_column

Revision ID: bbcfa910a8a5
Revises: 531e4a890480
Create Date: 2017-01-10 15:10:02.746131

"""

# revision identifiers, used by Alembic.
revision = 'bbcfa910a8a5'
down_revision = '531e4a890480'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

import zun


def upgrade():
    op.add_column('container',
                  sa.Column('restart_policy',
                            zun.db.sqlalchemy.models.JSONEncodedDict(),
                            nullable=True))

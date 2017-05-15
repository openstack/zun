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

"""Add container hosts label info

Revision ID: 17ab8b533cc8
Revises: 04ba87af76bb
Create Date: 2017-05-03 14:00:06.170629

"""

# revision identifiers, used by Alembic.
revision = '17ab8b533cc8'
down_revision = '04ba87af76bb'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

import zun


def upgrade():
    op.add_column('compute_node',
                  sa.Column('labels',
                            zun.db.sqlalchemy.models.JSONEncodedDict(),
                            nullable=True))

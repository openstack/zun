# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""add meta addresses to container

Revision ID: 4a0c4f7a4a33
Revises: 43e1088c3389
Create Date: 2016-11-20 12:18:44.086036

"""

# revision identifiers, used by Alembic.
revision = '4a0c4f7a4a33'
down_revision = '43e1088c3389'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

from zun.db.sqlalchemy import models


def upgrade():
    op.add_column('container',
                  sa.Column('meta', models.JSONEncodedDict(),
                            nullable=True))
    op.add_column('container',
                  sa.Column('addresses', models.JSONEncodedDict(),
                            nullable=True))

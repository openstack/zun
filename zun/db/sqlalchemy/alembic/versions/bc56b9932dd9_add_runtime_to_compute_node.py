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


"""add runtime to compute node

Revision ID: bc56b9932dd9
Revises: f746cd28bcac
Create Date: 2018-08-06 18:30:43.890410

"""

# revision identifiers, used by Alembic.
revision = 'bc56b9932dd9'
down_revision = 'f746cd28bcac'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

import zun


def upgrade():
    op.add_column('compute_node',
                  sa.Column('runtimes',
                            zun.db.sqlalchemy.models.JSONEncodedList(),
                            nullable=True))

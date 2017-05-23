
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

"""add security groups

Revision ID: 174cafda0857
Revises: 5359d23b2322
Create Date: 2017-05-16 08:49:27.482284

"""

# revision identifiers, used by Alembic.
revision = '174cafda0857'
down_revision = '5359d23b2322'
branch_labels = None
depends_on = None


from alembic import op
import sqlalchemy as sa

import zun


def upgrade():
    op.add_column('container',
                  sa.Column('security_groups',
                            zun.db.sqlalchemy.models.JSONEncodedList(),
                            nullable=True))

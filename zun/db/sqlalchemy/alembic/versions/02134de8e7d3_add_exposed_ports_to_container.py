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
import zun
"""add_exposed_ports_to_container

Revision ID: 02134de8e7d3
Revises: a019998b09b5
Create Date: 2018-08-19 19:29:51.636559

"""

# revision identifiers, used by Alembic.
revision = '02134de8e7d3'
down_revision = 'a019998b09b5'
branch_labels = None
depends_on = None




def upgrade():
    op.add_column('container',
                  sa.Column('exposed_ports',
                            zun.db.sqlalchemy.models.JSONEncodedDict(),
                            nullable=True))

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

"""Add init containers uuids to capsule

Revision ID: 54bcb75afb32
Revises: 02134de8e7d3
Create Date: 2018-08-14 15:47:49.127773

"""

# revision identifiers, used by Alembic.
revision = '54bcb75afb32'
down_revision = '02134de8e7d3'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

from zun.db.sqlalchemy import models


def upgrade():
    op.add_column('capsule', sa.Column('init_containers_uuids',
                                       models.JSONEncodedList(),
                                       nullable=True))

# Copyright 2017 Arm Limited
#
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

"""add host to capsule

Revision ID: bcd6410d645e
Revises: 37bce72463e3
Create Date: 2017-09-20 17:23:49.346283

"""

# revision identifiers, used by Alembic.
revision = 'bcd6410d645e'
down_revision = '37bce72463e3'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('capsule',
                  sa.Column('host', sa.String(length=255),
                            nullable=True))

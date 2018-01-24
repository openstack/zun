# Copyright 2018 Arm Limited.
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


"""add volumes info and addresses to capsule

Revision ID: 10c9668a816d
Revises: 8b0082d9e7c1
Create Date: 2018-01-19 15:40:35.242920

"""

# revision identifiers, used by Alembic.
revision = '10c9668a816d'
down_revision = '8b0082d9e7c1'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

from zun.db.sqlalchemy import models


def upgrade():
    op.add_column('capsule', sa.Column('volumes_info',
                                       models.JSONEncodedDict(),
                                       nullable=True))

    op.add_column('capsule',
                  sa.Column('addresses', models.JSONEncodedDict(),
                            nullable=True))

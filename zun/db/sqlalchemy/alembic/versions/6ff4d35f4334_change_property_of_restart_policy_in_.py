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

"""change properties of restart policy in capsule

Revision ID: 6ff4d35f4334
Revises: d9714eadbdc2
Create Date: 2018-01-26 17:19:59.564188

"""

# revision identifiers, used by Alembic.
revision = '6ff4d35f4334'
down_revision = 'd9714eadbdc2'
branch_labels = None
depends_on = None

from alembic import op

import sqlalchemy as sa


def upgrade():
    op.alter_column('capsule', 'restart_policy',
                    type_=sa.String(length=255)
                    )

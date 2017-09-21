# Copyright 2017 Arm Limited.
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

"""change the properties of meta_labels

Revision ID: fc27c7415d9c
Revises: bcd6410d645e
Create Date: 2017-09-07 10:56:07.489031

"""

# revision identifiers, used by Alembic.
revision = 'fc27c7415d9c'
down_revision = 'bcd6410d645e'
branch_labels = None
depends_on = None

from alembic import op

import zun


def upgrade():
    op.alter_column('capsule', 'meta_labels',
                    type_=zun.db.sqlalchemy.models.JSONEncodedDict()
                    )

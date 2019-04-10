# Copyright 2017 ARM Limited
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

# revision identifiers, used by Alembic.
from alembic import op
import sqlalchemy as sa
revision = 'd2affd5b4172'
down_revision = 'f046346d1d87'
branch_labels = None
depends_on = None



def upgrade():
    op.add_column('volume_mapping',
                  sa.Column('auto_remove', sa.Boolean, nullable=True))

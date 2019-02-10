# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""add container_type to container

Revision ID: d73b72ab7cc6
Revises: 1bc34e18180b
Create Date: 2019-02-12 04:34:30.993517

"""

# revision identifiers, used by Alembic.
revision = 'd73b72ab7cc6'
down_revision = '1bc34e18180b'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

from zun.common import consts


def upgrade():
    op.add_column('container',
                  sa.Column('container_type', sa.Integer(), index=True,
                            default=consts.TYPE_CONTAINER,
                            server_default=str(consts.TYPE_CONTAINER)))

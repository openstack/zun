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

"""remove meta from container

Revision ID: c2052ead4f95
Revises: df87dbd4846c
Create Date: 2019-12-30 17:11:48.838977

"""

# revision identifiers, used by Alembic.
revision = 'c2052ead4f95'
down_revision = 'df87dbd4846c'
branch_labels = None
depends_on = None

from alembic import op


def upgrade():
    op.drop_column('container', 'meta')

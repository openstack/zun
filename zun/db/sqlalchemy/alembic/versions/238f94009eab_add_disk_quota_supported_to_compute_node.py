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

"""add disk_quota_supported to compute_node

Revision ID: 238f94009eab
Revises: 372433c0afd2
Create Date: 2018-04-01 18:46:29.977789

"""

# revision identifiers, used by Alembic.
revision = '238f94009eab'
down_revision = '372433c0afd2'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('compute_node',
                  sa.Column('disk_quota_supported', sa.Boolean(),
                            nullable=False, default=sa.sql.false(),
                            server_default=sa.sql.false()))

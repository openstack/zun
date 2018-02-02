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

"""drop_container_actions_foreign_key

Revision ID: fb9ad4a050f8
Revises: 6ff4d35f4334
Create Date: 2018-02-02 11:01:46.151429

"""

# revision identifiers, used by Alembic.
revision = 'fb9ad4a050f8'
down_revision = '6ff4d35f4334'
branch_labels = None
depends_on = None

from alembic import op
from sqlalchemy.engine.reflection import Inspector as insp

CONTAINER_ACTIONS = 'container_actions'
CONTAINER = 'container'


def upgrade():
    bind = op.get_bind()

    inspector = insp.from_engine(bind)
    foreign_keys = inspector.get_foreign_keys(CONTAINER_ACTIONS)

    for foreign_key in foreign_keys:
        if foreign_key.get('referred_table') == CONTAINER:
            op.drop_constraint(foreign_key.get('name'), CONTAINER_ACTIONS,
                               type_="foreignkey")
            op.create_foreign_key(
                None, CONTAINER_ACTIONS, CONTAINER, ['container_uuid'],
                ['uuid'], ondelete='CASCADE')

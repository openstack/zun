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

"""add ondelete to container_actions_events foreign key

Revision ID: 50829990c965
Revises: fb9ad4a050f8
Create Date: 2018-02-02 03:58:14.384716

"""

# revision identifiers, used by Alembic.
revision = '50829990c965'
down_revision = 'fb9ad4a050f8'
branch_labels = None
depends_on = None

from alembic import op
from sqlalchemy.engine.reflection import Inspector as insp

CONTAINER_ACTIONS_EVENTS = 'container_actions_events'
CONTAINER_ACTIONS = 'container_actions'


def upgrade():
    bind = op.get_bind()

    inspector = insp.from_engine(bind)
    foreign_keys = inspector.get_foreign_keys(CONTAINER_ACTIONS_EVENTS)

    for foreign_key in foreign_keys:
        if foreign_key.get('referred_table') == CONTAINER_ACTIONS:
            op.drop_constraint(foreign_key.get('name'),
                               CONTAINER_ACTIONS_EVENTS,
                               type_="foreignkey")
            op.create_foreign_key(
                None, CONTAINER_ACTIONS_EVENTS, CONTAINER_ACTIONS,
                ['action_id'], ['id'], ondelete='CASCADE')

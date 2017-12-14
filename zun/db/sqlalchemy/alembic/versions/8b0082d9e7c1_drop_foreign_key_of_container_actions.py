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

"""drop foreign key of container_actions container_uuid

Revision ID: 8b0082d9e7c1
Revises: b6bfca998431
Create Date: 2017-12-14 15:32:38.520594

"""

# revision identifiers, used by Alembic.
revision = '8b0082d9e7c1'
down_revision = 'b6bfca998431'
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

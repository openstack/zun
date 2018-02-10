# Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""add availability_zone to service

Revision ID: 3f49fa520409
Revises: 50829990c965
Create Date: 2018-02-10 22:33:22.890723

"""

# revision identifiers, used by Alembic.
revision = '3f49fa520409'
down_revision = '50829990c965'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('zun_service',
                  sa.Column('availability_zone', sa.String(255),
                            nullable=True))

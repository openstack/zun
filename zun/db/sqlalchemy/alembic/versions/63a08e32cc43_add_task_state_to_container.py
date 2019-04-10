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


from alembic import op
import sqlalchemy as sa
"""add task state to container

Revision ID: 63a08e32cc43
Revises: 93fbb05b77b9
Create Date: 2016-08-14 20:10:04.038358

"""

# revision identifiers, used by Alembic.
revision = '63a08e32cc43'
down_revision = '93fbb05b77b9'
branch_labels = None
depends_on = None



def upgrade():
    op.add_column('container',
                  sa.Column('task_state', sa.String(length=20),
                            nullable=True))

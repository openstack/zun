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


from alembic import op
import sqlalchemy as sa
"""add memory field to container

Revision ID: 93fbb05b77b9
Revises: 5971a6844738
Create Date: 2016-08-05 19:03:03.764296

"""

# revision identifiers, used by Alembic.
revision = '93fbb05b77b9'
down_revision = '5971a6844738'
branch_labels = None
depends_on = None



def upgrade():
    op.add_column('container',
                  sa.Column('memory', sa.String(length=255),
                            nullable=True))

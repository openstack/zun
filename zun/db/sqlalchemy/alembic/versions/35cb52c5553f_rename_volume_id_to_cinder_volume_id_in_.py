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

"""rename volume_id to cinder_volume_id in volume_mapping

Revision ID: 35cb52c5553f
Revises: 54bcb75afb32
Create Date: 2018-09-22 20:20:02.072979

"""

# revision identifiers, used by Alembic.
revision = '35cb52c5553f'
down_revision = '54bcb75afb32'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column(
        'volume_mapping', 'volume_id',
        new_column_name='cinder_volume_id',
        type_=sa.String(36)
    )

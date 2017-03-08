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

"""add uuid_to_resource_class

Revision ID: 8192905fd835
Revises: e4d145e195f4
Create Date: 2017-02-24 07:00:22.344162

"""

# revision identifiers, used by Alembic.
revision = '8192905fd835'
down_revision = 'e4d145e195f4'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('resource_class',
                  sa.Column('uuid', sa.String(length=36), nullable=False))
    op.create_unique_constraint('uniq_resource_class0uuid',
                                'resource_class', ['uuid'])
    op.drop_index('uniq_container0name', table_name='resource_class')

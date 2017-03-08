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

"""Add cpu workdir ports hostname labels to container

Revision ID: 1192ba19a6e9
Revises: 63a08e32cc43
Create Date: 2016-08-20 09:56:38.902481

"""

# revision identifiers, used by Alembic.
revision = '1192ba19a6e9'
down_revision = '63a08e32cc43'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

import zun


def upgrade():
    op.add_column('container',
                  sa.Column('cpu', sa.Float(),
                            nullable=True))
    op.add_column('container',
                  sa.Column('workdir', sa.String(length=255),
                            nullable=True))
    op.add_column('container',
                  sa.Column('ports',
                            zun.db.sqlalchemy.models.JSONEncodedList(),
                            nullable=True))
    op.add_column('container',
                  sa.Column('hostname', sa.String(length=255),
                            nullable=True))
    op.add_column('container',
                  sa.Column('labels',
                            zun.db.sqlalchemy.models.JSONEncodedDict(),
                            nullable=True))

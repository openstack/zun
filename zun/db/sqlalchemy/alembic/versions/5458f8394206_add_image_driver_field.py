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


"""add image driver field

Revision ID: 5458f8394206
Revises: d1ef05fd92c8
Create Date: 2017-01-25 19:01:46.033461

"""

# revision identifiers, used by Alembic.
revision = '5458f8394206'
down_revision = 'd1ef05fd92c8'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('container',
                  sa.Column('image_driver', sa.Text(),
                            nullable=True))

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

"""add healthcheck to containers

Revision ID: 2fb377a5a519
Revises: 105626c4f972
Create Date: 2018-05-03 11:27:00.722445

"""

# revision identifiers, used by Alembic.
revision = '2fb377a5a519'
down_revision = '105626c4f972'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
import zun


def upgrade():
    with op.batch_alter_table('container', schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            'healthcheck', zun.db.sqlalchemy.models.JSONEncodedDict(),
            nullable=True))

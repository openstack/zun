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

"""drop capsule table

Revision ID: 157a0595e13e
Revises: d73b72ab7cc6
Create Date: 2019-02-18 20:21:39.108829

"""

# revision identifiers, used by Alembic.
revision = '157a0595e13e'
down_revision = 'd73b72ab7cc6'
branch_labels = None
depends_on = None

from alembic import op


def upgrade():
    op.drop_table('capsule')

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


"""Convert type of 'command' from string to list

Revision ID: 3e80bbfd8da7
Revises: 26896d5f9053
Create Date: 2018-06-20 11:21:38.077673

"""

import json
import shlex

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3e80bbfd8da7'
down_revision = '26896d5f9053'
branch_labels = None
depends_on = None


TABLE_MODEL = sa.Table(
    'container', sa.MetaData(),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('command', sa.Text()))


def upgrade():
    op.alter_column('container', 'command', type_=sa.Text())
    # Convert 'command' from string to json-encoded list
    session = sa.orm.Session(bind=op.get_bind())
    with session.begin(subtransactions=True):
        for row in session.query(TABLE_MODEL):
            if row[1]:
                command = shlex.split(row[1])
                command = json.dumps(command)
                session.execute(
                    TABLE_MODEL.update().values(
                        command=command).where(
                            TABLE_MODEL.c.id == row[0]))
    session.commit()

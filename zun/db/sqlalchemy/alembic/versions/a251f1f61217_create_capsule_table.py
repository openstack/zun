# Copyright 2017 ARM Holdings
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""create capsule table

Revision ID: a251f1f61217
Revises: 75315e219cfb
Create Date: 2017-06-20 17:12:56.105277

"""

# revision identifiers, used by Alembic.
revision = 'a251f1f61217'
down_revision = '75315e219cfb'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

from zun.db.sqlalchemy import models


def upgrade():
    op.create_table(
        'capsule',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('capsule_version', sa.String(length=255), nullable=True),
        sa.Column('kind', sa.String(length=36), nullable=True),
        sa.Column('project_id', sa.String(length=255), nullable=True),
        sa.Column('user_id', sa.String(length=255), nullable=True),
        sa.Column('restart_policy', sa.String(length=255), nullable=True),
        sa.Column('host_selector', sa.String(length=255), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('status', sa.String(length=255), nullable=True),
        sa.Column('status_reason', sa.Text(), nullable=True),
        sa.Column('message', models.JSONEncodedDict(), nullable=True),
        sa.Column('spec', models.JSONEncodedDict(), nullable=True),
        sa.Column('cpu', sa.Float(), nullable=True),
        sa.Column('memory', sa.String(length=255), nullable=True),
        sa.Column('meta_name', sa.String(length=255), nullable=True),
        sa.Column('meta_labels', models.JSONEncodedList(), nullable=True),
        sa.Column('containers_uuids', models.JSONEncodedList(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

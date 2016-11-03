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

"""Zun DB test base class."""

import fixtures

import zun.conf
from zun.db import api as db_api
from zun.db.sqlalchemy import api as sqla_api
from zun.db.sqlalchemy import migration
from zun.db.sqlalchemy import models
from zun.tests import base


CONF = zun.conf.CONF

_DB_CACHE = None


class Database(fixtures.Fixture):

    def __init__(self, db_api, db_migrate, sql_connection):
        self.sql_connection = sql_connection
        self.engine = db_api.get_engine()
        self.engine.dispose()
        conn = self.engine.connect()
        self.setup_sqlite(db_migrate)
        self.post_migrations()

        self._DB = "".join(line for line in conn.connection.iterdump())
        self.engine.dispose()

    def setup_sqlite(self, db_migrate):
        if db_migrate.version():
            return
        models.Base.metadata.create_all(self.engine)
        db_migrate.stamp('head')

    def _setUp(self):
        conn = self.engine.connect()
        conn.connection.executescript(self._DB)
        self.addCleanup(self.engine.dispose)

    def post_migrations(self):
        """Any addition steps that are needed outside of the migrations."""


class DbTestCase(base.TestCase):

    def setUp(self):
        super(DbTestCase, self).setUp()

        self.dbapi = db_api.get_instance()

        global _DB_CACHE
        if not _DB_CACHE:
            _DB_CACHE = Database(sqla_api, migration,
                                 sql_connection=CONF.database.connection)
        self.useFixture(_DB_CACHE)

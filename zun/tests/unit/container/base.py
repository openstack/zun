# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo_db.sqlalchemy import enginefacade
import zun.conf
from zun.db import api as db_api
from zun.db.sqlalchemy import migration
from zun.tests import base
from zun.tests.unit.db.base import Database

CONF = zun.conf.CONF

_DB_CACHE = None


class DriverTestCase(base.TestCase):
    def setUp(self):
        super(DriverTestCase, self).setUp()
        self.dbapi = db_api._get_dbdriver_instance()

        global _DB_CACHE
        if not _DB_CACHE:
            engine = enginefacade.writer.get_engine()
            _DB_CACHE = Database(engine, migration,
                                 sql_connection=CONF.database.connection)
            engine.dispose()
        self.useFixture(_DB_CACHE)

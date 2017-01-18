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

from oslo_config import cfg

import zun.conf
from zun.db import api as db_api
from zun.db.sqlalchemy import api as sqla_api
from zun.db.sqlalchemy import migration
from zun.tests import base
from zun.tests.unit.db.base import Database

CONF = zun.conf.CONF

_DB_CACHE = None


class DriverTestCase(base.TestCase):
    def setUp(self):
        super(DriverTestCase, self).setUp()
        # NOTE(yuywz): In driver test cases, we use sqllite as
        # the DB backend, so we should set 'db_type' to 'sql'
        # to access sqllite DB with sqlalchemy api.
        cfg.CONF.set_override('db_type', 'sql')
        self.dbapi = db_api._get_dbdriver_instance()

        global _DB_CACHE
        if not _DB_CACHE:
            _DB_CACHE = Database(sqla_api, migration,
                                 sql_connection=CONF.database.connection)
        self.useFixture(_DB_CACHE)

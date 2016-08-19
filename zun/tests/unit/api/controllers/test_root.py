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

from oslo_config import cfg

import webtest

from zun.api import app
from zun.tests.unit.api import base as api_base


class TestRootController(api_base.FunctionalTest):
    def setUp(self):
        super(TestRootController, self).setUp()
        self.root_expected = {
            u'default_version':
            {u'id': u'v1', u'links':
             [{u'href': u'http://localhost/v1/', u'rel': u'self'}]},
            u'description': u'Zun is an OpenStack project which '
            'aims to provide container management.',
            u'versions': [{u'id': u'v1',
                          u'links':
                              [{u'href': u'http://localhost/v1/',
                                u'rel': u'self'}]}]}

        self.v1_expected = {
            u'media_types':
            [{u'base': u'application/json',
              u'type': u'application/vnd.openstack.zun.v1+json'}],
            u'links': [{u'href': u'http://localhost/v1/',
                        u'rel': u'self'},
                       {u'href':
                        u'http://docs.openstack.org/developer'
                        '/zun/dev/api-spec-v1.html',
                        u'type': u'text/html', u'rel': u'describedby'}],
            u'services': [{u'href': u'http://localhost/v1/services/',
                           u'rel': u'self'},
                          {u'href': u'http://localhost/services/',
                           u'rel': u'bookmark'}],
            u'id': u'v1',
            u'containers': [{u'href': u'http://localhost/v1/containers/',
                             u'rel': u'self'},
                            {u'href': u'http://localhost/containers/',
                             u'rel': u'bookmark'}]}

    def make_app(self, paste_file):
        file_name = self.get_path(paste_file)
        cfg.CONF.set_override("api_paste_config", file_name, group="api")
        return webtest.TestApp(app.load_app())

    def test_version(self):
        response = self.app.get('/')
        self.assertEqual(self.root_expected, response.json)

    def test_v1_controller(self):
        response = self.app.get('/v1/')
        self.assertEqual(self.v1_expected, response.json)

    def test_get_not_found(self):
        response = self.app.get('/a/bogus/url', expect_errors=True)
        assert response.status_int == 404

    def test_noauth(self):
        # Don't need to auth
        paste_file = "zun/tests/unit/api/controllers/noauth-paste.ini"
        app = self.make_app(paste_file)

        response = app.get('/')
        self.assertEqual(self.root_expected, response.json)

        response = app.get('/v1/')
        self.assertEqual(self.v1_expected, response.json)

        response = app.get('/v1/containers/')
        self.assertEqual(200, response.status_int)

    def test_auth_with_no_public_routes(self):
        # All apis need auth when access
        paste_file = "zun/tests/unit/api/controllers/auth-paste.ini"
        app = self.make_app(paste_file)

        response = app.get('/', expect_errors=True)
        self.assertEqual(401, response.status_int)

        response = app.get('/v1/', expect_errors=True)
        self.assertEqual(401, response.status_int)

    def test_auth_with_root_access(self):
        # Only / can access without auth
        paste_file = "zun/tests/unit/api/controllers/auth-root-access.ini"
        app = self.make_app(paste_file)

        response = app.get('/')
        self.assertEqual(self.root_expected, response.json)

        response = app.get('/v1/', expect_errors=True)
        self.assertEqual(401, response.status_int)

        response = app.get('/v1/containers', expect_errors=True)
        self.assertEqual(401, response.status_int)

    def test_auth_with_v1_access(self):
        # Only /v1 can access without auth
        paste_file = "zun/tests/unit/api/controllers/auth-v1-access.ini"
        app = self.make_app(paste_file)

        response = app.get('/', expect_errors=True)
        self.assertEqual(401, response.status_int)

        response = app.get('/v1/')
        self.assertEqual(self.v1_expected, response.json)

        response = app.get('/v1/containers', expect_errors=True)
        self.assertEqual(401, response.status_int)

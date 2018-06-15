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


CURRENT_VERSION = api_base.CURRENT_VERSION


class TestRootController(api_base.FunctionalTest):
    def setUp(self):
        super(TestRootController, self).setUp()
        self.root_expected = {
            'default_version':
            {'id': 'v1',
             'links': [{'href': 'http://localhost/v1/', 'rel': 'self'}],
             'max_version': '1.20',
             'min_version': '1.1',
             'status': 'CURRENT'},
            'description': 'Zun is an OpenStack project which '
            'aims to provide containers service.',
            'name': 'OpenStack Zun API',
            'versions': [{'id': 'v1',
                          'links': [{'href': 'http://localhost/v1/',
                                     'rel': 'self'}],
                          'max_version': '1.20',
                          'min_version': '1.1',
                          'status': 'CURRENT'}]}

        self.v1_expected = {
            'media_types':
            [{'base': 'application/json',
              'type': 'application/vnd.openstack.zun.v1+json'}],
            'links': [{'href': 'http://localhost/v1/',
                       'rel': 'self'},
                      {'href':
                       'https://docs.openstack.org/developer'
                       '/zun/dev/api-spec-v1.html',
                       'type': 'text/html', 'rel': 'describedby'}],
            'services': [{'href': 'http://localhost/v1/services/',
                          'rel': 'self'},
                         {'href': 'http://localhost/services/',
                          'rel': 'bookmark'}],
            'id': 'v1',
            'containers': [{'href': 'http://localhost/v1/containers/',
                            'rel': 'self'},
                           {'href': 'http://localhost/containers/',
                            'rel': 'bookmark'}],
            'hosts': [{'href': 'http://localhost/v1/hosts/',
                       'rel': 'self'},
                      {'href': 'http://localhost/hosts/',
                       'rel': 'bookmark'}],
            'availability_zones': [
                {'href': 'http://localhost/v1/availability_zones/',
                 'rel': 'self'},
                {'href': 'http://localhost/availability_zones/',
                 'rel': 'bookmark'}],
            'images': [{'href': 'http://localhost/v1/images/',
                        'rel': 'self'},
                       {'href': 'http://localhost/images/',
                        'rel': 'bookmark'}],
            'networks': [{'href': 'http://localhost/v1/networks/',
                          'rel': 'self'},
                         {'href': 'http://localhost/networks/',
                          'rel': 'bookmark'}],
            'capsules': [{'href': 'http://localhost/v1/capsules/',
                          'rel': 'self'},
                         {'href': 'http://localhost/capsules/',
                          'rel': 'bookmark'}]}

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
        headers = {'OpenStack-API-Version': CURRENT_VERSION}
        app = self.make_app(paste_file)

        response = app.get('/', headers=headers)
        self.assertEqual(self.root_expected, response.json)

        response = app.get('/v1/', headers=headers)
        self.assertEqual(self.v1_expected, response.json)

        response = app.get('/v1/containers/', headers=headers)
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

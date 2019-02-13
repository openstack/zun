# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from zun.common.docker_image import digest
from zun.common.docker_image import reference
from zun.common import exception
from zun.tests import base


class TestReference(base.BaseTestCase):
    def test_reference(self):
        def create_test_case(input_, err=None, repository=None, hostname=None,
                             tag=None, digest=None, path=None):
            return {
                'input': input_,
                'err': err,
                'repository': repository,
                'hostname': hostname,
                'tag': tag,
                'digest': digest,
                'path': path,
            }

        test_cases = [
            create_test_case(input_='test_com', repository='test_com'),
            create_test_case(input_='test.com:tag', repository='test.com',
                             tag='tag'),
            create_test_case(input_='test.com:5000', repository='test.com',
                             tag='5000'),
            create_test_case(input_='test.com/repo:tag',
                             repository='test.com/repo', hostname='test.com',
                             tag='tag'),
            create_test_case(input_='test:5000/repo',
                             repository='test:5000/repo',
                             hostname='test:5000'),
            create_test_case(input_='test:5000/repo:tag',
                             repository='test:5000/repo', hostname='test:5000',
                             tag='tag'),
            create_test_case(input_='test:5000/repo@sha256:{}'.
                                    format('f' * 64),
                             repository='test:5000/repo',
                             hostname='test:5000',
                             digest='sha256:{}'.format('f' * 64)),
            create_test_case(input_='test:5000/repo:tag@sha256:{}'.
                                    format('f' * 64),
                             repository='test:5000/repo',
                             hostname='test:5000',
                             tag='tag',
                             digest='sha256:{}'.format('f' * 64)),
            create_test_case(input_='test:5000/repo',
                             repository='test:5000/repo',
                             hostname='test:5000'),
            create_test_case(input_='', err=exception.NameEmpty),
            create_test_case(input_=':justtag',
                             err=exception.ReferenceInvalidFormat),
            create_test_case(input_='@sha256:{}'.format('f' * 64),
                             err=exception.ReferenceInvalidFormat),
            create_test_case(input_='repo@sha256:{}'.format('f' * 34),
                             err=digest.DigestInvalidLength),
            create_test_case(input_='validname@invaliddigest:{}'.
                                    format('f' * 64),
                             err=digest.DigestUnsupported),
            create_test_case(input_='{}a:tag'.format('a/' * 128),
                             err=exception.NameTooLong),
            create_test_case(input_='{}a:tag-puts-this-over-max'.
                                    format('a/' * 127),
                             repository='{}a'.format('a/' * 127),
                             hostname='',
                             tag='tag-puts-this-over-max'),
            create_test_case(input_='aa/asdf$$^/aa',
                             err=exception.ReferenceInvalidFormat),
            create_test_case(input_='sub-dom1.foo.com/bar/baz/quux',
                             repository='sub-dom1.foo.com/bar/baz/quux',
                             hostname='sub-dom1.foo.com'),
            create_test_case(input_='sub-dom1.foo.com/bar/baz/quux:some-'
                                    'long-tag',
                             repository='sub-dom1.foo.com/bar/baz/quux',
                             hostname='sub-dom1.foo.com',
                             tag='some-long-tag'),
            create_test_case(input_='b.gcr.io/test.example.com/my-app:test.'
                                    'example.com',
                             repository='b.gcr.io/test.example.com/my-app',
                             hostname='b.gcr.io',
                             tag='test.example.com'),
            create_test_case(input_='xn--n3h.com/myimage:xn--n3h.com',
                             repository='xn--n3h.com/myimage',
                             hostname='xn--n3h.com',
                             tag='xn--n3h.com'),
            create_test_case(input_='xn--7o8h.com/myimage:xn--7o8h.com@'
                                    'sha512:{}'.format('f' * 128),
                             repository='xn--7o8h.com/myimage',
                             hostname='xn--7o8h.com',
                             tag='xn--7o8h.com',
                             digest='sha512:{}'.format('f' * 128)),
            create_test_case(input_='foo_bar.com:8080',
                             repository='foo_bar.com',
                             tag='8080'),
            create_test_case(input_='foo/foo_bar.com:8080',
                             repository='foo/foo_bar.com',
                             hostname='',
                             tag='8080'),
            create_test_case(input_='test.com/foo',
                             repository='test.com/foo',
                             hostname='test.com',
                             path='foo'),
            create_test_case(input_='test_com/foo',
                             repository='test_com/foo',
                             hostname='',
                             path='test_com/foo'),
            create_test_case(input_='test:8080/foo',
                             repository='test:8080/foo',
                             hostname='test:8080',
                             path='foo'),
            create_test_case(input_='test.com:8080/foo',
                             repository='test.com:8080/foo',
                             hostname='test.com:8080',
                             path='foo'),
            create_test_case(input_='test-com:8080/foo',
                             repository='test-com:8080/foo',
                             hostname='test-com:8080',
                             path='foo'),
            create_test_case(input_='xn--n3h.com:18080/foo',
                             repository='xn--n3h.com:18080/foo',
                             hostname='xn--n3h.com:18080',
                             path='foo'),
        ]

        for tc in test_cases:
            if tc['err']:
                self.assertRaises(tc['err'], reference.Reference.parse,
                                  tc['input'])
                continue

            try:
                r = reference.Reference.parse(tc['input'])
            except Exception as e:
                raise e
            else:
                if tc['repository'] is not None:
                    self.assertEqual(tc['repository'], r['name'])

                if tc['hostname'] is not None:
                    hostname, _ = r.split_hostname()
                    self.assertEqual(tc['hostname'], hostname)

                if tc['path'] is not None:
                    _, path = r.split_hostname()
                    self.assertEqual(tc['path'], path)

                if tc['tag'] is not None:
                    self.assertEqual(tc['tag'], r['tag'])

                if tc['digest'] is not None:
                    self.assertEqual(tc['digest'], r['digest'])

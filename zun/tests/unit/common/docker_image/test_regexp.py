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

from zun.common.docker_image import regexp
from zun.tests import base


class TestRegexp(base.BaseTestCase):
    def test_generated_regexps(self):
        alphaNumericRegexp = r'[a-z0-9]+'
        separatorRegexp = r'(?:[._]|__|[-]*)'
        nameComponentRegexp = r'[a-z0-9]+(?:(?:(?:[._]|__|[-]*)[a-z0-9]+)+)?'
        hostnameComponentRegexp = r'(?:[a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9-]*'\
                                  '[a-zA-Z0-9])'
        hostnameRegexp = r'(?:[a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9])'\
                         '(?:(?:\.(?:[a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9-]*'\
                         '[a-zA-Z0-9]))+)?(?::[0-9]+)?'
        TagRegexp = r'[\w][\w.-]{0,127}'
        anchoredTagRegexp = r'^[\w][\w.-]{0,127}$'
        NameRegexp = r'(?:(?:[a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9])'\
                     '(?:(?:\.(?:[a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9-]*'\
                     '[a-zA-Z0-9]))+)?(?::[0-9]+)?/)?[a-z0-9]+(?:(?:'\
                     '(?:[._]|__|[-]*)[a-z0-9]+)+)?(?:(?:/[a-z0-9]+'\
                     '(?:(?:(?:[._]|__|[-]*)[a-z0-9]+)+)?)+)?'
        anchoredNameRegexp = r'^(?:((?:[a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9-]*'\
                             '[a-zA-Z0-9])(?:(?:\.(?:[a-zA-Z0-9]|[a-zA-Z0-9]'\
                             '[a-zA-Z0-9-]*[a-zA-Z0-9]))+)?(?::[0-9]+)?)/)?'\
                             '([a-z0-9]+(?:(?:(?:[._]|__|[-]*)[a-z0-9]+)+)?'\
                             '(?:(?:/[a-z0-9]+(?:(?:(?:[._]|__|[-]*)[a-z0-9]'\
                             '+)+)?)+)?)$'
        ReferenceRegexp = r'^((?:(?:[a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9-]*'\
                          '[a-zA-Z0-9])(?:(?:\.(?:[a-zA-Z0-9]|[a-zA-Z0-9]'\
                          '[a-zA-Z0-9-]*[a-zA-Z0-9]))+)?(?::[0-9]+)?/)?'\
                          '[a-z0-9]+(?:(?:(?:[._]|__|[-]*)[a-z0-9]+)+)?'\
                          '(?:(?:/[a-z0-9]+(?:(?:(?:[._]|__|[-]*)[a-z0-9]+)'\
                          '+)?)+)?)(?::([\w][\w.-]{0,127}))?(?:@'\
                          '([a-zA-Z0-9-_+.]+:[a-fA-F0-9]+))?$'

        ImageRegexps = regexp.ImageRegexps
        self.assertEqual(alphaNumericRegexp,
                         ImageRegexps.ALPHA_NUMERIC_REGEXP.pattern)
        self.assertEqual(separatorRegexp,
                         ImageRegexps.SEPARATOR_REGEXP.pattern)
        self.assertEqual(nameComponentRegexp,
                         ImageRegexps.NAME_COMPONENT_REGEXP.pattern)
        self.assertEqual(hostnameComponentRegexp,
                         ImageRegexps.HOSTNAME_COMPONENT_REGEXP.pattern)
        self.assertEqual(hostnameRegexp,
                         ImageRegexps.HOSTNAME_REGEXP.pattern)
        self.assertEqual(TagRegexp, ImageRegexps.TAG_REGEXP.pattern)
        self.assertEqual(anchoredTagRegexp,
                         ImageRegexps.ANCHORED_TAG_REGEXP.pattern)
        self.assertEqual(NameRegexp, ImageRegexps.NAME_REGEXP.pattern)
        self.assertEqual(anchoredNameRegexp,
                         ImageRegexps.ANCHORED_NAME_REGEXP.pattern)
        self.assertEqual(ReferenceRegexp,
                         ImageRegexps.REFERENCE_REGEXP.pattern)

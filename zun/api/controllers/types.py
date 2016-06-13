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

import logging

from zun.common import exception
from zun.common.i18n import _LE


LOG = logging.getLogger(__name__)


class Text(object):
    type_name = 'Text'

    @classmethod
    def validate(cls, value):
        return value


class Custom(object):
    def __init__(self, user_class):
        super(Custom, self).__init__()
        self.user_class = user_class
        self.type_name = self.user_class.__name__

    def validate(self, value):
        if not isinstance(value, self.user_class):
            try:
                value = self.user_class(**value)
            except Exception:
                LOG.exception(_LE('Failed to validate received value'))
                raise exception.InvalidValue(value=value, type=self.type_name)

        return value


class List(object):
    def __init__(self, type):
        super(List, self).__init__()
        self.type = type
        self.type_name = 'List(%s)' % self.type.type_name

    def validate(self, value):
        if not isinstance(value, list):
            raise exception.InvalidValue(value=value, type=self.type_name)

        try:
            return [self.type.validate(v) for v in value]
        except Exception:
            LOG.exception(_LE('Failed to validate received value'))
            raise exception.InvalidValue(value=value, type=self.type_name)

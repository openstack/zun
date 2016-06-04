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
import six

from oslo_utils import strutils

from zun.common import exception
from zun.common.i18n import _
from zun.common.i18n import _LE

LOG = logging.getLogger(__name__)


class Text(object):
    type_name = 'Text'

    @classmethod
    def validate(cls, value):
        if value is None:
            return None

        if not isinstance(value, six.string_types):
            raise exception.InvalidValue(value=value, type=cls.type_name)

        return value


class String(object):
    type_name = 'String'

    @classmethod
    def validate(cls, value, min_length=0, max_length=None):
        if value is None:
            return None

        try:
            strutils.check_string_length(value, min_length=min_length,
                                         max_length=max_length)
        except TypeError:
            raise exception.InvalidValue(value=value, type=cls.type_name)
        except ValueError as e:
            raise exception.InvalidValue(message=str(e))

        return value


class Integer(object):
    type_name = 'Integer'

    @classmethod
    def validate(cls, value, minimum=None):
        if value is None:
            return None

        if not isinstance(value, six.integer_types):
            try:
                value = int(value)
            except Exception:
                LOG.exception(_LE('Failed to convert value to int'))
                raise exception.InvalidValue(value=value, type=cls.type_name)

        if minimum is not None and value < minimum:
            message = _("Integer '%(value)s' is smaller than "
                        "'%(min)d'.") % {'value': value, 'min': minimum}
            raise exception.InvalidValue(message=message)

        return value


class Bool(object):
    type_name = 'Bool'

    @classmethod
    def validate(cls, value, default=None):
        if value is None:
            value = default

        if not isinstance(value, bool):
            try:
                value = strutils.bool_from_string(value, strict=True)
            except Exception:
                LOG.exception(_LE('Failed to convert value to bool'))
                raise exception.InvalidValue(value=value, type=cls.type_name)

        return value


class Custom(object):
    def __init__(self, user_class):
        super(Custom, self).__init__()
        self.user_class = user_class
        self.type_name = self.user_class.__name__

    def validate(self, value):
        if value is None:
            return None

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
        if value is None:
            return None

        if not isinstance(value, list):
            raise exception.InvalidValue(value=value, type=self.type_name)

        try:
            return [self.type.validate(v) for v in value]
        except Exception:
            LOG.exception(_LE('Failed to validate received value'))
            raise exception.InvalidValue(value=value, type=self.type_name)

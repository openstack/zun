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

import datetime
import re
import six

from oslo_log import log as logging
from oslo_utils import strutils
from oslo_utils import uuidutils

from zun.common import exception
from zun.common.i18n import _

LOG = logging.getLogger(__name__)
restricted_name_chars = '[a-zA-Z0-9][a-zA-Z0-9_.-]'
container_name_pattern = re.compile('^' + restricted_name_chars + '+$')
# TODO(pksingh): Image name pattern is not correct,need to fix that later
image_name_pattern = re.compile(restricted_name_chars)

MIN_MEMORY_SIZE = 4194304
VALID_UNITS = {
    'b': 1,
    'k': 1024,
    'm': 1024 * 1024,
    'g': 1024 * 1024 * 1024,
    'B': 1,
    'K': 1024,
    'M': 1024 * 1024,
    'G': 1024 * 1024 * 1024
}


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
            raise exception.InvalidValue(message=six.text_type(e))

        return value


class NameType(String):
    type_name = 'NameType'

    # NameType allows to be None or a string matches pattern
    # `[a-zA-Z0-9][a-zA-Z0-9_.-].` with minimum length is 2 and maximum length
    # 255 string type.

    @classmethod
    def validate(cls, value, pattern=None):
        if value is None:
            return value
        super(NameType, cls).validate(value, min_length=2, max_length=255)
        match = pattern.match(value)
        if match:
            return value
        else:
            message = _('%s does not match [a-zA-Z0-9][a-zA-Z0-9_.-]') % value
            raise exception.InvalidValue(message)


class Integer(object):
    type_name = 'Integer'

    @classmethod
    def validate(cls, value, minimum=None, maximum=None):
        if value is None:
            return None

        if not isinstance(value, six.integer_types):
            try:
                value = int(value)
            except Exception:
                LOG.exception('Failed to convert value to int')
                raise exception.InvalidValue(value=value, type=cls.type_name)

        if minimum is not None and value < minimum:
            message = _("Integer '%(value)s' is smaller than "
                        "'%(min)d'.") % {'value': value, 'min': minimum}
            raise exception.InvalidValue(message=message)

        if maximum is not None and value > maximum:
            message = _("Integer '%(value)s' is large than "
                        "'%(max)d'.") % {'value': value, 'max': maximum}
            raise exception.InvalidValue(message=message)

        return value


class Port(object):
    type_name = 'Port'

    @classmethod
    def validate(cls, value):
        return Integer.validate(value, minimum=1, maximum=65535)


class Float(object):
    type_name = 'Float'

    @classmethod
    def validate(cls, value):
        if value is None:
            return None

        if not isinstance(value, float):
            try:
                value = float(value)
            except Exception:
                LOG.exception('Failed to convert value to float')
                raise exception.InvalidValue(value=value, type=cls.type_name)

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
                LOG.exception('Failed to convert value to bool')
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
                LOG.exception('Failed to validate received value')
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
            LOG.exception('Failed to validate received value')
            raise exception.InvalidValue(value=value, type=self.type_name)


class Uuid(object):
    type_name = 'Uuid'

    @classmethod
    def validate(cls, value):
        if not uuidutils.is_uuid_like(value):
            raise exception.InvalidUUID(uuid=value)
        return value


class Dict(object):
    type_name = 'Dict'

    def __init__(self, key_type, value_type):
        super(Dict, self).__init__()
        self.key_type = key_type
        self.value_type = value_type
        self.type_name = 'Dict(%s, %s)' % (
            self.key_type.type_name, self.value_type.type_name)

    def validate(self, value):
        if value is None:
            return None

        if not isinstance(value, dict):
            raise exception.InvalidValue(value=value, type=self.type_name)

        try:
            return {self.key_type.validate(k): self.value_type.validate(v)
                    for k, v in value.items()}
        except Exception:
            LOG.exception('Failed to validate received value')
            raise exception.InvalidValue(value=value, type=self.type_name)


class Json(object):
    type_name = 'Json'

    @classmethod
    def validate(cls, value):
        if value is None:
            return None

        if not isinstance(value, dict):
            raise exception.InvalidValue(value=value, type=cls.type_name)

        return value


class DateTime(object):
    type_name = "DateTime"

    @classmethod
    def validate(cls, value):
        if value is None:
            return
        elif isinstance(value, datetime.datetime):
            return value
        raise exception.InvalidValue(value=value,
                                     type=cls.type_name)


class MemoryType(object):
    type_name = 'MemoryType'

    @classmethod
    def validate(cls, value):
        if value is None:
            return
        elif value.isdigit() and int(value) >= MIN_MEMORY_SIZE:
            return value
        elif (value.isalnum() and
              value[:-1].isdigit() and value[-1] in VALID_UNITS.keys()):
            if int(value[:-1]) * VALID_UNITS[value[-1]] >= MIN_MEMORY_SIZE:
                return value
        LOG.exception('Failed to validate container memory value')
        message = """
        memory must be either integer or string of below format.
        <integer><memory_unit> memory_unit must be 'k','b','m','g'
        in both cases"""
        raise exception.InvalidValue(message=message, value=value,
                                     type=cls.type_name)


class ImageSize(object):
    type_name = 'ImageSize'

    @classmethod
    def validate(cls, value):
        if value is None:
            return
        elif value.isdigit():
            return value
        elif (value.isalnum() and
              value[:-1].isdigit() and value[-1] in VALID_UNITS.keys()):
            return int(value[:-1]) * VALID_UNITS[value[-1]]
        else:
            LOG.exception('Failed to validate image size')
            message = _("""
            size must be either integer or string of below format.
            <integer><memory_unit> memory_unit must be 'k','b','m','g'
            in both cases""")
            raise exception.InvalidValue(message=message, value=value,
                                         type=cls.type_name)


class EnumType(object):
    type_name = 'EnumType'

    @classmethod
    def validate(cls, value, name=None, values=None):
        if value is None:
            return None
        if value.lower() not in set(values):
            message = _(
                "%(name)s should be one of: %(values)s") % {
                    'name': name,
                    'values': ', '.join([six.text_type(v) for v in values])}
            raise exception.InvalidValue(message)
        else:
            return value.lower()

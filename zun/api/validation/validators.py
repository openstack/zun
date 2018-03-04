# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import jsonschema
import six

from zun.common import exception
from zun.common.i18n import _


class SchemaValidator(object):
    """Resource reference validator class."""

    validator_org = jsonschema.Draft4Validator

    def __init__(self, schema, is_body=True):
        self.is_body = is_body
        validators = {
            'minimum': self._validate_minimum,
            'maximum': self._validate_maximum
        }
        validator_cls = jsonschema.validators.extend(self.validator_org,
                                                     validators)
        fc = jsonschema.FormatChecker()
        self.validator = validator_cls(schema, format_checker=fc)

    def validate(self, *args, **kwargs):
        try:
            self.validator.validate(*args, **kwargs)
        except jsonschema.ValidationError as ex:
            if len(ex.path) > 0:
                if self.is_body:
                    detail = _("Invalid input for field '%(path)s'."
                               "Value: '%(value)s'. %(message)s")
                else:
                    detail = _("Invalid input for query parameters "
                               "'%(path)s'. Value: '%(value)s'. %(message)s")
                detail = detail % {
                    'path': ex.path.pop(), 'value': ex.instance,
                    'message': six.text_type(ex)
                }
            else:
                detail = six.text_type(ex)
            raise exception.SchemaValidationError(detail=detail)

    def _number_from_str(self, instance):
        if isinstance(instance, float) or isinstance(instance, int):
            return instance

        try:
            value = int(instance)
        except (ValueError, TypeError):
            try:
                value = float(instance)
            except (ValueError, TypeError):
                return None
        return value

    def _validate_minimum(self, validator, minimum, instance, schema):
        instance = self._number_from_str(instance)
        if instance is None:
            return
        return self.validator_org.VALIDATORS['minimum'](validator, minimum,
                                                        instance, schema)

    def _validate_maximum(self, validator, maximum, instance, schema):
        instance = self._number_from_str(instance)
        if instance is None:
            return
        return self.validator_org.VALIDATORS['maximum'](validator, maximum,
                                                        instance, schema)

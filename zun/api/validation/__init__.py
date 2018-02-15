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

import functools

from zun.api.validation import validators


def validated(request_body_schema):
    """Register a schema to validate a resource reference.

    Registered schema will be used for validating a request body just before
    API method execution.

    :param request_body_schema: a schema to validate the resource reference
    """
    schema_validator = validators.SchemaValidator(request_body_schema,
                                                  is_body=True)

    def add_validator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            schema_validator.validate(kwargs)
            return func(*args, **kwargs)
        return wrapper
    return add_validator


def validate_query_param(req, query_param_schema):
    """Register a schema to validate a resource reference.

    Registered schema will be used for validating a request query params
    just before API method execution.

    :param req: the request object
    :param query_param_schema: a schema to validate the resource reference
    """

    schema_validator = validators.SchemaValidator(query_param_schema,
                                                  is_body=False)

    def add_validator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            schema_validator.validate(req.params.mixed())
            return func(*args, **kwargs)
        return wrapper
    return add_validator

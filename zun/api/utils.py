# Copyright 2013 Red Hat, Inc.
# All Rights Reserved.
#
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

import functools
from oslo_utils import uuidutils
import pecan

from zun.api.controllers import versions
from zun.common import exception
from zun.common.i18n import _
import zun.conf
from zun import objects

CONF = zun.conf.CONF


DOCKER_MINIMUM_MEMORY = 4 * 1024 * 1024


def string_or_none(value):
    if value in [None, 'None']:
        return None
    else:
        return value


def validate_limit(limit):
    try:
        if limit is not None and int(limit) <= 0:
            raise exception.InvalidValue(_("Limit must be positive integer"))
    except ValueError:
        raise exception.InvalidValue(_("Limit must be positive integer"))

    if limit is not None:
        return min(CONF.api.max_limit, int(limit))
    else:
        return CONF.api.max_limit


def validate_sort_dir(sort_dir):
    if sort_dir not in ['asc', 'desc']:
        raise exception.InvalidValue(_("Invalid sort direction: %s. "
                                       "Acceptable values are "
                                       "'asc' or 'desc'") % sort_dir)
    return sort_dir


def get_resource(resource, resource_ident):
    """Get the resource from the uuid or logical name.

    :param resource: the resource type.
    :param resource_ident: the UUID or logical name of the resource.

    :returns: The resource.
    """
    resource = getattr(objects, resource)
    context = pecan.request.context
    if context.is_admin:
        context.all_projects = True
    if uuidutils.is_uuid_like(resource_ident):
        return resource.get_by_uuid(context, resource_ident)

    return resource.get_by_name(context, resource_ident)


def _do_enforce_content_types(pecan_req, valid_content_types):
    """Content type enforcement

    Check to see that content type in the request is one of the valid
    types passed in by our caller.
    """
    if pecan_req.content_type not in valid_content_types:
        m = (
            "Unexpected content type: {type}. Expected content types "
            "are: {expected}"
        ).format(
            type=pecan_req.content_type.decode('utf-8'),
            expected=valid_content_types
        )
        pecan.abort(415, m)


def enforce_content_types(valid_content_types):
    """Decorator handling content type enforcement on behalf of REST verbs."""

    def content_types_decorator(fn):

        @functools.wraps(fn)
        def content_types_enforcer(inst, *args, **kwargs):
            _do_enforce_content_types(pecan.request, valid_content_types)
            return fn(inst, *args, **kwargs)

        return content_types_enforcer

    return content_types_decorator


def version_check(action, version):
    """Check whether the current version supports the operation.

    :param action: Operations to be executed.
    :param version: The minimum version required to perform the operation.

    """
    req_version = pecan.request.version
    min_version = versions.Version('', '', '', version)
    if req_version < min_version:
        raise exception.InvalidParamInVersion(param=action,
                                              req_version=req_version,
                                              min_version=min_version)

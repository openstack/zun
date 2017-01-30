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

import jsonpatch
from oslo_utils import uuidutils
import pecan
import wsme

from zun.common.i18n import _
import zun.conf
from zun import objects

CONF = zun.conf.CONF


JSONPATCH_EXCEPTIONS = (jsonpatch.JsonPatchException,
                        jsonpatch.JsonPointerException,
                        KeyError)


DOCKER_MINIMUM_MEMORY = 4 * 1024 * 1024


def string_or_none(value):
    if value in [None, 'None']:
        return None
    else:
        return value


def validate_limit(limit):
    try:
        if limit is not None and int(limit) <= 0:
            raise wsme.exc.ClientSideError(_("Limit must be positive integer"))
    except ValueError:
        raise wsme.exc.ClientSideError(_("Limit must be positive integer"))

    if limit is not None:
        return min(CONF.api.max_limit, int(limit))
    else:
        return CONF.api.max_limit


def validate_sort_dir(sort_dir):
    if sort_dir not in ['asc', 'desc']:
        raise wsme.exc.ClientSideError(_("Invalid sort direction: %s. "
                                         "Acceptable values are "
                                         "'asc' or 'desc'") % sort_dir)
    return sort_dir


def apply_jsonpatch(doc, patch):
    for p in patch:
        if p['op'] == 'add' and p['path'].count('/') == 1:
            attr = p['path'].lstrip('/')
            if attr not in doc:
                msg = _("Adding a new attribute %s to the root of "
                        "the resource is not allowed.") % p['path']
                raise wsme.exc.ClientSideError(msg)
            if doc[attr] is not None:
                msg = _("The attribute %s has existed, please use "
                        "'replace' operation instead.") % p['path']
                raise wsme.exc.ClientSideError(msg)
    return jsonpatch.apply_patch(doc, patch)


def get_resource(resource, resource_ident):
    """Get the resource from the uuid or logical name.

    :param resource: the resource type.
    :param resource_ident: the UUID or logical name of the resource.

    :returns: The resource.
    """
    resource = getattr(objects, resource)

    if uuidutils.is_uuid_like(resource_ident):
        return resource.get_by_uuid(pecan.request.context, resource_ident)

    return resource.get_by_name(pecan.request.context, resource_ident)


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

        def content_types_enforcer(inst, *args, **kwargs):
            _do_enforce_content_types(pecan.request, valid_content_types)
            return fn(inst, *args, **kwargs)

        return content_types_enforcer

    return content_types_decorator

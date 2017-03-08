# Copyright 2013 - Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Zun base exception handling.

Includes decorator for re-raising Zun-type exceptions.

"""

import functools
import inspect
from oslo_utils import uuidutils
import sys
from webob import util as woutil

from keystoneclient import exceptions as keystone_exceptions
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import excutils
import pecan
import six

from zun.common.i18n import _
from zun.common.i18n import _LE
import zun.conf

LOG = logging.getLogger(__name__)

CONF = zun.conf.CONF

try:
    CONF.import_opt('fatal_exception_format_errors',
                    'oslo_versionedobjects.exception')
except cfg.NoSuchOptError as e:
    # Note:work around for zun run against master branch
    # in devstack gate job, as zun not branched yet
    # verisonobjects kilo/master different version can
    # cause issue here. As it changed import group. So
    # add here before branch to prevent gate failure.
    # Bug: #1447873
    CONF.import_opt('fatal_exception_format_errors',
                    'oslo_versionedobjects.exception',
                    group='oslo_versionedobjects')


def wrap_exception(notifier=None, event_type=None):
    """This decorator wraps a method to catch any exceptions.

    It logs the exception as well as optionally sending
    it to the notification system.
    """
    def inner(f):
        def wrapped(self, context, *args, **kw):
            # Don't store self or context in the payload, it now seems to
            # contain confidential information.
            try:
                return f(self, context, *args, **kw)
            except Exception as e:
                with excutils.save_and_reraise_exception():
                    if notifier:
                        call_dict = inspect.getcallargs(f, self, context,
                                                        *args, **kw)
                        payload = dict(exception=e,
                                       private=dict(args=call_dict)
                                       )

                        temp_type = event_type
                        if not temp_type:
                            # If f has multiple decorators, they must use
                            # functools.wraps to ensure the name is
                            # propagated.
                            temp_type = f.__name__

                        notifier.error(context, temp_type, payload)

        return functools.wraps(f)(wrapped)
    return inner


OBFUSCATED_MSG = _('Your request could not be handled '
                   'because of a problem in the server. '
                   'Error Correlation id is: %s')


def wrap_controller_exception(func, func_server_error, func_client_error):
    """This decorator wraps controllers methods to handle exceptions:

    - if an unhandled Exception or a ZunException with an error code >=500
    is catched, raise a http 5xx ClientSideError and correlates it with a log
    message

    - if a ZunException is catched and its error code is <500, raise a http
    4xx and logs the excp in debug mode

    """
    @functools.wraps(func)
    def wrapped(*args, **kw):
        try:
            return func(*args, **kw)
        except Exception as excp:
            if isinstance(excp, ZunException):
                http_error_code = excp.code
            else:
                http_error_code = 500

            if http_error_code >= 500:
                # log the error message with its associated
                # correlation id
                log_correlation_id = uuidutils.generate_uuid()
                LOG.exception(_LE("%(correlation_id)s:%(excp)s") %
                              {'correlation_id': log_correlation_id,
                               'excp': str(excp)})
                # raise a client error with an obfuscated message
                return func_server_error(log_correlation_id, http_error_code)
            else:
                # raise a client error the original message
                LOG.debug(excp)
                return func_client_error(excp, http_error_code)
    return wrapped


def wrap_pecan_controller_exception(func):
    """This decorator wraps pecan controllers to handle exceptions."""
    def _func_server_error(log_correlation_id, status_code):
        pecan.response.status = status_code
        return {
            'status_code': status_code,
            'title': woutil.status_reasons[status_code],
            'description': six.text_type(OBFUSCATED_MSG % log_correlation_id),
        }

    def _func_client_error(excp, status_code):
        pecan.response.status = status_code
        return {
            'status_code': status_code,
            'title': woutil.status_reasons[status_code],
            'description': six.text_type(excp),
        }

    return wrap_controller_exception(func,
                                     _func_server_error,
                                     _func_client_error)


def wrap_keystone_exception(func):
    """Wrap keystone exceptions and throw Zun specific exceptions."""
    @functools.wraps(func)
    def wrapped(*args, **kw):
        try:
            return func(*args, **kw)
        except keystone_exceptions.AuthorizationFailure:
            raise AuthorizationFailure(
                client=func.__name__, message="reason: %s" % sys.exc_info()[1])
        except keystone_exceptions.ClientException:
            raise AuthorizationFailure(
                client=func.__name__,
                message="unexpected keystone client error occurred: %s"
                        % sys.exc_info()[1])
    return wrapped


class ZunException(Exception):
    """Base Zun Exception

    To correctly use this class, inherit from it and define
    a 'message' property. That message will get printf'd
    with the keyword arguments provided to the constructor.

    """
    message = _("An unknown exception occurred.")
    code = 500

    def __init__(self, message=None, **kwargs):
        self.kwargs = kwargs

        if 'code' not in self.kwargs and hasattr(self, 'code'):
            self.kwargs['code'] = self.code

        if message:
            self.message = message

        try:
            self.message = self.message % kwargs
        except KeyError:
            # kwargs doesn't match a variable in the message
            # log the issue and the kwargs
            LOG.exception(_LE('Exception in string format operation, '
                              'kwargs: %s') % kwargs)
            try:
                ferr = CONF.fatal_exception_format_errors
            except cfg.NoSuchOptError:
                ferr = CONF.oslo_versionedobjects.fatal_exception_format_errors
            if ferr:
                raise

        super(ZunException, self).__init__(self.message)

    def __str__(self):
        if six.PY3:
            return self.message
        return self.message.encode('utf-8')

    def __unicode__(self):
        return self.message

    def format_message(self):
        if self.__class__.__name__.endswith('_Remote'):
            return self.args[0]
        else:
            return six.text_type(self)


class ObjectNotFound(ZunException):
    message = _("The %(name)s %(id)s could not be found.")


class ObjectNotUnique(ZunException):
    message = _("The %(name)s already exists.")


class ResourceNotFound(ObjectNotFound):
    message = _("The %(name)s resource %(id)s could not be found.")
    code = 404


class ResourceExists(ObjectNotUnique):
    message = _("The %(name)s resource already exists.")
    code = 409


class AuthorizationFailure(ZunException):
    message = _("%(client)s connection failed. %(message)s")


class UnsupportedObjectError(ZunException):
    message = _('Unsupported object type %(objtype)s')


class IncompatibleObjectVersion(ZunException):
    message = _('Version %(objver)s of %(objname)s is not supported')


class OrphanedObjectError(ZunException):
    message = _('Cannot call %(method)s on orphaned %(objtype)s object')


class Invalid(ZunException):
    message = _("Unacceptable parameters.")
    code = 400


class InvalidValue(Invalid):
    message = _("Received value '%(value)s' is invalid for type %(type)s.")


class ValidationError(Invalid):
    message = "%(detail)s"


class SchemaValidationError(ValidationError):
    message = "%(detail)s"


class InvalidUUID(Invalid):
    message = _("Expected a uuid but received %(uuid)s.")


class InvalidName(Invalid):
    message = _("Expected a name but received %(uuid)s.")


class InvalidDiscoveryURL(Invalid):
    message = _("Received invalid discovery URL '%(discovery_url)s' for "
                "discovery endpoint '%(discovery_endpoint)s'.")


class GetDiscoveryUrlFailed(ZunException):
    message = _("Failed to get discovery url from '%(discovery_endpoint)s'.")


class InvalidUuidOrName(Invalid):
    message = _("Expected a name or uuid but received %(uuid)s.")


class InvalidIdentity(Invalid):
    message = _("Expected an uuid or int but received %(identity)s.")


class InvalidCsr(Invalid):
    message = _("Received invalid csr %(csr)s.")


class HTTPNotFound(ResourceNotFound):
    pass


class Conflict(ZunException):
    message = _('Conflict.')
    code = 409


class InvalidState(Conflict):
    message = _("Invalid resource state.")


# Cannot be templated as the error syntax varies.
# msg needs to be constructed when raised.
class InvalidParameterValue(Invalid):
    message = _("%(err)s")


class PatchError(Invalid):
    message = _("Couldn't apply patch '%(patch)s'. Reason: %(reason)s")


class NotAuthorized(ZunException):
    message = _("Not authorized.")
    code = 403


class ConfigInvalid(ZunException):
    message = _("Invalid configuration file. %(error_msg)s")


class PolicyNotAuthorized(NotAuthorized):
    message = _("Policy doesn't allow %(action)s to be performed.")


class ContainerNotFound(HTTPNotFound):
    message = _("Container %(container)s could not be found.")


class ComputeNodeNotFound(HTTPNotFound):
    message = _("Compute node %(compute_node)s could not be found.")


class ImageNotFound(HTTPNotFound):
    message = _("Image %(image)s could not be found.")


class ZunServiceNotFound(HTTPNotFound):
    message = _("Zun service %(binary)s on host %(host)s could not be found.")


class ResourceProviderNotFound(HTTPNotFound):
    message = _("Resource provider %(resource_provider)s could not be found.")


class ResourceClassNotFound(HTTPNotFound):
    message = _("Resource class %(resource_class)s could not be found.")


class InventoryNotFound(HTTPNotFound):
    message = _("Inventory %(inventory)s could not be found.")


class AllocationNotFound(HTTPNotFound):
    message = _("Allocation %(allocation)s could not be found.")


class ContainerAlreadyExists(ResourceExists):
    message = _("A container with %(field)s %(value)s already exists.")


class ComputeNodeAlreadyExists(ResourceExists):
    message = _("A compute node with %(field)s %(value)s already exists.")


class ImageAlreadyExists(ResourceExists):
    message = _("An image with tag %(tag)s and repo %(repo)s already exists.")


class ZunServiceAlreadyExists(ResourceExists):
    message = _("Service %(binary)s on host %(host)s already exists.")


class ResourceProviderAlreadyExists(ResourceExists):
    message = _("A resource provider with %(field)s %(value)s already exists.")


class ResourceClassAlreadyExists(ResourceExists):
    message = _("A resource class with %(field)s %(value)s already exists.")


class UniqueConstraintViolated(ResourceExists):
    message = _("A resource with %(fields)s violates unique constraint.")


class InvalidStateException(ZunException):
    message = _("Cannot %(action)s container %(id)s in %(actual_state)s state")
    code = 409


class DockerError(ZunException):
    message = _("Docker internal error: %(error_msg)s.")


class PollTimeOut(ZunException):
    message = _("Polling request timed out.")


class ServerInError(ZunException):
    message = _('Went to status %(resource_status)s due to '
                '"%(status_reason)s"')


class ServerUnknownStatus(ZunException):
    message = _('%(result)s - Unknown status %(resource_status)s due to '
                '"%(status_reason)s"')


class EntityNotFound(ZunException):
    message = _("The %(entity)s (%(name)s) could not be found.")


class CommandError(ZunException):
    message = _("The command: %(cmd)s failed on the system.")


class NoValidHost(ZunException):
    message = _("No valid host was found. %(reason)s")


class NoInteractiveFlag(Invalid):
    message = _("%(msg)s")


class CPUPinningUnknown(ZunException):
    message = _("CPU set to pin %(requested)s must be a subset of "
                "known CPU set %(cpuset)s")


class CPUUnpinningUnknown(Invalid):
    msg_fmt = _("CPU set to unpin %(requested)s must be a subset of "
                "known CPU set %(cpuset)s")


class CPUPinningInvalid(Invalid):
    msg_fmt = _("CPU set to pin %(requested)s must be a subset of "
                "free CPU set %(free)s")


class CPUUnpinningInvalid(Invalid):
    msg_fmt = _("CPU set to unpin %(requested)s must be a subset of "
                "pinned CPU set %(pinned)s")

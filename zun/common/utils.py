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

# It's based on oslo.i18n usage in OpenStack Keystone project and
# recommendations from http://docs.openstack.org/developer/oslo.i18n/usage.html

"""Utilities and helper functions."""
import eventlet
import functools
import mimetypes
import time

from oslo_context import context as common_context
from oslo_log import log as logging
from oslo_service import loopingcall
import pecan
import six

from zun.common import exception
from zun.common.i18n import _
from zun.common.i18n import _LW


LOG = logging.getLogger(__name__)


def safe_rstrip(value, chars=None):
    """Removes trailing characters from a string if that does not make it empty

    :param value: A string value that will be stripped.
    :param chars: Characters to remove.
    :return: Stripped value.

    """
    if not isinstance(value, six.string_types):
        LOG.warning(_LW(
            "Failed to remove trailing character. Returning original object. "
            "Supplied object is not a string: %s,"
        ), value)
        return value

    return value.rstrip(chars) or value


def _do_allow_certain_content_types(func, content_types_list):
    # Allows you to bypass pecan's content-type restrictions
    cfg = pecan.util._cfg(func)
    cfg.setdefault('content_types', {})
    cfg['content_types'].update((value, '')
                                for value in content_types_list)
    return func


def allow_certain_content_types(*content_types_list):
    def _wrapper(func):
        return _do_allow_certain_content_types(func, content_types_list)
    return _wrapper


def allow_all_content_types(f):
    return _do_allow_certain_content_types(f, mimetypes.types_map.values())


def parse_image_name(image):
    image_parts = image.split(':', 1)

    image_repo = image_parts[0]
    image_tag = 'latest'

    if len(image_parts) > 1:
        image_tag = image_parts[1]

    return image_repo, image_tag


def spawn_n(func, *args, **kwargs):
    """Passthrough method for eventlet.spawn_n.

    This utility exists so that it can be stubbed for testing without
    interfering with the service spawns.

    It will also grab the context from the threadlocal store and add it to
    the store on the new thread.  This allows for continuity in logging the
    context when using this method to spawn a new thread.
    """
    _context = common_context.get_current()

    @functools.wraps(func)
    def context_wrapper(*args, **kwargs):
        # NOTE: If update_store is not called after spawn_n it won't be
        # available for the logger to pull from threadlocal storage.
        if _context is not None:
            _context.update_store()
        func(*args, **kwargs)

    eventlet.spawn_n(context_wrapper, *args, **kwargs)


def translate_exception(function):
    """Wraps a method to catch exceptions.

    If the exception is not an instance of ZunException,
    translate it into one.
    """

    @functools.wraps(function)
    def decorated_function(self, context, *args, **kwargs):
        try:
            return function(self, context, *args, **kwargs)
        except Exception as e:
            if not isinstance(e, exception.ZunException):
                e = exception.ZunException("Unexpected Error: %s" % str(e))
                raise e
            raise

    return decorated_function


def check_container_id(function):
    '''Check container_id property of given container instance.'''

    @functools.wraps(function)
    def decorated_function(*args, **kwargs):
        container = args[1]
        if getattr(container, 'container_id', None) is None:
            msg = _("Cannot operate an uncreated container.")
            raise exception.Invalid(message=msg)
        return function(*args, **kwargs)

    return decorated_function


def poll_until(retriever, condition=lambda value: value,
               sleep_time=1, time_out=None, success_msg=None,
               timeout_msg=None):
    """Retrieves object until it passes condition, then returns it.

    If time_out_limit is passed in, PollTimeOut will be raised once that
    amount of time is elapsed.
    """
    start_time = time.time()

    def poll_and_check():
        obj = retriever()
        if condition(obj):
            raise loopingcall.LoopingCallDone(retvalue=obj)
        if time_out is not None and time.time() - start_time > time_out:
            raise exception.PollTimeOut

    try:
        poller = loopingcall.FixedIntervalLoopingCall(
            f=poll_and_check).start(sleep_time, initial_delay=False)
        poller.wait()
        LOG.info(success_msg)
    except exception.PollTimeOut:
        LOG.error(timeout_msg)
        raise
    except Exception:
        LOG.exception(_("Unexpected exception occurred."))
        raise


def get_image_pull_policy(image_pull_policy, image_tag):
    if not image_pull_policy:
        if image_tag == 'latest':
            image_pull_policy = 'always'
        else:
            image_pull_policy = 'ifnotpresent'
    return image_pull_policy


def should_pull_image(image_pull_policy, present):
    if image_pull_policy == 'never':
        return False
    if image_pull_policy == 'always' or \
            (image_pull_policy == 'ifnotpresent' and not present):
        return True
    return False

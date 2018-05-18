# Copyright (c) 2015 OpenStack Foundation
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

"""Policy Engine For zun."""

from oslo_log import log as logging
from oslo_policy import policy
from oslo_utils import excutils

from zun.common import exception
from zun.common import policies
import zun.conf

_ENFORCER = None
CONF = zun.conf.CONF
LOG = logging.getLogger(__name__)


# we can get a policy enforcer by this init.
# oslo policy support change policy rule dynamically.
# at present, policy.enforce will reload the policy rules when it checks
# the policy files have been touched.
def init(policy_file=None, rules=None,
         default_rule=None, use_conf=True, overwrite=True):
    """Init an Enforcer class.

        :param policy_file: Custom policy file to use, if none is
                            specified, ``conf.policy_file`` will be
                            used.
        :param rules: Default dictionary / Rules to use. It will be
                      considered just in the first instantiation. If
                      :meth:`load_rules` with ``force_reload=True``,
                      :meth:`clear` or :meth:`set_rules` with
                      ``overwrite=True`` is called this will be overwritten.
        :param default_rule: Default rule to use, conf.default_rule will
                             be used if none is specified.
        :param use_conf: Whether to load rules from cache or config file.
        :param overwrite: Whether to overwrite existing rules when reload rules
                          from config file.
    """
    global _ENFORCER
    if not _ENFORCER:
        # https://docs.openstack.org/oslo.policy/latest/user/usage.html
        _ENFORCER = policy.Enforcer(CONF,
                                    policy_file=policy_file,
                                    rules=rules,
                                    default_rule=default_rule,
                                    use_conf=use_conf,
                                    overwrite=overwrite)
        register_rules(_ENFORCER)
    return _ENFORCER


def register_rules(enforcer):
    enforcer.register_defaults(policies.list_rules())


def enforce(context, rule=None, target=None,
            do_raise=True, exc=None, *args, **kwargs):

    """Checks authorization of a rule against the target and credentials.

        :param dict context: As much information about the user performing the
                             action as possible.
        :param rule: The rule to evaluate.
        :param dict target: As much information about the object being operated
                            on as possible.
        :param do_raise: Whether to raise an exception or not if check
                         fails.
        :param exc: Class of the exception to raise if the check fails.
                    Any remaining arguments passed to :meth:`enforce` (both
                    positional and keyword arguments) will be passed to
                    the exception class. If not specified,
                    :class:`PolicyNotAuthorized` will be used.

        :return: ``False`` if the policy does not allow the action and `exc` is
                 not provided; otherwise, returns a value that evaluates to
                 ``True``.  Note: for rules using the "case" expression, this
                 ``True`` value will be the specified string from the
                 expression.
    """
    enforcer = init()
    credentials = context.to_policy_values()
    if not exc:
        exc = exception.PolicyNotAuthorized
    if target is None:
        target = {'project_id': context.project_id,
                  'user_id': context.user_id}
    return enforcer.enforce(rule, target, credentials,
                            do_raise=do_raise, exc=exc, *args, **kwargs)


def authorize(context, action, target, do_raise=True, exc=None,
              might_not_exist=False):
    """Verifies that the action is valid on the target in this context.

       :param context: zun context
       :param action: string representing the action to be checked
           this should be colon separated for clarity.
           i.e. ``network:attach_external_network``
       :param target: dictionary representing the object of the action
           for object creation this should be a dictionary representing the
           location of the object e.g. ``{'project_id': context.project_id}``
       :param do_raise: if True (the default), raises PolicyNotAuthorized;
           if False, returns False
       :param exc: Class of the exception to raise if the check fails.
            Any remaining arguments passed to :meth:`authorize` (both
            positional and keyword arguments) will be passed to
            the exception class. If not specified,
            :class:`PolicyNotAuthorized` will be used.
       :param might_not_exist: If True the policy check is skipped (and the
            function returns True) if the specified policy does not exist.
            Defaults to false.

       :raises zun.common.exception.PolicyNotAuthorized: if verification fails
           and do_raise is True. Or if 'exc' is specified it will raise an
           exception of that type.

       :return: returns a non-False value (not necessarily "True") if
           authorized, and the exact value False if not authorized and
           do_raise is False.
    """
    credentials = context.to_policy_values()
    if not exc:
        exc = exception.PolicyNotAuthorized
    if might_not_exist and not (_ENFORCER.rules and action in _ENFORCER.rules):
        return True
    try:
        result = _ENFORCER.enforce(action, target, credentials,
                                   do_raise=do_raise, exc=exc, action=action)
    except Exception:
        with excutils.save_and_reraise_exception():
            LOG.debug('Policy check for %(action)s failed with credentials '
                      '%(credentials)s',
                      {'action': action, 'credentials': credentials})
    return result


def check_is_admin(context):
    """Whether or not user is admin according to policy setting.

    """
    init()
    target = {}
    credentials = context.to_policy_values()
    return _ENFORCER.enforce('context_is_admin', target, credentials)

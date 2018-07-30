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

"""Utility methods for scheduling."""

import collections
import re

import os_resource_classes as orc
from oslo_log import log as logging
from six.moves.urllib import parse

import zun.conf
from zun import objects


LOG = logging.getLogger(__name__)

CONF = zun.conf.CONF


class ResourceRequest(object):
    """Presents a granular resource request via RequestGroup instances."""
    # extra_specs-specific consts
    XS_RES_PREFIX = 'resources'
    XS_TRAIT_PREFIX = 'trait'
    # Regex patterns for numbered or un-numbered resources/trait keys
    XS_KEYPAT = re.compile(r"^(%s)([1-9][0-9]*)?:(.*)$" %
                           '|'.join((XS_RES_PREFIX, XS_TRAIT_PREFIX)))

    def __init__(self):
        # { ident: RequestGroup }
        self._rg_by_id = {}
        self._group_policy = None
        # Default to the configured limit but _limit can be
        # set to None to indicate "no limit".
        self._limit = CONF.scheduler.max_placement_results

    def __str__(self):
        return ', '.join(sorted(
            list(str(rg) for rg in list(self._rg_by_id.values()))))

    @property
    def group_policy(self):
        return self._group_policy

    @group_policy.setter
    def group_policy(self, value):
        self._group_policy = value

    def get_request_group(self, ident):
        if ident not in self._rg_by_id:
            rq_grp = objects.RequestGroup(use_same_provider=bool(ident))
            self._rg_by_id[ident] = rq_grp
        return self._rg_by_id[ident]

    def add_request_group(self, request_group):
        """Inserts the existing group with a unique integer id

        This function can ensure unique ids by using bigger
        ids than the maximum of existing ids.

        :param request_group: the RequestGroup to be added
        """
        # NOTE(gibi) [0] just here to always have a defined maximum
        group_idents = [0] + [int(ident) for ident in self._rg_by_id if ident]
        ident = max(group_idents) + 1
        self._rg_by_id[ident] = request_group

    def _add_resource(self, groupid, rclass, amount):
        # Validate the class.
        if not (rclass.startswith(orc.CUSTOM_NAMESPACE) or
                rclass in orc.STANDARDS):
            LOG.warning(
                "Received an invalid ResourceClass '%(key)s' in extra_specs.",
                {"key": rclass})
            return
        # val represents the amount.  Convert to int, or warn and skip.
        try:
            amount = int(amount)
            if amount < 0:
                raise ValueError()
        except ValueError:
            LOG.warning(
                "Resource amounts must be nonnegative integers. Received "
                "'%(val)s' for key resources%(groupid)s.",
                {"groupid": groupid or '', "val": amount})
            return
        self.get_request_group(groupid).resources[rclass] = amount

    def _add_trait(self, groupid, trait_name, trait_type):
        # Currently the only valid values for a trait entry are 'required'
        # and 'forbidden'
        trait_vals = ('required', 'forbidden')
        if trait_type == 'required':
            self.get_request_group(groupid).required_traits.add(trait_name)
        elif trait_type == 'forbidden':
            self.get_request_group(groupid).forbidden_traits.add(trait_name)
        else:
            LOG.warning(
                "Only (%(tvals)s) traits are supported. Received '%(val)s' "
                "for key trait%(groupid)s.",
                {"tvals": ', '.join(trait_vals), "groupid": groupid or '',
                 "val": trait_type})
        return

    def _add_group_policy(self, policy):
        # The only valid values for group_policy are 'none' and 'isolate'.
        if policy not in ('none', 'isolate'):
            LOG.warning(
                "Invalid group_policy '%s'. Valid values are 'none' and "
                "'isolate'.", policy)
            return
        self._group_policy = policy

    @classmethod
    def from_extra_specs(cls, extra_specs, req=None):
        """Processes resources and traits in numbered groupings in extra_specs.

        Examines extra_specs for items of the following forms:
            "resources:$RESOURCE_CLASS": $AMOUNT
            "resources$N:$RESOURCE_CLASS": $AMOUNT
            "trait:$TRAIT_NAME": "required"
            "trait$N:$TRAIT_NAME": "required"

        Does *not* yet handle member_of[$N].

        :param extra_specs: The extra_specs dict.
        :param req: the ResourceRequest object to add the requirements to or
               None to create a new ResourceRequest
        :return: A ResourceRequest object representing the resources and
                 required traits in the extra_specs.
        """
        # TODO(efried): Handle member_of[$N], which will need to be reconciled
        # with destination.aggregates handling in resources_from_request_spec

        if req is not None:
            ret = req
        else:
            ret = cls()

        for key, val in extra_specs.items():
            if key == 'group_policy':
                ret._add_group_policy(val)
                continue

            match = cls.XS_KEYPAT.match(key)
            if not match:
                continue

            # 'prefix' is 'resources' or 'trait'
            # 'suffix' is $N or None
            # 'name' is either the resource class name or the trait name.
            prefix, suffix, name = match.groups()

            # Process "resources[$N]"
            if prefix == cls.XS_RES_PREFIX:
                ret._add_resource(suffix, name, val)

            # Process "trait[$N]"
            elif prefix == cls.XS_TRAIT_PREFIX:
                ret._add_trait(suffix, name, val)

        return ret

    def resource_groups(self):
        for rg in self._rg_by_id.values():
            yield rg.resources

    def get_num_of_numbered_groups(self):
        return len([ident for ident in self._rg_by_id.keys()
                    if ident is not None])

    def merged_resources(self, resources=None):
        """Returns a merge of {resource_class: amount} for all resource groups.

        Amounts of the same resource class from different groups are added
        together.

        :param resources: A flat dict of {resource_class: amount}.  If
                          specified, the resources therein are folded
                          into the return dict, such that any resource
                          in resources is included only if that
                          resource class does not exist elsewhere in the
                          merged ResourceRequest.
        :return: A dict of the form {resource_class: amount}
        """
        ret = collections.defaultdict(lambda: 0)
        for resource_dict in self.resource_groups():
            for resource_class, amount in resource_dict.items():
                ret[resource_class] += amount
        if resources:
            for resource_class, amount in resources.items():
                # If it's in there - even if zero - ignore the one from the
                # flavor.
                if resource_class not in ret:
                    ret[resource_class] = amount
            # Now strip zeros.  This has to be done after the above - we can't
            # use strip_zeros :(
            ret = {rc: amt for rc, amt in ret.items() if amt}
        return dict(ret)

    def _clean_empties(self):
        """Get rid of any empty ResourceGroup instances."""
        for ident, rg in list(self._rg_by_id.items()):
            if not any((rg.resources, rg.required_traits,
                        rg.forbidden_traits)):
                self._rg_by_id.pop(ident)

    def strip_zeros(self):
        """Remove any resources whose amounts are zero."""
        for resource_dict in self.resource_groups():
            for rclass in list(resource_dict):
                if resource_dict[rclass] == 0:
                    resource_dict.pop(rclass)
        self._clean_empties()

    def to_querystring(self):
        """Produce a querystring of the form expected by
        GET /allocation_candidates.
        """
        # TODO(gibi): We have a RequestGroup OVO so we can move this to that
        # class as a member function.
        # NOTE(efried): The sorting herein is not necessary for the API; it is
        # to make testing easier and logging/debugging predictable.
        def to_queryparams(request_group, suffix):
            res = request_group.resources
            required_traits = request_group.required_traits
            forbidden_traits = request_group.forbidden_traits
            aggregates = request_group.aggregates
            in_tree = request_group.in_tree

            resource_query = ",".join(
                sorted("%s:%s" % (rc, amount)
                       for (rc, amount) in res.items()))
            qs_params = [('resources%s' % suffix, resource_query)]

            # Assemble required and forbidden traits, allowing for either/both
            # to be empty.
            required_val = ','.join(
                sorted(required_traits) +
                ['!%s' % ft for ft in sorted(forbidden_traits)])
            if required_val:
                qs_params.append(('required%s' % suffix, required_val))
            if aggregates:
                aggs = []
                # member_ofN is a list of lists.  We need a tuple of
                # ('member_ofN', 'in:uuid,uuid,...') for each inner list.
                for agglist in aggregates:
                    aggs.append(('member_of%s' % suffix,
                                 'in:' + ','.join(sorted(agglist))))
                qs_params.extend(sorted(aggs))
            if in_tree:
                qs_params.append(('in_tree%s' % suffix, in_tree))
            return qs_params

        if self._limit is not None:
            qparams = [('limit', self._limit)]
        else:
            qparams = []
        if self._group_policy is not None:
            qparams.append(('group_policy', self._group_policy))

        for ident, rg in self._rg_by_id.items():
            # [('resourcesN', 'rclass:amount,rclass:amount,...'),
            #  ('requiredN', 'trait_name,!trait_name,...'),
            #  ('member_ofN', 'in:uuid,uuid,...'),
            #  ('member_ofN', 'in:uuid,uuid,...')]
            qparams.extend(to_queryparams(rg, ident or ''))

        return parse.urlencode(sorted(qparams))

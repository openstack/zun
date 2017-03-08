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

import pecan

from zun.api.controllers import base
from zun.api.controllers import link
from zun.api.controllers import types


class Collection(base.APIBase):

    fields = {
        'next': {
            'validate': types.Text.validate,
        },
    }

    @property
    def collection(self):
        return getattr(self, self._type)

    def has_next(self, limit):
        """Return whether collection has more items."""
        return len(self.collection) and len(self.collection) == limit

    def get_next(self, limit, url=None, **kwargs):
        """Return a link to the next subset of the collection."""
        if not self.has_next(limit):
            return None

        resource_url = url or self._type
        q_args = ''.join(['%s=%s&' % (key, kwargs[key]) for key in kwargs])
        next_args = '?%(args)slimit=%(limit)d&marker=%(marker)s' % {
            'args': q_args, 'limit': limit,
            'marker': self.collection[-1].uuid}

        return link.make_link('next', pecan.request.host_url,
                              resource_url, next_args).href

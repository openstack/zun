# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from zun.common.docker_image import digest as digest_
from zun.common.docker_image import regexp
from zun.common import exception


ImageRegexps = regexp.ImageRegexps

NAME_TOTAL_LENGTH_MAX = 255


class Reference(dict):
    def __init__(self, name=None, tag=None, digest=None):
        super(Reference, self).__init__()
        self['name'] = name
        self['tag'] = tag
        self['digest'] = digest

    def split_hostname(self):
        name = self['name']
        matched = ImageRegexps.ANCHORED_NAME_REGEXP.match(name)

        if not matched:
            return '', name
        matches = matched.groups()
        if len(matches) != 2:
            return '', name
        hostname = matches[0]
        if hostname is None:
            return '', name
        if ('.' not in hostname and ':' not in hostname and
                hostname != 'localhost'):
            return '', name

        return matches[0], matches[1]

    def string(self):
        return '{}:{}@{}'.format(self['name'], self['tag'], self['digest'])

    def best_reference(self):
        if not self['name']:
            if self['digest']:
                return DigestReference(self['digest'])
            return None

        if not self['tag']:
            if self['digest']:
                return CanonicalReference(self['name'], self['digest'])
            return NamedReference(self['name'])

        if not self['digest']:
            return TaggedReference(self['name'], self['tag'])

        return self

    @classmethod
    def parse(cls, s):
        matched = ImageRegexps.REFERENCE_REGEXP.match(s)
        if not matched and not s:
            raise exception.NameEmpty()
        if not matched:
            raise exception.ReferenceInvalidFormat()

        matches = matched.groups()
        if len(matches[0]) > NAME_TOTAL_LENGTH_MAX:
            raise exception.NameTooLong(length_max=NAME_TOTAL_LENGTH_MAX)

        ref = cls(name=matches[0], tag=matches[1])
        if matches[2]:
            digest_.validate_digest(matches[2])
            ref['digest'] = matches[2]

        r = ref.best_reference()
        if not r:
            raise exception.NameEmpty()

        return r


class NamedReference(Reference):
    def __init__(self, name, **kwargs):
        super(NamedReference, self).__init__(name=name, **kwargs)

    def string(self):
        return '{}'.format(self['name'])


class DigestReference(Reference):
    def __init__(self, digest, **kwargs):
        super(DigestReference, self).__init__(digest=digest, **kwargs)

    def string(self):
        return self['digest']


class CanonicalReference(NamedReference):
    def __init__(self, name, digest, **kwargs):
        super(CanonicalReference, self).__init__(name=name, digest=digest,
                                                 **kwargs)

    def string(self):
        return '{}@{}'.format(self['name'], self['digest'])


class TaggedReference(NamedReference):
    def __init__(self, name, tag, **kwargs):
        super(TaggedReference, self).__init__(name=name, tag=tag, **kwargs)

    def string(self):
        return '{}:{}'.format(self['name'], self['tag'])

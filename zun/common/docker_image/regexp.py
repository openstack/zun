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

import re


def _quote_meta(s):
    special_chars = frozenset("()[]{}?*+|^$\\.-#&~")
    escape = lambda c: r'\{}'.format(c) if c in special_chars else c
    sp = (escape(c) for c in s)
    return r''.join(sp)


def match(regexp):
    return re.compile(regexp)


def literal(s):
    return match(_quote_meta(s))


def expression(*res):
    return match(r''.join(r.pattern for r in res))


def optional(*res):
    return match(r'{}?'.format(group(expression(*res)).pattern))


def repeated(*res):
    return match(r'{}+'.format(group(expression(*res)).pattern))


def group(*res):
    return match(r'(?:{})'.format(expression(*res).pattern))


def capture(*res):
    return match(r'({})'.format(expression(*res).pattern))


def anchored(*res):
    return match(r'^{}$'.format(expression(*res).pattern))


class ImageRegexps(object):
    ALPHA_NUMERIC_REGEXP = match(r'[a-z0-9]+')
    SEPARATOR_REGEXP = match(r'(?:[._]|__|[-]*)')
    NAME_COMPONENT_REGEXP = expression(
        ALPHA_NUMERIC_REGEXP,
        optional(repeated(SEPARATOR_REGEXP, ALPHA_NUMERIC_REGEXP))
    )
    HOSTNAME_COMPONENT_REGEXP = match(
        r'(?:[a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9])')
    HOSTNAME_REGEXP = expression(
        HOSTNAME_COMPONENT_REGEXP,
        optional(repeated(literal(r'.'), HOSTNAME_COMPONENT_REGEXP)),
        optional(literal(r':'), match(r'[0-9]+'))
    )
    TAG_REGEXP = match(r'[\w][\w.-]{0,127}')
    ANCHORED_TAG_REGEXP = anchored(TAG_REGEXP)
    DIGEST_REGEXP = match(r'[a-zA-Z0-9-_+.]+:[a-fA-F0-9]+')
    ANCHORED_DIGEST_REGEXP = anchored(DIGEST_REGEXP)
    NAME_REGEXP = expression(
        optional(HOSTNAME_REGEXP, literal(r'/')),
        NAME_COMPONENT_REGEXP,
        optional(repeated(literal(r'/'), NAME_COMPONENT_REGEXP))
    )
    ANCHORED_NAME_REGEXP = anchored(
        optional(capture(HOSTNAME_REGEXP), literal(r'/')),
        capture(NAME_COMPONENT_REGEXP,
                optional(repeated(literal(r'/'), NAME_COMPONENT_REGEXP)))
    )
    REFERENCE_REGEXP = anchored(
        capture(NAME_REGEXP),
        optional(literal(r':'), capture(TAG_REGEXP)),
        optional(literal(r'@'), capture(DIGEST_REGEXP))
    )


class DigestRegexps(object):
    DIGEST_REGEXP = match(r'[a-zA-Z0-9-_+.]+:[a-fA-F0-9]+')
    DIGEST_REGEXP_ANCHORED = anchored(DIGEST_REGEXP)

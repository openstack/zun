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

from zun.common.docker_image import regexp

DigestRegexps = regexp.DigestRegexps


class InvalidDigest(Exception):
    @classmethod
    def default(cls):
        return cls("invalid digest")


class DigestUnsupported(InvalidDigest):
    @classmethod
    def default(cls):
        return cls("unsupported digest algorithm")


class DigestInvalidLength(InvalidDigest):
    @classmethod
    def default(cls):
        return cls("invalid checksum digest length")


DIGESTS_SIZE = {
    'sha256': 32,
    'sha384': 48,
    'sha512': 64,
}


def validate_digest(digest):
    matched = DigestRegexps.DIGEST_REGEXP_ANCHORED.match(digest)
    if not matched:
        raise InvalidDigest.default()

    i = digest.find(':')
    # case: "sha256:" with no hex.
    if i < 0 or ((i + 1) == len(digest)):
        raise InvalidDigest.default()

    algorithm = digest[:i]
    if algorithm not in DIGESTS_SIZE:
        raise DigestUnsupported.default()

    if DIGESTS_SIZE[algorithm] * 2 != len(digest[i + 1:]):
        raise DigestInvalidLength.default()

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

import base64

from cryptography import fernet
from oslo_config import cfg
from oslo_utils import encodeutils

from zun.common import exception


def encrypt(value, encryption_key=None):
    if value is None:
        return None

    encryption_key = get_valid_encryption_key(encryption_key)
    encoded_key = base64.b64encode(encryption_key.encode('utf-8'))
    sym = fernet.Fernet(encoded_key)
    res = sym.encrypt(encodeutils.safe_encode(value))
    return encodeutils.safe_decode(res)


def decrypt(data, encryption_key=None):
    if data is None:
        return None

    encryption_key = get_valid_encryption_key(encryption_key)
    encoded_key = base64.b64encode(encryption_key.encode('utf-8'))
    sym = fernet.Fernet(encoded_key)
    try:
        value = sym.decrypt(encodeutils.safe_encode(data))
        if value is not None:
            return encodeutils.safe_decode(value, 'utf-8')
    except fernet.InvalidToken:
        raise exception.InvalidEncryptionKey()


def get_valid_encryption_key(encryption_key):
    if encryption_key is None:
        encryption_key = cfg.CONF.auth_encryption_key

    return encryption_key[:32]

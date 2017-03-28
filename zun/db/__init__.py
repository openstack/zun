# Copyright 2015 NEC Corporation.  All rights reserved.
#
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

from oslo_db import options

from zun.common import paths
import zun.conf

_DEFAULT_SQL_CONNECTION = 'sqlite:///' + paths.state_path_def('zun.sqlite')

options.set_defaults(zun.conf.CONF)
options.set_defaults(zun.conf.CONF, _DEFAULT_SQL_CONNECTION)

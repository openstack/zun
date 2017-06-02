# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import time


def wait_for_condition(condition, interval=2, timeout=60):
    start_time = time.time()
    end_time = time.time() + timeout
    while time.time() < end_time:
        result = condition()
        if result:
            return result
        time.sleep(interval)
    raise Exception(("Timed out after %s seconds.  Started on %s and ended "
                     "on %s") % (timeout, start_time, end_time))

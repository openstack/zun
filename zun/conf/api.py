#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

from oslo_config import cfg


api_service_opts = [
    cfg.PortOpt('port',
                default=9517,
                help='The port for the zun API server.'),
    cfg.IPOpt('host_ip',
              default='$my_ip',
              help="The listen IP for the zun API server. "
                   "The default is ``$my_ip``, "
                   "the IP address of this host."),
    cfg.BoolOpt('enable_ssl_api',
                default=False,
                help="Enable the integrated stand-alone API to service "
                     "requests via HTTPS instead of HTTP. If there is a "
                     "front-end service performing HTTPS offloading from "
                     "the service, this option should be False; note, you "
                     "will want to change public API endpoint to represent "
                     "SSL termination URL with 'public_endpoint' option."),
    cfg.IntOpt('workers',
               help="Number of workers for zun-api service. "
                    "The default will be the number of CPUs available."),
    cfg.IntOpt('max_limit',
               default=1000,
               help='The maximum number of items returned in a single '
                    'response from a collection resource.'),
    cfg.StrOpt('api_paste_config',
               default="api-paste.ini",
               help="Configuration file for WSGI definition of API."),
    cfg.BoolOpt('enable_image_validation',
                default=True,
                help="Enable image validation.")
]


api_group = cfg.OptGroup(name='api',
                         title='Options for the zun-api service')


ALL_OPTS = (api_service_opts)


def register_opts(conf):
    conf.register_group(api_group)
    conf.register_opts(ALL_OPTS, api_group)


def list_opts():
    return {
        api_group: ALL_OPTS
    }

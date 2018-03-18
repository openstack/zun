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

from oslo_config import cfg

from zun.conf import path

image_driver_opts = [
    cfg.ListOpt(
        'image_driver_list',
        default=['glance', 'docker'],
        help="""Defines the list of image driver to use for downloading image.
Possible values:
* ``docker``
* ``glance``
Services which consume this:
* ``zun-compute``
Interdependencies to other options:
* None
"""),
    cfg.StrOpt(
        'default_image_driver',
        default='docker',
        help='The default container image driver to use.'),
]

sandbox_opts = [
    cfg.StrOpt(
        'sandbox_image',
        default='kubernetes/pause',
        help='Container image for sandbox container.'),
    cfg.StrOpt(
        'sandbox_image_driver',
        default='docker',
        help='Image driver for sandbox container.'),
    cfg.StrOpt(
        'sandbox_image_pull_policy',
        default='ifnotpresent',
        help='Image pull policy for sandbox image.'),
]

glance_driver_opts = [
    cfg.StrOpt(
        'images_directory',
        default=path.state_path_def('images'),
        help='Shared directory where glance images located. If '
             'specified, docker will try to load the image from '
             'the shared directory by image ID.'),
]

glance_opt_group = cfg.OptGroup(name='glance',
                                title='Glance options for image management')

DEFAULT_OPTS = (image_driver_opts + sandbox_opts)
GLANCE_OPTS = (glance_driver_opts)


def register_opts(conf):
    conf.register_group(glance_opt_group)
    conf.register_opts(glance_driver_opts, group=glance_opt_group)
    conf.register_opts(image_driver_opts)
    conf.register_opts(sandbox_opts)


def list_opts():
    return {"DEFAULT": DEFAULT_OPTS, glance_opt_group: GLANCE_OPTS}

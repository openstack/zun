To generate the sample higgins.conf file, run the following
command from the top level of the higgins directory:

tox -egenconfig

Or you can generate the sample higgins.conf file in global
environment, run the following command from the top level
of the higgins directory:

pip install oslo.config
oslo-config-generator --config-file \
                etc/higgins/higgins-config-generator.conf

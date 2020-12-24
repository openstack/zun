====================
Policy configuration
====================

Configuration
~~~~~~~~~~~~~

.. warning::

   JSON formatted policy file is deprecated since Zun 7.0.0 (Wallaby).
   This `oslopolicy-convert-json-to-yaml`__ tool will migrate your existing
   JSON-formatted policy file to YAML in a backward-compatible way.

.. __: https://docs.openstack.org/oslo.policy/latest/cli/oslopolicy-convert-json-to-yaml.html

The following is an overview of all available policies in Zun. For a sample
configuration file.

.. show-policy::
   :config-file: ../../etc/zun/zun-policy-generator.conf

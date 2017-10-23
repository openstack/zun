Continuous Integration with Jenkins
===================================

Zun uses a `Jenkins <http://jenkins-ci.org>`_ server to automate development
tasks.

Jenkins performs tasks such as:

`gate-zun-pep8-ubuntu-xenial`
    Run PEP8 checks on proposed code changes that have been reviewed.

`gate-zun-python27-ubuntu-xenial`
    Run unit tests using python2.7 on proposed code changes that have been
    reviewed.

`gate-zun-python35`
    Run unit tests using python3.5 on proposed code changes that have been
    reviewed.

`gate-zun-docs-ubuntu-xenial`
    Build this documentation and push it to `OpenStack Zun
    <https://docs.openstack.org/zun/latest/>`_.

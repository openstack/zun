vagrant-devstack-zun
=======================

A Vagrant-based devstack setup for zun.
Steps to try vagrant image:
1. Install virtual-box and vagrant on your local machine.
2. Git clone zun repository.
3. cd zun/contrib/vagrant
4. vagrant up
   It will take around 20 mins.
5. vagrant ssh
   You will get vm shell with all necessary setup.

Note: For enabling/disabling various services, please see below file:
      zun/contrib/vagrant/config/localrc

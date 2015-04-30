Installing the Undercloud
==========================

#. Log in to your machine (baremetal or VM) where you want to install the
   undercloud as a non-root user (such as the stack user)::

       ssh <non-root-user>@<rdo-manager-machine>

   .. note::
      If you don't have a non-root user created yet, log in as root and create
      one with following commands::

          sudo useradd stack
          sudo passwd stack  # specify a password

          echo "stack ALL=(root) NOPASSWD:ALL" | sudo tee -a /etc/sudoers.d/stack
          sudo chmod 0440 /etc/sudoers.d/stack

          su - stack

   .. admonition:: Baremetal
      :class: baremetal

      Ensure that there is a FQDN hostname set and that the $HOSTNAME environment
      variable matches that value.

      Use ``hostnamectl`` to set a hostname if needed::

          sudo hostnamectl set-hostname myhost.mydomain
          sudo hostnamectl set-hostname --transient myhost.mydomain

      An entry for the system's FQDN hostname is also needed in /etc/hosts. For
      example, if the system is named *myhost.mydomain*, /etc/hosts should have
      an entry like::

         127.0.0.1   myhost.mydomain


#. Enable needed repositories:

   .. only:: internal

      .. admonition:: RHEL
         :class: rhel

          Enable rhos-release::

              sudo yum install -y http://rhos-release.virt.bos.redhat.com/repos/rhos-release/rhos-release-latest.noarch.rpm
              sudo rhos-release 6

              # We need openwsman-python from the optional repo
              sudo yum install -y yum-utils
              sudo yum-config-manager --enable rhelosp-rhel-7-server-opt

   ::

       # Enable RDO Kilo
       sudo yum install -y https://rdoproject.org/repos/openstack-kilo/rdo-release-kilo.rpm

       # Enable RDO-Manager Trunk
       sudo curl -o /etc/yum.repos.d/rdo-management-trunk.repo http://trunk-mgt.rdoproject.org/centos-kilo/current-passed-ci/delorean-rdo-management.repo


#. Install the unified CLI (also installs instack-undercloud as a dependency)::

    sudo yum install -y python-rdomanager-oscplugin


#. Run the script to install the undercloud:

  .. admonition:: Baremetal
     :class: baremetal

     Copy in the sample configuration file and edit it to reflect your environment::

        cp /usr/share/instack-undercloud/undercloud.conf.sample ~/undercloud.conf


  Install the undercloud::

      openstack undercloud install


Once the install has completed, you should take note of the files ``stackrc`` and
``undercloud-passwords.conf``.  You can source ``stackrc`` to interact with the
undercloud via the OpenStack command-line client.  ``undercloud-passwords.conf``
contains the passwords used for each service in the undercloud.  These passwords
will be automatically reused if the undercloud is reinstalled on the same system,
so it is not necessary to copy them to ``undercloud.conf``.

.. note::
    Any passwords set in ``undercloud.conf`` will take precedence over the ones in
    ``undercloud-passwords.conf``.

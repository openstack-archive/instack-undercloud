Installing the Undercloud
=========================

Make sure you are logged in as a non-root user (such as the stack user) on the
node on which you want to install the undercloud.

.. admonition:: Virtual
   :class: virtual

   This node will be a VM called *instack* and you can use the stack user.

.. admonition:: Baremetal
   :class: baremetal

   This will be the host you selected for the Undercloud while preparing the environment.

#. Download and execute the instack-undercloud setup script:

   .. only:: internal

      .. admonition:: RHEL
         :class: rhel

          Enable rhos-release::

              export RUN_RHOS_RELEASE=1
   ::

    curl https://raw.githubusercontent.com/rdo-management/instack-undercloud/master/scripts/instack-setup-host | bash -x

#. Install instack-undercloud::

    sudo yum install -y instack-undercloud

#. Run script to install the undercloud:

  .. note:: Ensure that there is an entry for the system's full hostname in /etc/hosts.
     For example, if the system is named *myhost.mydomain*, /etc/hosts should have
     an entry like::

        127.0.0.1   myhost.mydomain

  .. admonition:: Baremetal
     :class: baremetal

     Copy in the sample answers file and edit it to reflect your environment::

        cp /usr/share/instack-undercloud/instack.answers.sample ~/instack.answers


  ::

    instack-install-undercloud

Once the install script has run to completion, you should take note of the
files ``/root/stackrc`` and ``/root/tripleo-undercloud-passwords``. Both these
files will be needed to interact with the installed undercloud. Copy them to
the home directory for easier use later.::

    sudo cp /root/tripleo-undercloud-passwords .
    sudo cp /root/stackrc .


Updating the Undercloud
-----------------------

The installed packages can be upgraded on the Undercloud.

#. Rerun the setup script to update the list of defined yum repositories::

    instack-setup-host

#. Use yum to update the installed packages. No services should need to be
   restarted after updating::

    sudo yum update -y

Installing the Undercloud
=========================

Make sure you are logged in as a non-root user (such as the stack user) on the
node on which you want to install the undercloud.

If you used the virt setup this node will be a VM called *instack* and you can
use the stack user.

For a baremetal setup this will be the host you selected for the Undercloud
while preparing the environment.

#. Download and execute the instack-undercloud setup script::

    curl https://raw.githubusercontent.com/rdo-management/instack-undercloud/master/scripts/instack-setup-host | bash -x

#. Install instack-undercloud::

    sudo yum install -y instack-undercloud

#. If installing on baremetal, copy in the sample answers file and edit it
   to reflect your environment::

    cp /usr/share/instack-undercloud/instack.answers.sample ~/instack.answers

#. Run script to install the undercloud::

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

    sudo yum update

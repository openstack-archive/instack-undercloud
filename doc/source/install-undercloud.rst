Installing the Undercloud
=========================

Make sure you are logged in as a non-root user (such as the stack user) on the
node on which you want to install the undercloud.

If you used the virt setup this node will be a VM called *instack* and you can
use the stack user.

For a baremetal setup this will be the host you selected for the Undercloud
while preparing the environment.

#. Download and execute the instack-undercloud setup script::

    curl https://raw.githubusercontent.com/rdo-management/instack-undercloud/master/scripts/instack-setup-host-rhel7 | bash -x

#. Install instack-undercloud::

    sudo yum install instack-undercloud

#. Source rhel7rc to set appropriate environment variables::

    source /usr/share/instack-undercloud/rhel7rc

#. Run script to install the undercloud::

    instack-install-undercloud

Once the install script has run to completion, you should take note of the
files ``/root/stackrc`` and ``/root/tripleo-undercloud-passwords``. Both these
files will be needed to interact with the installed undercloud. Copy them to
the home directory for easier use later.::

    sudo cp /root/tripleo-undercloud-passwords .
    sudo cp /root/stackrc .

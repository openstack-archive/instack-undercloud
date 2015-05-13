Updating Undercloud Components
------------------------------

You can upgrade any packages that are installed on the undercloud machine.

#. Update the RDO-Manager Trunk repository::


       # Remove old and enable new RDO-Manager Trunk
       sudo rm /etc/yum.repos.d/rdo-management-trunk.repo
       sudo curl -o /etc/yum.repos.d/rdo-management-trunk.repo http://trunk-mgt.rdoproject.org/centos-kilo/current-passed-ci/delorean-rdo-management.repo

#. Use yum to update all installed packages::

    sudo yum update -y

    # You can specify the package names to update as options in the yum update command.

You do not need to restart any services after you update.

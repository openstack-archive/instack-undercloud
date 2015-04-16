Updating Undercloud Components
------------------------------

You can upgrade any packages that are installed on the undercloud machine.

#. Re-run the setup script to update the list of defined yum repositories::

    instack-setup-host

#. Use yum to update all installed packages::

    sudo yum update -y

    # You can specify the package names to update as options in the yum update command.

You do not need to restart any services after you update.

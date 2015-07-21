Accessing the GUI
=================

Part of the Undercloud installation is also Tuskar-UI which you can use to drive
the deployment. It runs on the instack virtual machine on ``http://localhost/dashboard``


Example of how to access Tuskar-UI:
-----------------------------------

Considering that Tuskar-UI runs in a instack VM and virt host is a remote host
machine, to access the UI in the browser, follow these steps:

#. On host machine create ssh tunnel from instack vm to virt host::

    ssh -g -N -L 8080:127.0.0.1:80 root@<undercloud_vm_ip>

#. On instack VM edit ``/etc/openstack-dashboard/local_settings`` and add virt host ``hostname`` to ``ALLOWED_HOSTS`` array

#. Restart Apache::

    systemctl restart httpd

#. Allow port ``8080`` on host machine::

    sudo iptables -I INPUT -p tcp -m tcp --dport 8080 -j ACCEPT

#. Navigate to ``http://<virt_host_hostname>:8080/dashboard`` in the browser

When logging into the dashboard the default user and password are found in the ``/root/stackrc`` file on the instack virtual machine, ``OS_USERNAME`` and ``OS_PASSWORD``.

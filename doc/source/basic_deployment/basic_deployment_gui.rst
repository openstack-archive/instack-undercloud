Basic Deployment (GUI)
======================


Access the GUI
--------------

Part of the Undercloud installation is also Tuskar-UI which you can use to drive
the deployment.


.. admonition:: Virtual
   :class: virtual

   In the case of a virtual deployment, Tuskar-UI runs on the instack virtual
   machine on ``http://localhost/dashboard``. Considering this and the fact that
   the virt host is a remote host machine, to access the UI in the browser,
   follow these steps:

   #. On host machine create ssh tunnel from instack vm to virt host::

       ssh -g -N -L 8080:127.0.0.1:80 root@<undercloud_vm_ip>

   #. On instack VM edit ``/etc/openstack-dashboard/local_settings`` and add virt host ``hostname`` to ``ALLOWED_HOSTS`` array

   #. Restart Apache::

       systemctl restart httpd

   #. Navigate to ``http://<virt_host_hostname>:8080/dashboard`` in the browser

When logging into the dashboard the default user and password are found in the ``/root/stackrc`` file on the instack virtual machine, ``OS_USERNAME`` and ``OS_PASSWORD``.

After logging into the dashboard, make sure that the project is set to *admin* (if it is not, change the project to *admin* using the Project switcher at the top bar).


Overview Page
-------------
When you log into the GUI, you will land on the *Overview* page. This page contains all the information about the
current state of the deployment. On the left side, there is a list of available deployment roles. On the right side,
there is a deployment checklist which indicates whether all the prerequisites for the deployment have been satisfied.

Get Images
----------

To perform a successful deployment, you will need the following images: discovery ramdisk, deployment ramdisk, and
openstack-full image. To upload the images and load them into Glance, navigate to *Provisioning Images* and use the
*Create Image* button to create the necessary images. You will need to following image files handy::

    overcloud-full.vmlinuz
    overcloud-full.initrd
    overcloud-full.qcow2
    deploy-ramdisk-ironic.kernel
    deploy-ramdisk-ironic.initramfs
    discovery-ramdisk.kernel
    discovery-ramdisk.initramfs

To create the 'overcloud-full-vmlinuz' image, fill the *Create Image* form like so::

    Name: overcloud-full-vmlinuz
    Image Source: Image File
    Image File: overcloud-full.vmlinuz
    Format: AKI
    Public: checked

To create the 'overcloud-full-initrd' image, fill the *Create Image* form like so::

    Name: overcloud-full-initrd
    Image Source: Image File
    Image File: overcloud-full.initrd
    Format: ARI
    Public: checked

To create the 'overcloud-full' image, fill the *Create Image* form like so::

    Name: overcloud-full
    Image Source: Image File
    Image File: overcloud-full.qcow2
    Kernel: overcloud-full-vmlinuz
    Ramdisk: overcloud-full-initrd
    Format: QCOW2
    Public: checked

To create the 'bm-deploy-kernel' image, fill the *Create Image* form like so::

    Name: bm-deploy-kernel
    Image Source: Image File
    Image File: deploy-ramdisk-ironic.kernel
    Format: AKI
    Public: checked

To create the 'bm-deploy-ramdisk' image, fill the *Create Image* form like so::

    Name: bm-deploy-ramdisk
    Image Source: Image File
    Image File: deploy-ramdisk-ironic.initramfs
    Format: ARI
    Public: checked

You will also need to copy the discovery images to HTTP BOOT directory on the undercloud node. Assuming you have these
images handy in your home directory on the undercloud node, run the following commands to copy them to /httpboot::

    sudo cp -f discovery-ramdisk.kernel /httpboot/discovery.kernel
    sudo cp -f discovery-ramdisk.initramfs /httpboot/discovery.ramdisk


Register Nodes
--------------

To register nodes for your deployment, navigate to the *Nodes* page, and click the + sign to open the *Register Nodes* form.
This form gives you a choice of manually adding node data using the *Add* link, or supplying a CSV file with node data
using the *Upload* link. Choose one of these two options to register your nodes with Ironic. Make sure you provide, at
minimum, the *Power Management* properties, the *MAC address(es)* for the nodes and the *Deployment Images*. The rest of the
attributes are optional and in case you don't supply them, they will be obtained by running the introspection on the
nodes. When you have finished providing the node data, click the *Register Nodes* button to register your nodes.

.. note::
   When using a CSV file to upload node data, make sure the fields are in this order::

       driver,address,username,password/ssh key,mac addresses,cpu architecture,number of CPUs,available memory,available storage


   As stated above, hardware properties (cpu architecture, number of CPUs, available memory, available storage)
   are not mandatory, and in case they are not provided in the CSV file, they will be obtained via introspection.

   Here are the contents of an example CSV file to register two virtual nodes::

       pxe_ssh,192.168.122.1,root,"-----BEGIN RSA PRIVATE KEY-----
       MIIEowIBAAKCAQEAw6J6supEV40toLTiH6Taj8k6bI2CSJSK31spMfLIKzPuvzCV
       PGZdhKMx1o++u9TcFFh7U1caojg1Jj/XKdPcktGBQvAmiNa9nybmTjiOqq/b1svr
       W1Yn23WvkEBL7peFUZVAgJDvxcf42LtA72RdgzegFdrP0y4z6UJlJRnxAckxfa/o
       b05N3nrK2yteZQVuMBVB2P7QAgy62aIqJBacWrLplaZMJZZYQJ9ialXZXAMPIN3P
       5l9emMOJjBbXv76G6B/Ik9J6Ryv8SFhQbLzWu1eXjT8g3d5KlD/lvh6fwN/HjYOb
       6o5LvMD61vpOaR0B8Ta/+vu4R+GiLB+ArhS9WQIDAQABAoIBAAUWLGqKfMxp902+
       ZkK8XpJugP5hj4mjkxjLnf6WeW3mI8cE1FyFrNjOBXW2txbbKf29bzdzhFXDcF5W
       Opnz0EBhAiNjax0TuEpzEHnoLo1xlR24n534V4D1RmNRyKejeOvuHYc6PYG++VFp
       TP7sdSH8SEVJMy4ifWcLOuYEDqglL1uSPQgO8HkmlvOvgI1LnLx9wjeNC1D7weZu
       Eh75GTGRLL8i0X0bLmaNZ1Fs3Ge2tLNS0hfu6epCiT3ZAQTBVyFbVmN6btnQ/BHM
       nDSZQ2JEDjQByCiBch9hTk/V2UNmn5dOUGPTwp2IP5Blpq2X7u1IoXQiAhI+zVcN
       9mqbK6ECgYEA9hbQF7iEP4RhClNUVmQJd1zQjC2D5Vj0ik68MdgcT1QFrrCGaRPb
       eayCxyDoNyUAWGtqToTQ5v3b1dxwsJryMekHD0OL75fl1KbD0bRiawVG81QbyC3U
       I05Lr5LCdm80xdktC6caIkpoRF6e9xhAQduXDHZyQ6TdJtRHS6E3uPsCgYEAy4N6
       xFml63vk2qFPyMkSfp82ey6YiGchXxZSDl/tDiDDHgDVRtYi5+7iCNVrjkwtUXI3
       zK+G+m74AIx1C9ZSW81y5ymxKLGz1+OUy3Vtp0Zf5R1/Q+l9I4sl1dkB2wJcb2Ls
       2A3yl9NEt5M3bHZUQk4ttmhfqOFiSmNd/uFbersCgYEAvlAYMDAPfnum/HBDKeiF
       dZz+31mXxjeMLqYDXtzNz/+fwWBdIkgsFKX4IX1ueK8R3E990Clg0TMD3xlywPGj
       WjvnrMNFJk6nfFRX3gaNkkxreWTTc3UVuRQk7iwmXadU/akd8AQT7u7yQeWXNGq5
       zvS+lPHJHk0ShqPmWzPbvx8CgYBAiB9slXSsN+v4e4AeDcwkhH21D7BkSDdnvF8m
       mbpEaZUVNXRrcsk8vB3GaU4in/sawVn6OIpXbMqM+fy/VSVmYL4XmLvJSJfbVBnB
       binoCcOsle7d7PK2S5AiwB37gUMoOrkZRUrwY5h9kVvYs6jCIaITHgN/PIB7UAjl
       IjZsswKBgC9AgnXvw4M1bcS1SK1WdJXACrmfX5tGMLzCEVJgmJtiWobvpNsfcZ/Q
       EanIrYxnJ1zWZstefEuLWGzja+xwL/rsnTl77DPuvZRr/QxXMRaPFn5VTnH5kh0y
       9FlihAmgG1n2k3CCFNtdxAKBqPGLz2wUuRDHYhF4WKYuvghIpQA7
       -----END RSA PRIVATE KEY-----",00:d1:2c:a2:ed:58
       pxe_ssh,192.168.122.1,root,"-----BEGIN RSA PRIVATE KEY-----
       MIIEowIBAAKCAQEAw6J6supEV40toLTiH6Taj8k6bI2CSJSK31spMfLIKzPuvzCV
       PGZdhKMx1o++u9TcFFh7U1caojg1Jj/XKdPcktGBQvAmiNa9nybmTjiOqq/b1svr
       W1Yn23WvkEBL7peFUZVAgJDvxcf42LtA72RdgzegFdrP0y4z6UJlJRnxAckxfa/o
       b05N3nrK2yteZQVuMBVB2P7QAgy62aIqJBacWrLplaZMJZZYQJ9ialXZXAMPIN3P
       5l9emMOJjBbXv76G6B/Ik9J6Ryv8SFhQbLzWu1eXjT8g3d5KlD/lvh6fwN/HjYOb
       6o5LvMD61vpOaR0B8Ta/+vu4R+GiLB+ArhS9WQIDAQABAoIBAAUWLGqKfMxp902+
       ZkK8XpJugP5hj4mjkxjLnf6WeW3mI8cE1FyFrNjOBXW2txbbKf29bzdzhFXDcF5W
       Opnz0EBhAiNjax0TuEpzEHnoLo1xlR24n534V4D1RmNRyKejeOvuHYc6PYG++VFp
       TP7sdSH8SEVJMy4ifWcLOuYEDqglL1uSPQgO8HkmlvOvgI1LnLx9wjeNC1D7weZu
       Eh75GTGRLL8i0X0bLmaNZ1Fs3Ge2tLNS0hfu6epCiT3ZAQTBVyFbVmN6btnQ/BHM
       nDSZQ2JEDjQByCiBch9hTk/V2UNmn5dOUGPTwp2IP5Blpq2X7u1IoXQiAhI+zVcN
       9mqbK6ECgYEA9hbQF7iEP4RhClNUVmQJd1zQjC2D5Vj0ik68MdgcT1QFrrCGaRPb
       eayCxyDoNyUAWGtqToTQ5v3b1dxwsJryMekHD0OL75fl1KbD0bRiawVG81QbyC3U
       I05Lr5LCdm80xdktC6caIkpoRF6e9xhAQduXDHZyQ6TdJtRHS6E3uPsCgYEAy4N6
       xFml63vk2qFPyMkSfp82ey6YiGchXxZSDl/tDiDDHgDVRtYi5+7iCNVrjkwtUXI3
       zK+G+m74AIx1C9ZSW81y5ymxKLGz1+OUy3Vtp0Zf5R1/Q+l9I4sl1dkB2wJcb2Ls
       2A3yl9NEt5M3bHZUQk4ttmhfqOFiSmNd/uFbersCgYEAvlAYMDAPfnum/HBDKeiF
       dZz+31mXxjeMLqYDXtzNz/+fwWBdIkgsFKX4IX1ueK8R3E990Clg0TMD3xlywPGj
       WjvnrMNFJk6nfFRX3gaNkkxreWTTc3UVuRQk7iwmXadU/akd8AQT7u7yQeWXNGq5
       zvS+lPHJHk0ShqPmWzPbvx8CgYBAiB9slXSsN+v4e4AeDcwkhH21D7BkSDdnvF8m
       mbpEaZUVNXRrcsk8vB3GaU4in/sawVn6OIpXbMqM+fy/VSVmYL4XmLvJSJfbVBnB
       binoCcOsle7d7PK2S5AiwB37gUMoOrkZRUrwY5h9kVvYs6jCIaITHgN/PIB7UAjl
       IjZsswKBgC9AgnXvw4M1bcS1SK1WdJXACrmfX5tGMLzCEVJgmJtiWobvpNsfcZ/Q
       EanIrYxnJ1zWZstefEuLWGzja+xwL/rsnTl77DPuvZRr/QxXMRaPFn5VTnH5kh0y
       9FlihAmgG1n2k3CCFNtdxAKBqPGLz2wUuRDHYhF4WKYuvghIpQA7


Introspect Nodes
----------------

When registering nodes as described above, if you leave out any of the hardware properties for any of the nodes,
introspection will be run on the nodes to obtain these missing properties, as soon as you click the *Register Nodes*
button. In this case, the nodes will be located in the *Maintenance* tab and will have the status *Discovering*. After
the introspection process has finished (this can take up to 5 minutes for VM / 15 minutes for baremetal), the hardware
properties will get populated and the nodes will have the status *Discovered*. At this point, you can move the nodes
to the *Free* tab, by selecting them using the checkbox on the left side and clicking the *Activate Nodes* button. Now
the nodes are ready and available for deployment.


Create Flavors
--------------

To create the necessary flavor, navigate to the *Flavors* page. One suggested flavor, matching the hardware properties
of the created nodes, will be available. To create it, open the dropdown menu under *Actions*, click *Edit before creating*,
change the name to 'baremetal' and click the *Create Flavors* button.


Configure Roles
---------------

To configure deployment roles, navigate to the *Deployment Roles* page. *Flavor* and *Image* needs to be set to all the
deployment roles. For each of the deployment roles, click the *edit* button and set the *Flavor* to 'baremetal' and
*Image* to 'overcloud-full'. Save the form.


Service Configuration
---------------------

To perform the necessary service configuration, navigate to the *Service Configuration* page and click the
*Simplified Configuration* button. In the *Service Configuration* form, make sure that the values of the *Deployment Type*
and *Public Interface* fields are correct. Also make sure you set the *SNMP Password* and the *Cloud name*.


Deploy the Overcloud
--------------------

To deploy the overcloud, navigate to the *Overview* page. The deployment plan validation will be performed and if the
plan is valid, the *Verify and Deploy* button will be enabled. Click this button to open the deployment confirmation
dialog. In case you want to enable network isolation, check the *Enable Network Isolation* box. Click *Deploy*.

This will trigger the creation of the overcloud heat stack. The page will reload and you will be able to monitor the
current status of the deployment. On the right side you will see the progress bar as well as the last event from
the Heat event list. If you want to see the full event list, you can navigate to the *Deployment Log* page.


Initialize the Overcloud
------------------------

Once the deployment has successfully completed, you need to perform the initialization of Keystone and Neutron in the
overcloud. To do this, click the *Initialize* button, fill out the form and click *Initialize*. Once the initialization has
completed, the page will reload and you will see deployment details on the *Overview* page. On the left side the
information about roles and node counts will be displayed, along with the system load charts for each deployment role.
On the right side, the access information for the overcloud Horizon will be displayed.


Post-Deployment
---------------


Access the Overcloud
^^^^^^^^^^^^^^^^^^^^

When the overcloud is deployed, the access information needed to to log into the overcloud Horizon is located on
the *Overview* page.


Redeploy the Overcloud
^^^^^^^^^^^^^^^^^^^^^^

The overcloud can be redeployed when desired. First, you have to delete the existing overcloud by clicking the
*Undeploy* button on the *Overview* page. This will trigger the deletion of the Heat stack. After the overcloud has been
deleted, the *Overview* page will again display the deployment checklist along with the *Verify and Deploy* button. If you
wish to deploy the overcloud again, repeat the steps from the *Deploy the Overcloud* section on this page.

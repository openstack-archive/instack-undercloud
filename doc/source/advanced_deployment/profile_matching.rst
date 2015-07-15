Advanced Profile Matching
=========================

Here are additional setup steps to take advantage of the advanced profile
matching and the AHC features.

Enable advanced profile matching
--------------------------------

* Install the ahc-tools package::

    sudo yum install -y ahc-tools

* Add the credentials for Ironic and Swift to the
  **/etc/ahc-tools/ahc-tools.conf** file.
  These will be the same credentials that ironic-discoverd uses,
  and can be copied from **/etc/ironic-discoverd/discoverd.conf**::

    $ sudo -i
    # mkdir -p /etc/ahc-tools
    # sed 's/\[discoverd/\[ironic/' /etc/ironic-discoverd/discoverd.conf > /etc/ahc-tools/ahc-tools.conf
    # chmod 0600 /etc/ahc-tools/ahc-tools.conf
    # exit

  Example::

    [ironic]
    os_auth_url = http://192.0.2.1:5000/v2.0
    os_username = ironic
    os_password = <PASSWORD>
    os_tenant_name = service

    [swift]
    os_auth_url = http://192.0.2.1:5000/v2.0
    os_username = ironic
    os_password = <PASSWORD>
    os_tenant_name = service

Accessing additional introspection data
---------------------------------------

Every introspection run (as described in
:doc:`../basic_deployment/basic_deployment`) collects a lot of additional
facts about the hardware and puts them as JSON in Swift. Swift container name
is ``ironic-inspector`` and can be modified in
**/etc/ironic-discoverd/discoverd.conf**. Swift object name is stored under
``hardware_swift_object`` key in Ironic node extra field.

State file
----------

Configuration file **/etc/ahc-tools/edeploy/state** defines how many nodes of
each profile we want to match. This file contains list of tuples with profile
name and number of nodes for this profile. ``*`` symbol can be used to match
any number, but make sure that such tuple will go last.

For example to start with 1 control node and any number of compute ones,
populate this file with the following contents::

    [('control', '1'), ('compute', '*')]

Matching rules
--------------

These matching rules will determine what profile gets assigned to each node
and are stored in files named **/etc/ahc-tools/edeploy/PROFILE.specs** for
each profile defined in **/etc/ahc-tools/edeploy/state**.

Open the **/etc/ahc-tools/edeploy/control.specs** file.
This is a JSON-like file that might look like this::

      [
       ('disk', '$disk', 'size', 'gt(4)'),
       ('network', '$eth', 'ipv4', 'network(192.0.2.0/24)'),
       ('memory', 'total', 'size', 'ge(4294967296)'),
      ]

These rules match on the data collected during introspection.
Note that disk size is in GiB, while memory size is in KiB.

There is a set of helper functions to make matching more flexible.

* network() : the network interface shall be in the specified network
* gt(), ge(), lt(), le() : greater than (or equal), lower than (or equal)
* in() : the item to match shall be in a specified set
* regexp() : match a regular expression
* or(), and(), not(): boolean functions. or() and and() take 2 parameters
  and not() one parameter.

There are also placeholders, *$disk* and *$eth* in the above example.
These will store the value in that place for later use.

* For example if we had a "fact" from discovery::

    ('disk', 'sda', 'size', '40')

This would match the first rule in the above control.specs file,
and we would store ``"disk": "sda"``.

Running advanced profile matching
---------------------------------

* After adjusting the matching rules, we are ready to do the matching::

      sudo ahc-match

* This will attempt to match all of the available nodes to the roles
  we have defined in the **/etc/ahc-tools/edeploy/state** file.
  When a node matches a role, the role is added to the node in Ironic in
  the form of a capability. We can check this with ``ironic node-show``::

        [stack@instack ~]# ironic node-show b73fb5fa-1a2c-49c6-b38e-8de41e3c0532 | grep properties -A2
        | properties             | {u'memory_mb': u'4096', u'cpu_arch': u'x86_64', u'local_gb': u'40',      |
        |                        | u'cpus': u'1', u'capabilities': u'profile:control,boot_option:local'}    |
        | instance_uuid          | None

* In the above output, we can see that the control profile is added
  as a capability to the node. Next we will need to create flavors in Nova
  that actually map to these profiles.

Create flavors to use advanced matching
---------------------------------------

In order to use the profiles assigned to the Ironic nodes, Nova needs to have
flavors that have the property "capabilities:profile" set to the intended profile.

For example, with just the compute and control profiles:

* Create the flavors

  ::

    openstack flavor create --id auto --ram 4096 --disk 40 --vcpus 1 control
    openstack flavor create --id auto --ram 4096 --disk 40 --vcpus 1 compute

.. note::

  The values for ram, disk, and vcpus should be set to a minimal lower bound,
  as Nova will still check that the Ironic nodes have at least this much
  even if we set lower properties in the **.specs** files.

* Assign the properties

  ::

    openstack flavor set --property "cpu_arch"="x86_64" --property "capabilities:boot_option"="local" --property "capabilities:profile"="compute" compute
    openstack flavor set --property "cpu_arch"="x86_64" --property "capabilities:boot_option"="local" --property "capabilities:profile"="control" control


Use the flavors to deploy
-------------------------

By default, all nodes are deployed to the **baremetal** flavor.
The RDO-Manager CLI has options to support more advanced role matching.

Continuing with the example with only a control and compute profile:

* Get the Tuskar plan name

  ::

    openstack management plan list

* Deploy the overcloud

  ::

    openstack overcloud deploy --control-flavor control --compute-flavor compute --plan <Name or UUID from above>


Use the flavors to scale
-------------------------

The process to scale an overcloud that uses our advanced profiles is the same
as the process used when we only have the **baremetal** flavor.

.. note::

  The original overcloud must have been deployed as above in order to scale
  using advanced profiles, as the flavor to role mapping happens then.

* Update the **/etc/ahc-tools/edeploy/state** file to match the number
  of nodes we want to match to each role.

* Run `sudo ahc-match` to match available nodes to the defined roles.

* Scale the overcloud (example below adds two more nodes to the compute role)

  ::

    openstack overcloud scale stack overcloud overcloud -r Compute-1 -n 2


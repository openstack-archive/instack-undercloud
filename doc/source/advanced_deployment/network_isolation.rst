Configuring Network Isolation
=============================

Introduction
------------

RDO-Manager provides configuration of isolated overcloud networks. Using
this approach it is possible to host traffic for specific types of network
traffic (tenants, storage, API/RPC, etc.) in isolated networks. This allows
for assigning network traffic to specific network interfaces or bonds. Using
bonds provides fault tolerance, and may provide load sharing, depending on the
bonding protocols used. When isolated networks are configured, the OpenStack
services will be configured to use the isolated networks. If no isolated
networks are configured, all services run on the provisioning network.

There are two parts to the network configuration: the parameters that apply
to the network as a whole, and the templates which configure the network
interfaces on the deployed hosts.

Architecture
------------

The following VLANs will be used in the final deployment:

* IPMI* (IPMI System controller, iLO, DRAC)
* Provisioning* (Undercloud control plane for deployment and management)
* Internal API (OpenStack internal API, RPC, and DB)
* Tenant (Tenant tunneling network for GRE/VXLAN networks)
* Storage (Access to storage resources from Compute and Controller nodes)
* Storage Management (Replication, Ceph back-end services)
* External (Public OpenStack APIs, Horzizon dashboard, optionally floating IPs)

.. note::
  Networks marked with '*' are usually native VLANs, others may be trunked.

Additionally, if floating IPs will be hosted on a separate VLAN, that VLAN will
need to be trunked to the controller hosts. It will not be included in the
network configuration steps in this document, the VLAN will be added as a
post-configuration step.

The External network should have a gateway router address. This will be used
in the subnet configuration of the network environment.

The Provisioning network will usually be delivered on a dedicated interface.
By default, PXE boot must occur on the native VLAN, although some system
controllers will allow booting from a VLAN. The Provisioning interface is
also used by the Compute and Storage nodes as their default gateway, in order
to contact DNS, NTP, and for system maintenance. The Undercloud can be used
as a default gateway, but in that case all traffic will be behind an IP
masquerade NAT, and will not be reachable from the rest of the network. The
Undercloud is also a single point of failure for the overcloud default route.
If there is an external gateway on a router device on the Provisioning network,
the Undercloud Neutron DHCP server can offer that instead::

  neutron subnet-show     # Copy the UUID from the provisioning subnet
  neutron subnet-update <UUID> --gateway_ip <IP_ADDRESS>

Often, the number of VLANs will exceed the number of physical Ethernet ports,
so some VLANs are delivered with VLAN tagging to separate the traffic. On an
Ethernet bond, typically all VLANs are trunked, and there is no traffic on the
native VLAN (native VLANs on bonds are supported, but will require customizing
the NIC templates).

The networks are connected to the roles as follows:

Controller:

* All networks

Compute:

* Provisioning
* Internal API
* Storage
* Tenant

Ceph Storage:

* Provisioning
* Storage
* Storage Management

Cinder Storage:

* Provisioning
* Internal API
* Storage
* Storage Management

Swift Storage:

* Provisioning
* Internal API
* Storage
* Storage Management

Workflow
--------

The procedure for enabling network isolation is this:

1. Create network environment file (e.g. /home/stack/network-environment.yaml)
2. Edit IP subnets and VLANs in the environment file to match local environment
3. Make a copy of the appropriate sample network interface configurations
4. Edit the network interface configurations to match local environment
5. Deploy overcloud with the proper parameters to include network isolation

The next section will walk through the elements that need to be added to
the network-environment.yaml to enable network isolation. The sections
after that deal with configuring the network interface templates. The final step
will deploy the overcloud with network isolation and a custom environment.

Create Network Environment File
-------------------------------
The environment file will describe the network environment and will point to
the network interface configuration files to use for the overcloud nodes.
The subnets that will be used for the isolated networks need to be defined,
along with the IP address ranges that should be used for IP assignment. These
values must be customized for the local environment.

It is important for the ExternalInterfaceDefaultRoute to be reachable on the
subnet that is used for ExternalNetCidr. This will allow the OpenStack Public
APIs and the Horizon Dashboard to be reachable. Without a valid default route,
the post-deployment steps cannot be performed.

.. note::
  The ``resource_registry`` section of the network-environment.yaml contains
  pointers to the network interface configurations for the deployed roles.
  These files must exist at the path referenced here, and will be copied
  later in this guide.

Example::

  resource_registry:
    OS::TripleO::BlockStorage::Net::SoftwareConfig: /home/stack/nic-configs/cinder-storage.yaml
    OS::TripleO::Compute::Net::SoftwareConfig: /home/stack/nic-configs/compute.yaml
    OS::TripleO::Controller::Net::SoftwareConfig: /home/stack/nic-configs/controller.yaml
    OS::TripleO::ObjectStorage::Net::SoftwareConfig: /home/stack/nic-configs/swift-storage.yaml
    OS::TripleO::CephStorage::Net::SoftwareConfig: /home/stack/nic-configs/ceph-storage.yaml

  parameter_defaults:
    # Customize all these values to match the local environment
    InternalApiNetCidr: 172.17.0.0/24
    StorageNetCidr: 172.18.0.0/24
    StorageMgmtNetCidr: 172.19.0.0/24
    TenantNetCidr: 172.16.0.0/24
    ExternalNetCidr: 10.1.2.0/24
    InternalApiAllocationPools: [{'start': '172.17.0.10', 'end': '172.17.0.200'}]
    StorageAllocationPools: [{'start': '172.18.0.10', 'end': '172.18.0.200'}]
    StorageMgmtAllocationPools: [{'start': '172.19.0.10', 'end': '172.19.0.200'}]
    TenantAllocationPools: [{'start': '172.16.0.10', 'end': '172.16.0.200'}]
    # Use an External allocation pool which will leave room for floating IPs
    ExternalAllocationPools: [{'start': '10.1.2.10', 'end': '10.1.2.50'}]
    InternalApiNetworkVlanID: 201
    StorageNetworkVlanID: 202
    StorageMgmtNetworkVlanID: 203
    TenantNetworkVlanID: 204
    ExternalNetworkVlanID: 100
    # Set to the router gateway on the external network
    ExternalInterfaceDefaultRoute: 10.1.2.1
    # Customize bonding options if required (will be ignored if bonds are not used)
    BondInterfaceOvsOptions:
        "bond_mode=balance-tcp lacp=active other-config:lacp-fallback-ab=true"

Creating Custom Interface Templates
-----------------------------------

In order to configure the network interfaces on each node, the network
interface templates may need to be customized.

Start by copying the configurations from one of the example directories. The
first example copies the templates which include network bonding. The second
example copies the templates which use a single network interface with
multiple VLANs (this configuration is mostly intended for testing).

To copy the bonded example interface configurations, run::

    $ cp /usr/share/openstack-tripleo-heat-templates/network/config/bond-with-vlans/* ~/nic-configs

To copy the single NIC with VLANs example interface configurations, run::

    $ cp /usr/share/openstack-tripleo-heat-templates/network/config/single-nic-vlans/* ~/nic-configs

Or, if you have custom NIC templates from another source, copy them to the location
referenced in the ``resource_registry`` section of the environment file.

Customizing the Interface Templates
-----------------------------------
The following example configures a bond on interfaces 3 and 4 of a system
with 4 interfaces. This example is based on the controller template from the
bond-with-vlans sample templates, but the bond has been placed on nic3 and nic4
instead of nic2 and nic3. The other roles will have a similar configuration,
but will have only a subset of the networks attached.

.. note::
  The nic1, nic2... abstraction considers only network interfaces which are
  connected to an Ethernet switch. If interfaces 1 and 4 are the only
  interfaces which are plugged in, they will be referred to as nic1 and nic2.

Example::

  heat_template_version: 2015-04-30

  description: >
    Software Config to drive os-net-config with 2 bonded nics on a bridge
    with a VLANs attached for the controller role.

  parameters:
    ExternalIpSubnet:
      default: ''
      description: IP address/subnet on the external network
      type: string
    InternalApiIpSubnet:
      default: ''
      description: IP address/subnet on the internal API network
      type: string
    StorageIpSubnet:
      default: ''
      description: IP address/subnet on the storage network
      type: string
    StorageMgmtIpSubnet:
      default: ''
      description: IP address/subnet on the storage mgmt network
      type: string
    TenantIpSubnet:
      default: ''
      description: IP address/subnet on the tenant network
      type: string
    BondInterfaceOvsOptions:
      default: ''
      description: The ovs_options string for the bond interface. Set things like
                   lacp=active and/or bond_mode=balance-slb using this option.
      type: string
    ExternalNetworkVlanID:
      default: 10
      description: Vlan ID for the external network traffic.
      type: number
    InternalApiNetworkVlanID:
      default: 20
      description: Vlan ID for the internal_api network traffic.
      type: number
    StorageNetworkVlanID:
      default: 30
      description: Vlan ID for the storage network traffic.
      type: number
    StorageMgmtNetworkVlanID:
      default: 40
      description: Vlan ID for the storage mgmt network traffic.
      type: number
    TenantNetworkVlanID:
      default: 50
      description: Vlan ID for the tenant network traffic.
      type: number
    ExternalInterfaceDefaultRoute:
      default: '10.0.0.1'
      description: Default route for the external network.
      type: string

  resources:
    OsNetConfigImpl:
      type: OS::Heat::StructuredConfig
      properties:
        group: os-apply-config
        config:
          os_net_config:
            network_config:
              -
                type: ovs_bridge
                name: {get_input: bridge_name}
                members:
                  -
                    type: ovs_bond
                    name: bond1
                    ovs_options: {get_param: BondInterfaceOvsOptions}
                    members:
                      -
                        type: interface
                        name: nic3
                        primary: true
                      -
                        type: interface
                        name: nic4
                  -
                    type: vlan
                    device: bond1
                    vlan_id: {get_param: ExternalNetworkVlanID}
                    addresses:
                      -
                        ip_netmask: {get_param: ExternalIpSubnet}
                    routes:
                      -
                        ip_netmask: 0.0.0.0/0
                        next_hop: {get_param: ExternalInterfaceDefaultRoute}
                  -
                    type: vlan
                    device: bond1
                    vlan_id: {get_param: InternalApiNetworkVlanID}
                    addresses:
                    -
                      ip_netmask: {get_param: InternalApiIpSubnet}
                  -
                    type: vlan
                    device: bond1
                    vlan_id: {get_param: StorageNetworkVlanID}
                    addresses:
                    -
                      ip_netmask: {get_param: StorageIpSubnet}
                  -
                    type: vlan
                    device: bond1
                    vlan_id: {get_param: StorageMgmtNetworkVlanID}
                    addresses:
                    -
                      ip_netmask: {get_param: StorageMgmtIpSubnet}
                  -
                    type: vlan
                    device: bond1
                    vlan_id: {get_param: TenantNetworkVlanID}
                    addresses:
                    -
                      ip_netmask: {get_param: TenantIpSubnet}

  outputs:
    OS::stack_id:
      description: The OsNetConfigImpl resource.
      value: {get_resource: OsNetConfigImpl}

Configuring Interfaces
----------------------
The individual interfaces may need to be modified. As an example, below are
the modifications that would be required to use the second NIC to connect to
an infrastructure network with DHCP addresses, and to use the third and fourth
NICs for the bond:

Example::

          network_config:
            # Add a DHCP infrastructure network to nic2
            -
              type: interface
              name: nic2
              use_dhcp: true
            -
              type: ovs_bridge
              name: br-bond
              members:
                -
                  type: ovs_bond
                  name: bond1
                  ovs_options: {get_param: BondInterfaceOvsOptions}
                  members:
                    # Modify bond NICs to use nic3 and nic4
                    -
                      type: interface
                      name: nic3
                      primary: true
                    -
                      type: interface
                      name: nic4

When using numbered interfaces ("nic1", "nic2", etc.) instead of named
interfaces ("eth0", "eno2", etc.), the network interfaces of hosts within
a role do not have to be exactly the same. For instance, one host may have
interfaces em1 and em2, while another has eno1 and eno2, but both hosts' NICs
can be referred to as nic1 and nic2.

The numbered NIC scheme only takes into account the interfaces that are live
(have a cable attached to the switch). So if you have some hosts with 4
interfaces, and some with 6, you should use nic1-nic4 and only plug in 4
cables on each host.

Configuring Routes and Default Routes
-------------------------------------
There are two ways that a host may have its default routes set. If the interface
is using DHCP, and the DHCP server offers a gateway address, the system will
install a default route for that gateway. Otherwise, a default route may be set
manually on an interface with a static IP.

Although the Linux kernel supports multiple default gateways, it will only use
the one with the lowest metric. If there are multiple DHCP interfaces, this can
result in an unpredictable default gateway. In this case, it is recommended that
defroute=no be set for the interfaces other than the one where we want the
default route. In this case, we want a DHCP interface (NIC 2) to be the default
route (rather than the Provisioning interface), so we disable the default route
on the provisioning interface:

Example::

            # No default route on the Provisioning network
            -
              type: interface
              name: nic1
              use_dhcp: true
              defroute: no
            # Instead use this DHCP infrastructure VLAN as the default route
            -
              type: interface
              name: nic2
              use_dhcp: true

To set a static route on an interface with a static IP, specify a route to the
subnet. For instance, here is a hypothetical route to the 10.1.2.0/24 subnet
via the gateway at 172.17.0.1 on the Internal API network:

Example::

            -
                  type: vlan
                  device: bond1
                  vlan_id: {get_param: InternalApiNetworkVlanID}
                  addresses:
                  -
                    ip_netmask: {get_param: InternalApiIpSubnet}
              routes:
                -
                  ip_netmask: 10.1.2.0/24
                  next_hop: 172.17.0.1

Configuring Jumbo Frames
------------------------
The Maximum Transmission Unit (MTU) setting determines the maximum amount of
data that can be transmitted by a single Ethernet frame. Using a larger value
can result in less overhead, since each frame adds data in the form of a
header. The default value is 1500, and using a value higher than that will
require the switch port to be configured to support jumbo frames. Most switches
support an MTU of at least 9000, but many are configured for 1500 by default.

The MTU of a VLAN cannot exceed the MTU of the physical interface. Make sure to
include the MTU value on the bond and/or interface.

Storage, Storage Management, Internal API, and Tenant networking can all
benefit from jumbo frames. In testing, tenant networking throughput was
over 300% greater when using jumbo frames in conjunction with VXLAN tunnels.

.. note::
  It is recommended that the Provisioning interface, External interface, and
  any floating IP interfaces be left at the default MTU of 1500. Connectivity
  problems are likely to occur otherwise.

Example::

                  -
                    type: ovs_bond
                    name: bond1
                    mtu: 9000
                    ovs_options: {get_param: BondInterfaceOvsOptions}
                    members:
                      -
                        type: interface
                        name: nic3
                        mtu: 9000
                        primary: true
                      -
                        type: interface
                        name: nic4
                        mtu: 9000
                  -
                    # The external interface should stay at default
                    type: vlan
                    device: bond1
                    vlan_id: {get_param: ExternalNetworkVlanID}
                    addresses:
                      -
                        ip_netmask: {get_param: ExternalIpSubnet}
                    routes:
                      -
                        ip_netmask: 0.0.0.0/0
                        next_hop: {get_param: ExternalInterfaceDefaultRoute}
                  -
                    # MTU 9000 for Internal API, Storage, and Storage Management
                    type: vlan
                    device: bond1
                    mtu: 9000
                    vlan_id: {get_param: InternalApiNetworkVlanID}
                    addresses:
                    -
                      ip_netmask: {get_param: InternalApiIpSubnet}

Assinging OpenStack Services to Isolated Networks
-------------------------------------------------

.. note::
  The services will be assigned to the networks according to the
  ``ServiceNetMap`` in ``overcloud-without-mergepy.yaml``. Unless these
  defaults need to be overridden, the ServiceNetMap does not need to be defined
  in the environment file.

Each OpenStack service is assigned to a network in the resource registry. The
service will be bound to the host IP within the named network on each host.
A service can be assigned to an alternate network by overriding the service to
network map in an environment file. The defaults should generally work, but
can be overridden.

Example::

  parameter_defaults:

    ServiceNetMap:
      NeutronTenantNetwork: tenant
      CeilometerApiNetwork: internal_api
      MongoDbNetwork: internal_api
      CinderApiNetwork: internal_api
      CinderIscsiNetwork: storage
      GlanceApiNetwork: storage
      GlanceRegistryNetwork: internal_api
      KeystoneAdminApiNetwork: internal_api
      KeystonePublicApiNetwork: internal_api
      NeutronApiNetwork: internal_api
      HeatApiNetwork: internal_api
      NovaApiNetwork: internal_api
      NovaMetadataNetwork: internal_api
      NovaVncProxyNetwork: internal_api
      SwiftMgmtNetwork: storage_mgmt
      SwiftProxyNetwork: storage
      HorizonNetwork: internal_api
      MemcachedNetwork: internal_api
      RabbitMqNetwork: internal_api
      RedisNetwork: internal_api
      MysqlNetwork: internal_api
      CephClusterNetwork: storage_mgmt
      CephPublicNetwork: storage

.. note::
  If an entry in the ServiceNetMap points to a network which does not exist,
  that service will be placed on the Provisioning network. To avoid that,
  make sure that each entry points to a valid network.

Deploying the Overcloud With Network Isolation
----------------------------------------------

When deploying with network isolation, you should specify the NTP server for the
overcloud nodes. If the clocks are not synchronized, some OpenStack services may
be unable to start, especially when using HA. The NTP server should be reachable
from both the External and Provisioning subnets. The neutron network type should
be specified, along with the tunneling or VLAN parameters.

To deploy with network isolation and include the network environment file, use
the ``-e`` parameters with the ``openstack overcloud deploy`` command. For
instance, to deploy VXLAN mode, the deployment command might be::

    openstack overcloud deploy -e /home/stack/network-environment.yaml \
    -e /usr/share/openstack-tripleo-heat-templates/environments/network-isolation.yaml \
    --plan openstack --ntp-server pool.ntp.org --neutron-network-type vxlan \
    --neutron-tunnel-types vxlan

To deploy with VLAN mode, you should specify the range of VLANs that will be
used for tenant networks::

    openstack overcloud deploy -e /home/stack/network-environment.yaml \
    -e /usr/share/openstack-tripleo-heat-templates/environments/network-isolation.yaml \
    --plan openstack --ntp-server pool.ntp.org --neutron-network-type vlan \
    --neutron-network-vlan-ranges datacentre:30:100 --neutron-disable-tunneling

Note that you must also pass the environment files (again using the ``-e`` or
``--environment-file`` option) whenever you make subsequent changes to the
overcloud, such as :doc:`../post_deployment/scale_roles`,
:doc:`../post_deployment/delete_nodes` or
:doc:`../post_deployment/package_update`.

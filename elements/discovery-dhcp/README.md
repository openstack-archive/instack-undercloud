Adds a discovery-dhcp element

This element adds a systemd service that spawns a dnsmasq process
TODO: add configuration here (e.g. for bind interface).

This dnsmasq process is intended to serve only new and undiscovered
machines. Already enrolled hardware continues to be served by the
neutron-dhcp-agent spawned dnsmasq process(es) (and this/ese is/are
already explicitly told not to answer calls from unknown machines).

The element uses iptables to block dhcp/bootp requests from already
enrolled hardware (by querying ironic), in pretty much exactly the
same way as the older bm-dnsmasq element, with a cronjob setup to
periodically update the chain (to include for example recently
discovered machines). An alternative is to use a dhcp hostfile with
'MAC, ignore' entries (and then sighup dnsmasq).

The way we get a list of MAC addresses depends on if we are in a virt or
baremetal environment:

In the baremetal case, Ironic will create a new node entry without
populating (amongst most other fields) the MAC address for an associated
port. Thus all MAC addresses reported by 'ironic port-list' can be added to
the iptables chain with 'DROP'.

For the VM case we expect Ironic to set a MAC address for newly enrolled
but not yet discovered nodes (for matching returned data). In this case, we
cannot use the MAC addresses given by 'ironic port-list' as these will
include the yet undiscovered node MACs. Thus we must get a list of all
nodes that have 'maintenance' set to False (is the case for
known/discovered machines) and then blacklist only their MACs, which
requires a potentially large number of API calls (1/node).


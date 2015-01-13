Sets up a dnsmasq process for forwarding dns requests. Also opens port 53 and
adds a rule to forward all traffic.

When applied to the undercloud, this will allow launched instances to install
packages from internal hosts.

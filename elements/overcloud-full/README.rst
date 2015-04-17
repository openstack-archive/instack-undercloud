overcloud-full
==============

Element for the overcloud-full image created by instack-undercloud.

Workarounds
-----------

This element can be used to apply needed workarounds.

* openstack-glance-api and openstack-glance-registry are currently installed
  explicitly since this is not handled by the overcloud-control element from
  tripleo-puppet-elements

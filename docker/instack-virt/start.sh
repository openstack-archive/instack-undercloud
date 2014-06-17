#!/bin/bash

/usr/share/openvswitch/scripts/ovs-ctl start --system-id=random
supervisord -n

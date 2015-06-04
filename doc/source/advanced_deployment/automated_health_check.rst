Automated Health Check (AHC)
============================

Start with matching the nodes to profiles as described in
:doc:`profile_matching`.

Enable running benchmarks during discovery
------------------------------------------

By default, the benchmark tests do not run during the discovery process.
You can enable this feature by setting *discovery_runbench = true* in the
**undercloud.conf** file prior to installing the undercloud.

If you want to enable this feature after installing the undercloud, you can set
*discovery_runbench = true* in **undercloud.conf**, and re-run
``openstack undercloud install``

Analyze the collected benchmark data
------------------------------------

After discovery has completed, we can do analysis on the benchmark data.

* Run the ``ahc-report`` script to see a general overview of the hardware

  ::

    $ source stackrc
    $ ahc-report --categories
    ##### HPA Controller #####
    3 identical systems :
    [u'7F8831F1-0D81-464E-A767-7577DF49AAA5', u'B9FE637A-5B97-4A52-BFDA-9244CEA65E23', u'7884BC95-6EF8-4447-BDE5-D19561718B29']
    []

    ########################
    ##### Megaraid Controller #####
    3 identical systems :
    [u'7F8831F1-0D81-464E-A767-7577DF49AAA5', u'B9FE637A-5B97-4A52-BFDA-9244CEA65E23', u'7884BC95-6EF8-4447-BDE5-D19561718B29']
    []

    #############################
    ##### AHCI Controller #####
    3 identical systems :
    [u'7F8831F1-0D81-464E-A767-7577DF49AAA5', u'B9FE637A-5B97-4A52-BFDA-9244CEA65E23', u'7884BC95-6EF8-4447-BDE5-D19561718B29']
    []

    #########################
    ##### IPMI SDR #####
    3 identical systems :
    [u'7F8831F1-0D81-464E-A767-7577DF49AAA5', u'B9FE637A-5B97-4A52-BFDA-9244CEA65E23', u'7884BC95-6EF8-4447-BDE5-D19561718B29']
    []

    ##################
    ##### Firmware #####
    3 identical systems :
    [u'7F8831F1-0D81-464E-A767-7577DF49AAA5', u'B9FE637A-5B97-4A52-BFDA-9244CEA65E23', u'7884BC95-6EF8-4447-BDE5-D19561718B29']
    [(u'firmware', u'bios', u'date', u'01/01/2011'),
     (u'firmware', u'bios', u'vendor', u'Seabios'),
     (u'firmware', u'bios', u'version', u'0.5.1')]

    ##################
    ##### Memory Timing(RAM) #####
    3 identical systems :
    [u'7F8831F1-0D81-464E-A767-7577DF49AAA5', u'B9FE637A-5B97-4A52-BFDA-9244CEA65E23', u'7884BC95-6EF8-4447-BDE5-D19561718B29']
    []

    ############################
    ##### Network Interfaces #####
    3 identical systems :
    [u'7F8831F1-0D81-464E-A767-7577DF49AAA5', u'B9FE637A-5B97-4A52-BFDA-9244CEA65E23', u'7884BC95-6EF8-4447-BDE5-D19561718B29']
    [(u'network', u'eth0', u'businfo', u'pci@0000:00:04.0'),
     (u'network', u'eth0', u'busy-poll', u'off [fixed]'),
     (u'network', u'eth0', u'driver', u'virtio_net'),
     (u'network', u'eth0', u'fcoe-mtu', u'off [fixed]'),
     (u'network', u'eth0', u'generic-receive-offload', u'on'),
     (u'network', u'eth0', u'generic-segmentation-offload', u'on'),
     (u'network', u'eth0', u'highdma', u'on [fixed]'),
     (u'network', u'eth0', u'large-receive-offload', u'off [fixed]'),
     (u'network', u'eth0', u'latency', u'0'),
     (u'network', u'eth0', u'link', u'yes'),
     (u'network', u'eth0', u'loopback', u'off [fixed]'),
     (u'network', u'eth0', u'netns-local', u'off [fixed]'),
     (u'network', u'eth0', u'ntuple-filters', u'off [fixed]'),
     (u'network', u'eth0', u'receive-hashing', u'off [fixed]'),
     (u'network', u'eth0', u'rx-all', u'off [fixed]'),
     (u'network', u'eth0', u'rx-checksumming', u'on [fixed]'),
     (u'network', u'eth0', u'rx-fcs', u'off [fixed]'),
     (u'network', u'eth0', u'rx-vlan-filter', u'on [fixed]'),
     (u'network', u'eth0', u'rx-vlan-offload', u'off [fixed]'),
     (u'network', u'eth0', u'rx-vlan-stag-filter', u'off [fixed]'),
     (u'network', u'eth0', u'rx-vlan-stag-hw-parse', u'off [fixed]'),
     (u'network', u'eth0', u'scatter-gather', u'on'),
     (u'network', u'eth0', u'scatter-gather/tx-scatter-gather', u'on'),
     (u'network', u'eth0', u'scatter-gather/tx-scatter-gather-fraglist', u'on'),
     (u'network', u'eth0', u'tcp-segmentation-offload', u'on'),
     (u'network',
      u'eth0',
      u'tcp-segmentation-offload/tx-tcp-ecn-segmentation',
      u'on'),
     (u'network', u'eth0', u'tcp-segmentation-offload/tx-tcp-segmentation', u'on'),
     (u'network',
      u'eth0',
      u'tcp-segmentation-offload/tx-tcp6-segmentation',
      u'on'),
     (u'network', u'eth0', u'tx-checksumming', u'on'),
     (u'network',
      u'eth0',
      u'tx-checksumming/tx-checksum-fcoe-crc',
      u'off [fixed]'),
     (u'network', u'eth0', u'tx-checksumming/tx-checksum-ip-generic', u'on'),
     (u'network', u'eth0', u'tx-checksumming/tx-checksum-ipv6', u'off [fixed]'),
     (u'network', u'eth0', u'tx-checksumming/tx-checksum-sctp', u'off [fixed]'),
     (u'network', u'eth0', u'tx-fcoe-segmentation', u'off [fixed]'),
     (u'network', u'eth0', u'tx-gre-segmentation', u'off [fixed]'),
     (u'network', u'eth0', u'tx-gso-robust', u'off [fixed]'),
     (u'network', u'eth0', u'tx-ipip-segmentation', u'off [fixed]'),
     (u'network', u'eth0', u'tx-lockless', u'off [fixed]'),
     (u'network', u'eth0', u'tx-mpls-segmentation', u'off [fixed]'),
     (u'network', u'eth0', u'tx-nocache-copy', u'on'),
     (u'network', u'eth0', u'tx-sit-segmentation', u'off [fixed]'),
     (u'network', u'eth0', u'tx-udp_tnl-segmentation', u'off [fixed]'),
     (u'network', u'eth0', u'tx-vlan-offload', u'off [fixed]'),
     (u'network', u'eth0', u'tx-vlan-stag-hw-insert', u'off [fixed]'),
     (u'network', u'eth0', u'udp-fragmentation-offload', u'on'),
     (u'network', u'eth0', u'vlan-challenged', u'off [fixed]')]

    ############################
    ##### Processors #####
    1 identical systems :
    [u'B9FE637A-5B97-4A52-BFDA-9244CEA65E23']
    [(u'cpu', u'logical', u'number', u'2'),
     (u'cpu', u'physical', u'number', u'2'),
     (u'cpu',
      u'physical_0',
      u'flags',
      u'fpu fpu_exception wp de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pse36 clflush mmx fxsr sse sse2 syscall nx x86-64 rep_good nopl pni cx16 hypervisor lahf_lm'),
     (u'cpu', u'physical_0', u'frequency', u'2000000000'),
     (u'cpu', u'physical_0', u'physid', u'401'),
     (u'cpu', u'physical_0', u'product', u'QEMU Virtual CPU version 1.5.3'),
     (u'cpu', u'physical_0', u'vendor', u'Intel Corp.'),
     (u'cpu',
      u'physical_1',
      u'flags',
      u'fpu fpu_exception wp de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pse36 clflush mmx fxsr sse sse2 syscall nx x86-64 rep_good nopl pni cx16 hypervisor lahf_lm'),
     (u'cpu', u'physical_1', u'frequency', u'2000000000'),
     (u'cpu', u'physical_1', u'physid', u'402'),
     (u'cpu', u'physical_1', u'product', u'QEMU Virtual CPU version 1.5.3'),
     (u'cpu', u'physical_1', u'vendor', u'Intel Corp.')]

    2 identical systems :
    [u'7F8831F1-0D81-464E-A767-7577DF49AAA5', u'7884BC95-6EF8-4447-BDE5-D19561718B29']
    [(u'cpu', u'logical', u'number', u'1'),
     (u'cpu', u'physical', u'number', u'1'),
     (u'cpu',
      u'physical_0',
      u'flags',
      u'fpu fpu_exception wp de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pse36 clflush mmx fxsr sse sse2 syscall nx x86-64 rep_good nopl pni cx16 hypervisor lahf_lm'),
     (u'cpu', u'physical_0', u'frequency', u'2000000000'),
     (u'cpu', u'physical_0', u'physid', u'401'),
     (u'cpu', u'physical_0', u'product', u'QEMU Virtual CPU version 1.5.3'),
     (u'cpu', u'physical_0', u'vendor', u'Intel Corp.')]

  In the example above we have two nodes with a single CPU, and one with two CPU's.

* We can also look for performance outliers

  ::

    $ ahc-report --outliers

    Group 0 : Checking logical disks perf
    standalone_randread_4k_KBps       : INFO    : sda          : Group performance : min=45296.00, mean=53604.67, max=67923.00, stddev=12453.21
    standalone_randread_4k_KBps       : ERROR   : sda          : Group's variance is too important :   23.23% of 53604.67 whereas limit is set to 15.00%
    standalone_randread_4k_KBps       : ERROR   : sda          : Group performance : UNSTABLE
    standalone_read_1M_IOps           : INFO    : sda          : Group performance : min= 1199.00, mean= 1259.00, max= 1357.00, stddev=   85.58
    standalone_read_1M_IOps           : INFO    : sda          : Group performance = 1259.00   : CONSISTENT
    standalone_randread_4k_IOps       : INFO    : sda          : Group performance : min=11320.00, mean=13397.33, max=16977.00, stddev= 3113.39
    standalone_randread_4k_IOps       : ERROR   : sda          : Group's variance is too important :   23.24% of 13397.33 whereas limit is set to 15.00%
    standalone_randread_4k_IOps       : ERROR   : sda          : Group performance : UNSTABLE
    standalone_read_1M_KBps           : INFO    : sda          : Group performance : min=1231155.00, mean=1292799.67, max=1393152.00, stddev=87661.11
    standalone_read_1M_KBps           : INFO    : sda          : Group performance = 1292799.67   : CONSISTENT

    Group 0 : Checking CPU perf
    bogomips                          : INFO    : logical_0    : Group performance : min= 4199.99, mean= 4199.99, max= 4199.99, stddev=    0.00
    bogomips                          : INFO    : logical_0    : Group performance = 4199.99   : CONSISTENT
    bogomips                          : INFO    : logical_1    : Group performance : min= 4199.99, mean= 4199.99, max= 4199.99, stddev=     nan
    bogomips                          : INFO    : logical_1    : Group performance = 4199.99   : CONSISTENT
    loops_per_sec                     : INFO    : logical_0    : Group performance : min=  379.00, mean=  398.67, max=  418.00, stddev=   19.50
    loops_per_sec                     : INFO    : logical_0    : Group performance =  398.67   : CONSISTENT
    loops_per_sec                     : INFO    : logical_1    : Group performance : min=  423.00, mean=  423.00, max=  423.00, stddev=     nan
    loops_per_sec                     : INFO    : logical_1    : Group performance =  423.00   : CONSISTENT
    loops_per_sec                     : INFO    : CPU Effi.    : Group performance : min=   99.28, mean=     inf, max=     inf, stddev=     nan
    loops_per_sec                     : INFO    : CPU Effi.    : Group performance =     inf % : CONSISTENT

    Group 0 : Checking Memory perf
    Memory benchmark 1K               : INFO    : logical_0    : Group performance : min= 1677.00, mean= 1698.33, max= 1739.00, stddev=   35.23
    Memory benchmark 1K               : INFO    : logical_0    : Group performance = 1698.33   : CONSISTENT
    Memory benchmark 1K               : INFO    : logical_1    : Group performance : min= 1666.00, mean= 1666.00, max= 1666.00, stddev=     nan
    Memory benchmark 1K               : INFO    : logical_1    : Group performance = 1666.00   : CONSISTENT
    Memory benchmark 1K               : INFO    : Thread effi. : Group performance : min=   71.54, mean=   71.54, max=   71.54, stddev=     nan
    Memory benchmark 1K               : INFO    : Thread effi. : Group performance =   71.54   : CONSISTENT
    Memory benchmark 1K               : INFO    : Forked Effi. : Group performance : min=  101.97, mean=  101.97, max=  101.97, stddev=     nan
    Memory benchmark 1K               : INFO    : Forked Effi. : Group performance =  101.97 % : CONSISTENT
    Memory benchmark 4K               : INFO    : logical_0    : Group performance : min= 4262.00, mean= 4318.00, max= 4384.00, stddev=   61.61
    Memory benchmark 4K               : INFO    : logical_0    : Group performance = 4318.00   : CONSISTENT
    Memory benchmark 4K               : INFO    : logical_1    : Group performance : min= 4363.00, mean= 4363.00, max= 4363.00, stddev=     nan
    Memory benchmark 4K               : INFO    : logical_1    : Group performance = 4363.00   : CONSISTENT
    Memory benchmark 4K               : INFO    : Thread effi. : Group performance : min=   77.75, mean=   77.75, max=   77.75, stddev=     nan
    Memory benchmark 4K               : INFO    : Thread effi. : Group performance =   77.75   : CONSISTENT
    Memory benchmark 4K               : INFO    : Forked Effi. : Group performance : min=   95.98, mean=   95.98, max=   95.98, stddev=     nan
    Memory benchmark 4K               : INFO    : Forked Effi. : Group performance =   95.98 % : CONSISTENT
    Memory benchmark 1M               : INFO    : logical_0    : Group performance : min= 7734.00, mean= 7779.00, max= 7833.00, stddev=   50.11
    Memory benchmark 1M               : INFO    : logical_0    : Group performance = 7779.00   : CONSISTENT
    Memory benchmark 1M               : INFO    : logical_1    : Group performance : min= 7811.00, mean= 7811.00, max= 7811.00, stddev=     nan
    Memory benchmark 1M               : INFO    : logical_1    : Group performance = 7811.00   : CONSISTENT
    Memory benchmark 1M               : INFO    : Thread effi. : Group performance : min=  101.20, mean=  101.20, max=  101.20, stddev=     nan
    Memory benchmark 1M               : INFO    : Thread effi. : Group performance =  101.20   : CONSISTENT
    Memory benchmark 1M               : INFO    : Forked Effi. : Group performance : min=   99.26, mean=   99.26, max=   99.26, stddev=     nan
    Memory benchmark 1M               : INFO    : Forked Effi. : Group performance =   99.26 % : CONSISTENT
    Memory benchmark 16M              : INFO    : logical_0    : Group performance : min= 5986.00, mean= 6702.33, max= 7569.00, stddev=  802.14
    Memory benchmark 16M              : ERROR   : logical_0    : Group's variance is too important :   11.97% of 6702.33 whereas limit is set to 7.00%
    Memory benchmark 16M              : ERROR   : logical_0    : Group performance : UNSTABLE
    Memory benchmark 16M              : INFO    : logical_1    : Group performance : min= 7030.00, mean= 7030.00, max= 7030.00, stddev=     nan
    Memory benchmark 16M              : INFO    : logical_1    : Group performance = 7030.00   : CONSISTENT
    Memory benchmark 16M              : INFO    : Thread effi. : Group performance : min=  109.94, mean=  109.94, max=  109.94, stddev=     nan
    Memory benchmark 16M              : INFO    : Thread effi. : Group performance =  109.94   : CONSISTENT
    Memory benchmark 16M              : INFO    : Forked Effi. : Group performance : min=   93.14, mean=   93.14, max=   93.14, stddev=     nan
    Memory benchmark 16M              : INFO    : Forked Effi. : Group performance =   93.14 % : CONSISTENT
    Memory benchmark 128M             : INFO    : logical_0    : Group performance : min= 6021.00, mean= 6387.00, max= 7084.00, stddev=  603.87
    Memory benchmark 128M             : ERROR   : logical_0    : Group's variance is too important :    9.45% of 6387.00 whereas limit is set to 7.00%
    Memory benchmark 128M             : ERROR   : logical_0    : Group performance : UNSTABLE
    Memory benchmark 128M             : INFO    : logical_1    : Group performance : min= 7089.00, mean= 7089.00, max= 7089.00, stddev=     nan
    Memory benchmark 128M             : INFO    : logical_1    : Group performance = 7089.00   : CONSISTENT
    Memory benchmark 128M             : INFO    : Thread effi. : Group performance : min=  107.11, mean=  107.11, max=  107.11, stddev=     nan
    Memory benchmark 128M             : INFO    : Thread effi. : Group performance =  107.11   : CONSISTENT
    Memory benchmark 128M             : INFO    : Forked Effi. : Group performance : min=   95.55, mean=   95.55, max=   95.55, stddev=     nan
    Memory benchmark 128M             : INFO    : Forked Effi. : Group performance =   95.55 % : CONSISTENT
    Memory benchmark 256M             : WARNING : Thread effi. : Benchmark not run on this group
    Memory benchmark 256M             : WARNING : Forked Effi. : Benchmark not run on this group
    Memory benchmark 1G               : INFO    : logical_0    : Group performance : min= 6115.00, mean= 6519.67, max= 7155.00, stddev=  557.05
    Memory benchmark 1G               : ERROR   : logical_0    : Group's variance is too important :    8.54% of 6519.67 whereas limit is set to 7.00%
    Memory benchmark 1G               : ERROR   : logical_0    : Group performance : UNSTABLE
    Memory benchmark 1G               : INFO    : logical_1    : Group performance : min= 7136.00, mean= 7136.00, max= 7136.00, stddev=     nan
    Memory benchmark 1G               : INFO    : logical_1    : Group performance = 7136.00   : CONSISTENT
    Memory benchmark 1G               : INFO    : Thread effi. : Group performance : min=  104.29, mean=  104.29, max=  104.29, stddev=     nan
    Memory benchmark 1G               : INFO    : Thread effi. : Group performance =  104.29   : CONSISTENT
    Memory benchmark 1G               : INFO    : Forked Effi. : Group performance : min=   98.98, mean=   98.98, max=   98.98, stddev=     nan
    Memory benchmark 1G               : INFO    : Forked Effi. : Group performance =   98.98 % : CONSISTENT
    Memory benchmark 2G               : INFO    : logical_0    : Group performance : min= 6402.00, mean= 6724.33, max= 7021.00, stddev=  310.30
    Memory benchmark 2G               : INFO    : logical_0    : Group performance = 6724.33   : CONSISTENT
    Memory benchmark 2G               : INFO    : logical_1    : Group performance : min= 7167.00, mean= 7167.00, max= 7167.00, stddev=     nan
    Memory benchmark 2G               : INFO    : logical_1    : Group performance = 7167.00   : CONSISTENT
    Memory benchmark 2G               : WARNING : Thread effi. : Benchmark not run on this group
    Memory benchmark 2G               : WARNING : Forked Effi. : Benchmark not run on this group

  The output above is from a virtual setup, so the benchmarks are not accurate.
  However we can see that the variance of the "standalone_randread_4k_KBps"
  metric was above the threshold, so the group is marked as unstable.

Exclude outliers from deployment
--------------------------------

We will use the sample reports above to construct some matching rules
for our deployment. Refer to :doc:`profile_matching` for details.

* Add a rule to the **control.specs** file to match the system with two CPUs

  ::

      [
       ('cpu', 'logical', 'number', 'ge(2)'),
       ('disk', '$disk', 'size', 'gt(4)'),
       ('network', '$eth', 'ipv4', 'network(192.0.2.0/24)'),
       ('memory', 'total', 'size', 'ge(4294967296)'),
      ]

* Add a rule to the **control.specs** file to exclude systems with below
  average disk performance from the control role

  ::

      [
       ('disk', '$disk', 'standalone_randread_4k_IOps', 'gt(13397)')
       ('cpu', 'logical', 'number', 'ge(2)'),
       ('disk', '$disk', 'size', 'gt(4)'),
       ('network', '$eth', 'ipv4', 'network(192.0.2.0/24)'),
       ('memory', 'total', 'size', 'ge(4294967296)'),
      ]

* Now rerun the matching and proceed with remaining steps from
  :doc:`profile_matching`.

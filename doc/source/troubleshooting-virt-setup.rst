Troubleshooting instack-virt-setup Failures
===========================================

* Due to a `bug in libvirt`_, it is possible for instack-virt-setup to fail
  with an error such as the following::

      libvirt: QEMU Driver error : unsupported configuration: This QEMU doesn't support virtio scsi controller
      Traceback (most recent call last):
      File "/usr/libexec/openstack-tripleo/configure-vm", line 133, in <module>
          main()
      File "/usr/libexec/openstack-tripleo/configure-vm", line 129, in main
          a = conn.defineXML(libvirt_template)
      File "/usr/lib64/python2.7/site-packages/libvirt.py", line 3445, in defineXML
          if ret is None:raise libvirtError('virDomainDefineXML() failed', conn=self)
      libvirt.libvirtError: unsupported configuration: This QEMU doesn't support virtio scsi controller

  The workaround is to do delete the libvirt capabilities cache and restart the service::

      rm -Rf  /var/cache/libvirt/qemu/capabilities/
      systemctl restart libvirtd

.. _bug in libvirt: https://bugzilla.redhat.com/show_bug.cgi?id=1195882

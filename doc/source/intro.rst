Introduction
============

instack-undercloud is a scripted installer and other tooling for OpenStack
based on `TripleO`_.

.. _Tripleo: https://wiki.openstack.org/wiki/TripleO

Documentation Conventions
-------------------------

Some steps in the following instructions only apply to certain environments,
such as deployments to real baremetal and deployments using RHEL.  These
steps are marked as follows:

.. admonition:: RHEL
   :class: rhel-tag

   Step that should only be run when using RHEL

.. admonition:: CentOS
   :class: centos-tag

   Step that should only be run when using CentOS


.. admonition:: Baremetal
   :class: baremetal-tag

   Step that should only be run when deploying to baremetal

.. admonition:: Virt
   :class: virt-tag

   Step that should only be run when deploying to virtual machines

.. admonition:: Ceph
   :class: ceph-tag

   Step that should only be run when deploying Ceph for use by the Overcloud

Any such steps should *not* be run if the target environment does not match
the section marking.

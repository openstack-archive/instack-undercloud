Welcome to RDO-Manager documentation
====================================

On these sites we are going to explain what `RDO-Manager <introduction/
introduction.html>`_ is and guide you how to use it to successfuly deploy and
manage `RDO <http://rdoproject.org>`_ (OpenStack packaged for Fedora, Centos and
RHEL distributions).

Contents:

.. toctree::
   :maxdepth: 2

   Introduction <introduction/introduction>
   Setup <setup>
   Installing the Undercloud <install-undercloud>
   Building Images <build-images>
   Deploying the Overcloud <deploy-overcloud>
   Vendor-Specific Setup <vendor-specific>
   How to Contribute <contributions/contributions>


Appendices
==========

.. toctree::

   Frequently Asked Questions (FAQ) <faq>
   AHC (Automated Health Check) Workflow <ahc-workflow>
   Troubleshooting instack-virt-setup Failures <troubleshooting-virt-setup>
   Troubleshooting a Failed Overcloud Deployment <troubleshooting-overcloud>


Documentation Conventions
=========================

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

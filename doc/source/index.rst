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
   Environments <environments/environments>
   Installing the Undercloud <install-undercloud>
   Building Images <build-images>
   Deploying the Overcloud <deploy-overcloud>
   Vendor-Specific Setup <vendor-specific>
   AHC (Automated Health Check) Workflow <ahc-workflow>
   Troubleshooting <troubleshooting/troubleshooting>
   How to Contribute <contributions/contributions>


Documentation Conventions
=========================

Some steps in the following instructions only apply to certain environments,
such as deployments to real baremetal and deployments using RHEL. These
steps are marked as follows:

.. admonition:: RHEL
   :class: rhel

   Step that should only be run when using RHEL

.. admonition:: CentOS
   :class: centos

   Step that should only be run when using CentOS


.. admonition:: Baremetal
   :class: baremetal

   Step that should only be run when deploying to baremetal

.. admonition:: Virtual
   :class: virtual

   Step that should only be run when deploying to virtual machines

.. admonition:: Ceph
   :class: ceph

   Step that should only be run when deploying Ceph for use by the Overcloud

Any such steps should *not* be run if the target environment does not match
the section marking.

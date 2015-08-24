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
   Environment Setup <environments/environments>
   Undercloud Installation <installation/installation>
   Basic Deployment (CLI) <basic_deployment/basic_deployment_cli>
   Basic Deployment (GUI) <basic_deployment/basic_deployment_gui>
   Advanced Deployment <advanced_deployment/advanced_deployment>
   Post Deployment <post_deployment/post_deployment>
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

.. admonition:: Portal Registration
   :class: portal

   Step that should only be run when using Portal Registration

.. admonition:: Satellite Registration
   :class: satellite

   Step that should only be run when using Satellite Registration

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

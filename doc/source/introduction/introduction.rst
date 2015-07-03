RDO-Manager Introduction
========================

RDO-Manager is an OpenStack Deployment & Management tool for RDO. It is based on
`OpenStack TripleO <https://wiki.openstack.org/wiki/TripleO>`_ project and its
philosophy is inspired by `SpinalStack <http://spinal-stack.readthedocs.org/en/
latest/>`_.


Useful links:

* `RDO-Manager Home Page <http://rdoproject.org/RDO-Manager>`_

* `RDO-Manager Repositories <http://github.com/rdo-management>`_

* `TripleO Documentation <http://docs.openstack.org/developer/tripleo-incubator/README.html>`_

|

**Architecture**

With RDO-Manager, you start by creating an **undercloud** (an actual operator
facing deployment cloud) that will contain the necessary OpenStack components to
deploy and manage an **overcloud** (an actual tenant facing workload cloud). The
overcloud is the deployed solution and can represent a cloud for any purpose
(e.g. production, staging, test, etc). The operator can choose any of available
Overcloud Roles (OpenStack components) they want to deploy to his environment.

Go to :doc:`architecture` to learn more.

|

**Components**

RDO-Manager is composed of set of official OpenStack components accompanied by
few other open sourced plugins which are increasing RDO-Manager capabilities.

Go to :doc:`components` to learn more.


.. toctree::
   :hidden:

   Architecture <architecture>
   Components <components>

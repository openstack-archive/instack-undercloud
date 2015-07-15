Additional node configuration
=============================

It is possible to enable additional configuration during one of the
following deployment phases:

* firstboot - run once config (performed by cloud-init)
* post-deploy - run after the services have been deployed and configured

.. note::

    This documentation assumes some knowledge of heat HOT_ template
    syntax, and makes use of heat environment_ files.  See the upstream
    heat documentation_ for further information.

.. _HOT: http://docs.openstack.org/developer/heat/template_guide/hot_guide.html
.. _environment: http://docs.openstack.org/developer/heat/template_guide/environment.html
.. _documentation: http://docs.openstack.org/developer/heat/template_guide/index.html

Firstboot extra configuration
-----------------------------

Firstboot configuration is optional, and is performed on *all* nodes on initial
deployment.

Any configuration possible via cloud-init may be performed at this point,
either by applying cloud-config yaml or running arbitrary additional
scripts.

The heat templates used for deployment provide the `OS::TripleO::NodeUserData`
resource as the interface to enable this configuration. A basic example of its
usage is provided below, followed by some notes related to real world
usage.

The script snippet below shows how to create a simple example containing two
scripts, combined via the MultipartMime_ resource::

    mkdir firstboot
    cat > firstboot/one_two.yaml << EOF
    heat_template_version: 2014-10-16

    resources:
      userdata:
        type: OS::Heat::MultipartMime
        properties:
          parts:
          - config: {get_resource: one_config}
          - config: {get_resource: two_config}

      one_config:
        type: OS::Heat::SoftwareConfig
        properties:
          config: |
            #!/bin/bash
            echo "one" > /tmp/one

      two_config:
        type: OS::Heat::SoftwareConfig
        properties:
          config: |
            #!/bin/bash
            echo "two" > /tmp/two

    outputs:
      OS::stack_id:
        value: {get_resource: userdata}
    EOF

.. _MultipartMime: http://docs.openstack.org/developer/heat/template_guide/openstack.html#OS::Heat::MultipartMime

.. note::

    The stack must expose an `OS::stack_id` output which references an
    OS::Heat::MultipartMime resource.

This template is then mapped to the `OS::TripleO::NodeUserData` resource type
via a heat environment file::

    cat > userdata_env.yaml << EOF
    resource_registry:
        OS::TripleO::NodeUserData: firstboot/one_two.yaml
    EOF

You may then deploy your overcloud referencing the additional environment file::

    openstack overcloud deploy --templates -e userdata_env.yaml

.. note::

    The userdata is applied to *all* nodes in the deployment.  If you need role
    specific logic, the userdata scripts can contain conditionals which use
    e.g the node hostname to determine the role.

.. note::

    OS::TripleO::NodeUserData is only applied on initial node deployment,
    not on any subsequent stack update, because cloud-init only processes the
    nova user-data once, on first boot.

For a more complete example, which creates an additional user and configures
SSH keys by accessing the nova metadata server, see
/usr/share/openstack-tripleo-heat-templates/firstboot/userdata_example.yaml
on the undercloud node or the tripleo-heat-templates_ repo.

.. _tripleo-heat-templates: https://github.com/rdo-management/tripleo-heat-templates/blob/mgt-master/firstboot/userdata_example.yaml

Post-Deploy extra configuration
-------------------------------

Post-deploy additional configuration is possible via the
`OS::TripleO::NodeExtraConfigPost` interface - this allows a heat template
to be specified which performs additional configuration using standard
heat SoftwareConfig_ resources.

.. _SoftwareConfig: http://docs.openstack.org/developer/heat/template_guide/software_deployment.html

.. note::

  The `OS::TripleO::NodeExtraConfigPost` applies configuration to *all* nodes,
  there is currently no per-role NodeExtraConfigPost interface.

Below is an example of a post-deployment configuration template::

    mkdir -p extraconfig/post-deploy/
    cat > extraconfig/post-deploy/example.yaml << EOF
    heat_template_version: 2014-10-16

    parameters:
      servers:
        type: json

      # Optional implementation specific parameters
      some_extraparam:
        type: string

    resources:

      ExtraConfig:
        type: OS::Heat::SoftwareConfig
        properties:
          group: script
          config:
            str_replace:
              template: |
                #!/bin/sh
                echo "extra _APARAM_" > /root/extra
              parameters:
                _APARAM_: {get_param: some_extraparam}

      ExtraDeployments:
        type: OS::Heat::SoftwareDeployments
        properties:
          servers:  {get_param: servers}
          config: {get_resource: ExtraConfig}
          actions: ['CREATE'] # Only do this on CREATE
    EOF

The "servers" parameter must be specified in all NodeExtraConfigPost
templates, this is the server list to apply the configuration to,
and is provided by the parent template.

Optionally, you may define additional parameters which are consumed by the
implementation.  These may then be provided via parameter_defaults in the
environment which enables the configuration.

.. note::

    If the parameter_defaults approach is used, care must be used to avoid
    unintended reuse of parameter names between multiple templates, because
    parameter_defaults is applied globally.

The "actions" property of the `OS::Heat::SoftwareDeployments` resource may be
used to specify when the configuration should be applied, e.g only on CREATE,
only on DELETE etc.  If this is ommitted, the heat default is to apply the
config on CREATE and UPDATE, e.g on initial deployment and every subsequent
update.

The extra config may be enabled via an environment file::

    cat > post_config_env.yaml << EOF
    resource_registry:
        OS::TripleO::NodeExtraConfigPost: extraconfig/post-deploy/example.yaml
    parameter_defaults:
        some_extraparam: avalue123
    EOF

You may then deploy your overcloud referencing the additional environment file::

    openstack overcloud deploy --templates -e post_config_env.yaml

Deploying with Heat Templates
=============================

It is possible to deploy to heat directly, using a directory of templates,
e.g without using any Tuskar plan.  This is potentially a more convenient
approach if you are only deploying via the CLI (the UI requires Tuskar),
and/or if you are developing significant enhancements or site-specific
additions to the templates.


Deploying an Overcloud without Tuskar
-------------------------------------

You may use the ``--templates`` option to enable deploying only using heat
templates, e.g no tuskar plan::

    openstack overcloud deploy --templates

.. note::

    The default location for the templates is
    `/usr/share/openstack-tripleo-heat-templates`.  Using this option
    will not include any modifications to the Tuskar role templates which
    may have been performed, templates are always read from local files.


Overriding specific templates with local versions
-------------------------------------------------

You may use heat environment files (via the ``--environment-file`` or ``-e``
option), combined with the ``--templates`` option to override specific
templates, e.g to test a bugfix outside of the location of the packaged
templates.

The mapping between heat resource types and the underlying templates can be
found in
`/usr/share/\
openstack-tripleo-heat-templates/overcloud-resource-registry-puppet.yaml`

Here is an example of copying a specific resource template and overriding
so the deployment uses the local version::

    mkdir local_templates
    cp /usr/share/openstack-tripleo-heat-templates/puppet/controller-puppet.yaml local_templates
    cat > override_templates.yaml << EOF
    resource_registry:
        OS::TripleO::Controller: local_templates/controller-puppet.yaml
    EOF
    openstack overcloud deploy --templates --environment-file override_templates.yaml

.. note::

    The ``--environment-file``/``-e`` option may be specified multiple times,
    if duplicate keys are specified in the environment files, the last one
    takes precedence.

.. note::

    You must also pass the environment files (again using the ``-e`` or
    ``--environment-file`` option) whenever you make subsequent changes to the
    overcloud, such as :doc:`../post_deployment/scale_roles`,
    :doc:`../post_deployment/delete_nodes` or
    :doc:`../post_deployment/package_update`.

.. _custom-template-location:

Using a custom location for all templates
-----------------------------------------

You may specify a path to the ``--templates`` option, such that the packaged
tree may be copied to another location, which is useful e.g for developer usage
where you wish to check the templates into a revision control system.

.. note::

    Use caution when using this approach as you will need to rebase any local
    changes on updates to the openstack-tripleo-heat-templates package, and
    care will be needed to avoid modifying anything in the tree which the CLI
    tools rely on (such as top-level parameters).  In many cases using the
    :doc:`ExtraConfig <extra_config>` interfaces or specific template overrides
    as outlined above may be preferable.

Here is an example of copying the entire tripleo-heat-templates tree to a
local directory and launching a deployment using the new location::

    cp -r /usr/share/openstack-tripleo-heat-templates /home/stack/
    openstack overcloud deploy --templates /home/stack/openstack-tripleo-heat-templates

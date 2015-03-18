puppet-stack-config
-------------------

puppet-stack-config provides static puppet configuration for a single node
baremetal cloud using the Ironic driver. A yaml template is used to render a
hiera data file at /etc/puppet/hieradata/puppet-stack-config.yaml.

The template rendering takes its input from a set of defined environment
variables.

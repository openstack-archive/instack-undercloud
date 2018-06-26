# Copyright 2015 Red Hat Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import print_function

import copy
import errno
import getpass
import glob
import hashlib
import json
import logging
import netaddr
import os
import platform
import re
import socket
import subprocess
import sys
import tempfile
import time
import uuid

from ironicclient import client as ir_client
from keystoneauth1 import session
from keystoneauth1 import exceptions as ks_exceptions
from keystoneclient import discover
import keystoneauth1.identity.generic as ks_auth
from mistralclient.api import client as mistralclient
from mistralclient.api import base as mistralclient_exc
from novaclient import client as novaclient
from novaclient import exceptions
import os_client_config
from oslo_config import cfg
from oslo_utils import netutils
import psutil
import pystache
import six
from swiftclient import client as swiftclient

from instack_undercloud import validator


# Making these values properties on a class allows us to delay their lookup,
# which makes testing code that interacts with these files much easier.
# NOTE(bnemec): The unit tests rely on these paths being in ~.  If they are
# ever moved the tests may need to be updated to avoid overwriting real files.
class Paths(object):
    @property
    def CONF_PATH(self):
        return os.path.expanduser('~/undercloud.conf')

    # NOTE(bnemec): Deprecated
    @property
    def ANSWERS_PATH(self):
        return os.path.expanduser('~/instack.answers')

    @property
    def PASSWORD_PATH(self):
        return os.path.expanduser('~/undercloud-passwords.conf')

    @property
    def LOG_FILE(self):
        return os.path.expanduser('~/.instack/install-undercloud.log')

    @property
    def WORKBOOK_PATH(self):
        return '/usr/share/openstack-tripleo-common/workbooks'


PATHS = Paths()
DEFAULT_LOG_LEVEL = logging.DEBUG
DEFAULT_LOG_FORMAT = '%(asctime)s %(levelname)s: %(message)s'
DEFAULT_NODE_RESOURCE_CLASS = 'baremetal'
LOG = None
CONF = cfg.CONF
COMPLETION_MESSAGE = """
#############################################################################
Undercloud %(undercloud_operation)s complete.

The file containing this installation's passwords is at
%(password_path)s.

There is also a stackrc file at %(stackrc_path)s.

These files are needed to interact with the OpenStack services, and should be
secured.

#############################################################################
"""
FAILURE_MESSAGE = """
#############################################################################
Undercloud %(undercloud_operation)s failed.

Reason: %(exception)s

See the previous output for details about what went wrong.  The full install
log can be found at %(log_file)s.

#############################################################################
"""
# We need 8 GB, leave a little room for variation in what 8 GB means on
# different platforms.
REQUIRED_MB = 7680
# Control plane network name
PHYSICAL_NETWORK = 'ctlplane'
SUBNETS_DEFAULT = ['ctlplane-subnet']

# Deprecated options
_deprecated_opt_network_gateway = [cfg.DeprecatedOpt(
  'network_gateway', group='DEFAULT')]
_deprecated_opt_network_cidr = [cfg.DeprecatedOpt(
  'network_cidr', group='DEFAULT')]
_deprecated_opt_dhcp_start = [cfg.DeprecatedOpt(
  'dhcp_start', group='DEFAULT')]
_deprecated_opt_dhcp_end = [cfg.DeprecatedOpt('dhcp_end', group='DEFAULT')]
_deprecated_opt_inspection_iprange = [cfg.DeprecatedOpt(
  'inspection_iprange', group='DEFAULT')]

# When adding new options to the lists below, make sure to regenerate the
# sample config by running "tox -e genconfig" in the project root.
_opts = [
    cfg.StrOpt('undercloud_hostname',
               help=('Fully qualified hostname (including domain) to set on '
                     'the Undercloud. If left unset, the '
                     'current hostname will be used, but the user is '
                     'responsible for configuring all system hostname '
                     'settings appropriately.  If set, the undercloud install '
                     'will configure all system hostname settings.'),
               ),
    cfg.StrOpt('local_ip',
               default='192.168.24.1/24',
               help=('IP information for the interface on the Undercloud '
                     'that will be handling the PXE boots and DHCP for '
                     'Overcloud instances.  The IP portion of the value will '
                     'be assigned to the network interface defined by '
                     'local_interface, with the netmask defined by the '
                     'prefix portion of the value.')
               ),
    cfg.StrOpt('undercloud_public_host',
               deprecated_name='undercloud_public_vip',
               default='192.168.24.2',
               help=('Virtual IP or DNS address to use for the public '
                     'endpoints of Undercloud services. Only used with SSL.')
               ),
    cfg.StrOpt('undercloud_admin_host',
               deprecated_name='undercloud_admin_vip',
               default='192.168.24.3',
               help=('Virtual IP or DNS address to use for the admin '
                     'endpoints of Undercloud services. Only used with SSL.')
               ),
    cfg.ListOpt('undercloud_nameservers',
                default=[],
                help=('DNS nameserver(s) to use for the undercloud node.'),
                ),
    cfg.ListOpt('undercloud_ntp_servers',
                default=[],
                help=('List of ntp servers to use.')),
    cfg.StrOpt('overcloud_domain_name',
               default='localdomain',
               help=('DNS domain name to use when deploying the overcloud. '
                     'The overcloud parameter "CloudDomain" must be set to a '
                     'matching value.')
               ),
    cfg.ListOpt('subnets',
                default=SUBNETS_DEFAULT,
                help=('List of routed network subnets for provisioning '
                      'and introspection. Comma separated list of names/tags. '
                      'For each network a section/group needs to be added to '
                      'the configuration file with these parameters set: '
                      'cidr, dhcp_start, dhcp_end, inspection_iprange, '
                      'gateway and masquerade. Note: The section/group must '
                      'be placed before or after any other section. (See '
                      'the example section [ctlplane-subnet] in the sample '
                      'configuration file.)')),
    cfg.StrOpt('local_subnet',
               default=SUBNETS_DEFAULT[0],
               help=('Name of the local subnet, where the PXE boot and DHCP '
                     'interfaces for overcloud instances is located. The IP '
                     'address of the local_ip/local_interface should reside '
                     'in this subnet.')),
    cfg.StrOpt('undercloud_service_certificate',
               default='',
               help=('Certificate file to use for OpenStack service SSL '
                     'connections.  Setting this enables SSL for the '
                     'OpenStack API endpoints, leaving it unset disables SSL.')
               ),
    cfg.BoolOpt('generate_service_certificate',
                default=False,
                help=('When set to True, an SSL certificate will be generated '
                      'as part of the undercloud install and this certificate '
                      'will be used in place of the value for '
                      'undercloud_service_certificate.  The resulting '
                      'certificate will be written to '
                      '/etc/pki/tls/certs/undercloud-[undercloud_public_host].'
                      'pem.  This certificate is signed by CA selected by the '
                      '"certificate_generation_ca" option.')
                ),
    cfg.StrOpt('certificate_generation_ca',
               default='local',
               help=('The certmonger nickname of the CA from which the '
                     'certificate will be requested. This is used only if '
                     'the generate_service_certificate option is set. '
                     'Note that if the "local" CA is selected the '
                     'certmonger\'s local CA certificate will be extracted to '
                     '/etc/pki/ca-trust/source/anchors/cm-local-ca.pem and '
                     'subsequently added to the trust chain.')

               ),
    cfg.StrOpt('service_principal',
               default='',
               help=('The kerberos principal for the service that will use '
                     'the certificate. This is only needed if your CA '
                     'requires a kerberos principal. e.g. with FreeIPA.')
               ),
    cfg.StrOpt('local_interface',
               default='eth1',
               help=('Network interface on the Undercloud that will be '
                     'handling the PXE boots and DHCP for Overcloud '
                     'instances.')
               ),
    cfg.IntOpt('local_mtu',
               default=1500,
               help=('MTU to use for the local_interface.')
               ),
    cfg.StrOpt('masquerade_network',
               default='192.168.24.0/24',
               deprecated_for_removal=True,
               deprecated_reason=('With support for routed networks, '
                                  'masquerading of the provisioning networks '
                                  'is moved to a boolean option for each '
                                  'subnet.'),
               help=('Network that will be masqueraded for external access, '
                     'if required. This should be the subnet used for PXE '
                     'booting.')
               ),
    cfg.StrOpt('hieradata_override',
               default='',
               help=('Path to hieradata override file. If set, the file will '
                     'be copied under /etc/puppet/hieradata and set as the '
                     'first file in the hiera hierarchy. This can be used '
                     'to custom configure services beyond what '
                     'undercloud.conf provides')
               ),
    cfg.StrOpt('net_config_override',
               default='',
               help=('Path to network config override template. If set, this '
                     'template will be used to configure the networking via '
                     'os-net-config. Must be in json format. '
                     'Templated tags can be used within the '
                     'template, see '
                     'instack-undercloud/elements/undercloud-stack-config/'
                     'net-config.json.template for example tags')
               ),
    cfg.StrOpt('inspection_interface',
               default='br-ctlplane',
               deprecated_name='discovery_interface',
               help=('Network interface on which inspection dnsmasq will '
                     'listen.  If in doubt, use the default value.')
               ),
    cfg.BoolOpt('inspection_extras',
                default=True,
                help=('Whether to enable extra hardware collection during '
                      'the inspection process. Requires python-hardware or '
                      'python-hardware-detect package on the introspection '
                      'image.')),
    cfg.BoolOpt('inspection_runbench',
                default=False,
                deprecated_name='discovery_runbench',
                help=('Whether to run benchmarks when inspecting nodes. '
                      'Requires inspection_extras set to True.')
                ),
    cfg.BoolOpt('inspection_enable_uefi',
                default=True,
                help=('Whether to support introspection of nodes that have '
                      'UEFI-only firmware.')
                ),
    cfg.BoolOpt('enable_node_discovery',
                default=False,
                help=('Makes ironic-inspector enroll any unknown node that '
                      'PXE-boots introspection ramdisk in Ironic. By default, '
                      'the "fake" driver is used for new nodes (it is '
                      'automatically enabled when this option is set to True).'
                      ' Set discovery_default_driver to override. '
                      'Introspection rules can also be used to specify driver '
                      'information for newly enrolled nodes.')
                ),
    cfg.StrOpt('discovery_default_driver',
               default='ipmi',
               help=('The default driver or hardware type to use for newly '
                     'discovered nodes (requires enable_node_discovery set to '
                     'True). It is automatically added to enabled_drivers '
                     'or enabled_hardware_types accordingly.')
               ),
    cfg.BoolOpt('undercloud_debug',
                default=True,
                help=('Whether to enable the debug log level for Undercloud '
                      'OpenStack services.')
                ),
    cfg.BoolOpt('undercloud_update_packages',
                default=True,
                help=('Whether to update packages during the Undercloud '
                      'install.')
                ),
    cfg.BoolOpt('enable_tempest',
                default=True,
                help=('Whether to install Tempest in the Undercloud.')
                ),
    cfg.BoolOpt('enable_telemetry',
                default=False,
                help=('Whether to install Telemetry services '
                      '(ceilometer, gnocchi, aodh, panko ) in the Undercloud.')
                ),
    cfg.BoolOpt('enable_ui',
                default=True,
                help=('Whether to install the TripleO UI.')
                ),
    cfg.BoolOpt('enable_validations',
                default=True,
                help=('Whether to install requirements to run the TripleO '
                      'validations.')
                ),
    cfg.BoolOpt('enable_cinder',
                default=False,
                help=('Whether to install the Volume service. It is not '
                      'currently used in the undercloud.')),
    cfg.BoolOpt('enable_novajoin',
                default=False,
                help=('Whether to install novajoin metadata service in '
                      'the Undercloud.')
                ),
    cfg.BoolOpt('enable_container_images_build',
                default=True,
                help=('Whether to enable docker container images to be build '
                      'on the undercloud.')
                ),
    cfg.ListOpt('docker_insecure_registries',
                default=[],
                help=('Array of host/port combiniations of docker insecure '
                      'registries.')
                ),
    cfg.StrOpt('ipa_otp',
               default='',
               help=('One Time Password to register Undercloud node with '
                     'an IPA server.  '
                     'Required when enable_novajoin = True.')
               ),
    cfg.BoolOpt('ipxe_enabled',
                default=True,
                help=('Whether to use iPXE for deploy and inspection.'),
                deprecated_name='ipxe_deploy',
                ),
    cfg.IntOpt('scheduler_max_attempts',
               default=30, min=1,
               help=('Maximum number of attempts the scheduler will make '
                     'when deploying the instance. You should keep it '
                     'greater or equal to the number of bare metal nodes '
                     'you expect to deploy at once to work around '
                     'potential race condition when scheduling.')),
    cfg.BoolOpt('clean_nodes',
                default=False,
                help=('Whether to clean overcloud nodes (wipe the hard drive) '
                      'between deployments and after the introspection.')),
    cfg.ListOpt('enabled_drivers',
                default=['pxe_ipmitool', 'pxe_drac', 'pxe_ilo'],
                help=('List of enabled bare metal drivers.'),
                deprecated_for_removal=True,
                deprecated_reason=('Please switch to hardware types and '
                                   'the enabled_hardware_types option.')),
    cfg.ListOpt('enabled_hardware_types',
                default=['ipmi', 'redfish', 'ilo', 'idrac'],
                help=('List of enabled bare metal hardware types (next '
                      'generation drivers).')),
    cfg.StrOpt('docker_registry_mirror',
               default='',
               help=('An optional docker \'registry-mirror\' that will be'
                     'configured in /etc/docker/daemon.json.')
               ),
    cfg.ListOpt('additional_architectures',
                default=[],
                help=('List of additional architectures enabled in your cloud '
                      'environment. The list of supported values is: %s'
                      % ' '.join(validator.SUPPORTED_ARCHITECTURES))),
    cfg.BoolOpt('enable_routed_networks',
                default=False,
                help=('Enable support for routed ctlplane networks.')),
]

# Routed subnets
_subnets_opts = [
    cfg.StrOpt('cidr',
               default='192.168.24.0/24',
               deprecated_opts=_deprecated_opt_network_cidr,
               help=('Network CIDR for the Neutron-managed subnet for '
                     'Overcloud instances.')),
    cfg.StrOpt('dhcp_start',
               default='192.168.24.5',
               deprecated_opts=_deprecated_opt_dhcp_start,
               help=('Start of DHCP allocation range for PXE and DHCP of '
                     'Overcloud instances on this network.')),
    cfg.StrOpt('dhcp_end',
               default='192.168.24.24',
               deprecated_opts=_deprecated_opt_dhcp_end,
               help=('End of DHCP allocation range for PXE and DHCP of '
                     'Overcloud instances on this network.')),
    cfg.StrOpt('inspection_iprange',
               default='192.168.24.100,192.168.24.120',
               deprecated_opts=_deprecated_opt_inspection_iprange,
               help=('Temporary IP range that will be given to nodes on this '
                     'network during the inspection process. Should not '
                     'overlap with the range defined by dhcp_start and '
                     'dhcp_end, but should be in the same ip subnet.')),
    cfg.StrOpt('gateway',
               default='192.168.24.1',
               deprecated_opts=_deprecated_opt_network_gateway,
               help=('Network gateway for the Neutron-managed network for '
                     'Overcloud instances on this network.')),
    cfg.BoolOpt('masquerade',
                default=False,
                help=('The network will be masqueraded for external access.')),
]

# Passwords, tokens, hashes
_auth_opts = [
    cfg.StrOpt('undercloud_db_password',
               help=('Password used for MySQL root user. '
                     'If left unset, one will be automatically generated.')
               ),
    cfg.StrOpt('undercloud_admin_token',
               help=('Keystone admin token. '
                     'If left unset, one will be automatically generated.')
               ),
    cfg.StrOpt('undercloud_admin_password',
               help=('Keystone admin password. '
                     'If left unset, one will be automatically generated.')
               ),
    cfg.StrOpt('undercloud_glance_password',
               help=('Glance service password. '
                     'If left unset, one will be automatically generated.')
               ),
    cfg.StrOpt('undercloud_heat_encryption_key',
               help=('Heat db encryption key(must be 16, 24, or 32 characters.'
                     ' If left unset, one will be automatically generated.')
               ),
    cfg.StrOpt('undercloud_heat_password',
               help=('Heat service password. '
                     'If left unset, one will be automatically generated.')
               ),
    cfg.StrOpt('undercloud_heat_cfn_password',
               help=('Heat cfn service password. '
                     'If left unset, one will be automatically generated.')
               ),
    cfg.StrOpt('undercloud_neutron_password',
               help=('Neutron service password. '
                     'If left unset, one will be automatically generated.')
               ),
    cfg.StrOpt('undercloud_nova_password',
               help=('Nova service password. '
                     'If left unset, one will be automatically generated.')
               ),
    cfg.StrOpt('undercloud_ironic_password',
               help=('Ironic service password. '
                     'If left unset, one will be automatically generated.')
               ),
    cfg.StrOpt('undercloud_aodh_password',
               help=('Aodh service password. '
                     'If left unset, one will be automatically generated.')
               ),
    cfg.StrOpt('undercloud_gnocchi_password',
               help=('Gnocchi service password. '
                     'If left unset, one will be automatically generated.')
               ),
    cfg.StrOpt('undercloud_ceilometer_password',
               help=('Ceilometer service password. '
                     'If left unset, one will be automatically generated.')
               ),
    cfg.StrOpt('undercloud_panko_password',
               help=('Panko service password. '
                     'If left unset, one will be automatically generated.')
               ),
    cfg.StrOpt('undercloud_ceilometer_metering_secret',
               help=('Ceilometer metering secret. '
                     'If left unset, one will be automatically generated.')
               ),
    cfg.StrOpt('undercloud_ceilometer_snmpd_user',
               default='ro_snmp_user',
               help=('Ceilometer snmpd read-only user. If this value is '
                     'changed from the default, the new value must be passed '
                     'in the overcloud environment as the parameter '
                     'SnmpdReadonlyUserName. This value must be between '
                     '1 and 32 characters long.')
               ),
    cfg.StrOpt('undercloud_ceilometer_snmpd_password',
               help=('Ceilometer snmpd password. '
                     'If left unset, one will be automatically generated.')
               ),
    cfg.StrOpt('undercloud_swift_password',
               help=('Swift service password. '
                     'If left unset, one will be automatically generated.')
               ),
    cfg.StrOpt('undercloud_mistral_password',
               help=('Mistral service password. '
                     'If left unset, one will be automatically generated.')
               ),
    cfg.StrOpt('undercloud_rabbit_cookie',
               help=('Rabbitmq cookie. '
                     'If left unset, one will be automatically generated.')
               ),
    cfg.StrOpt('undercloud_rabbit_password',
               help=('Rabbitmq password. '
                     'If left unset, one will be automatically generated.')
               ),
    cfg.StrOpt('undercloud_rabbit_username',
               help=('Rabbitmq username. '
                     'If left unset, one will be automatically generated.')
               ),
    cfg.StrOpt('undercloud_heat_stack_domain_admin_password',
               help=('Heat stack domain admin password. '
                     'If left unset, one will be automatically generated.')
               ),
    cfg.StrOpt('undercloud_swift_hash_suffix',
               help=('Swift hash suffix. '
                     'If left unset, one will be automatically generated.')
               ),
    cfg.StrOpt('undercloud_haproxy_stats_password',
               help=('HAProxy stats password. '
                     'If left unset, one will be automatically generated.')
               ),
    cfg.StrOpt('undercloud_zaqar_password',
               help=('Zaqar password. '
                     'If left unset, one will be automatically generated.')
               ),
    cfg.StrOpt('undercloud_horizon_secret_key',
               help=('Horizon secret key. '
                     'If left unset, one will be automatically generated.')
               ),
    cfg.StrOpt('undercloud_cinder_password',
               help=('Cinder service password. '
                     'If left unset, one will be automatically generated.')
               ),
    cfg.StrOpt('undercloud_novajoin_password',
               help=('Novajoin vendordata plugin service password. '
                     'If left unset, one will be automatically generated.')
               ),
]
CONF.register_opts(_opts)
CONF.register_opts(_auth_opts, group='auth')


def _load_subnets_config_groups():
    for group in CONF.subnets:
        g = cfg.OptGroup(name=group, title=group)
        CONF.register_opts(_subnets_opts, group=g)


def list_opts():
    return [(None, copy.deepcopy(_opts)),
            (SUBNETS_DEFAULT[0], copy.deepcopy(_subnets_opts)),
            ('auth', copy.deepcopy(_auth_opts)),
            ]


def _configure_logging(level, filename):
    """Does the initial logging configuration

    This should only ever be called once.  If further changes to the logging
    config are needed they should be made directly on the LOG object.

    :param level: The desired logging level
    :param filename: The log file.  Set to None to disable file logging.
    """
    try:
        os.makedirs(os.path.dirname(PATHS.LOG_FILE))
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    logging.basicConfig(filename=filename,
                        format=DEFAULT_LOG_FORMAT,
                        level=level)
    global LOG
    LOG = logging.getLogger(__name__)
    if os.environ.get('OS_LOG_CAPTURE') != '1':
        handler = logging.StreamHandler()
        formatter = logging.Formatter(DEFAULT_LOG_FORMAT)
        handler.setFormatter(formatter)
        LOG.addHandler(handler)


def _load_config():
    conf_params = []
    if os.path.isfile(PATHS.PASSWORD_PATH):
        conf_params += ['--config-file', PATHS.PASSWORD_PATH]
    if os.path.isfile(PATHS.CONF_PATH):
        conf_params += ['--config-file', PATHS.CONF_PATH]
    else:
        LOG.warning('%s does not exist. Using defaults.' % PATHS.CONF_PATH)
    CONF(conf_params)


def _run_command(args, env=None, name=None):
    """Run the command defined by args and return its output

    :param args: List of arguments for the command to be run.
    :param env: Dict defining the environment variables. Pass None to use
        the current environment.
    :param name: User-friendly name for the command being run. A value of
        None will cause args[0] to be used.
    """
    if name is None:
        name = args[0]

    if env is None:
        env = os.environ
    env = env.copy()

    # When running a localized python script, we need to tell it that we're
    # using utf-8 for stdout, otherwise it can't tell because of the pipe.
    env['PYTHONIOENCODING'] = 'utf8'

    try:
        return subprocess.check_output(args,
                                       stderr=subprocess.STDOUT,
                                       env=env).decode('utf-8')
    except subprocess.CalledProcessError as e:
        LOG.error('%s failed: %s', name, e.output)
        raise


def _run_live_command(args, env=None, name=None):
    """Run the command defined by args and log its output

    Takes the same arguments as _run_command, but runs the process
    asynchronously so the output can be logged while the process is still
    running.
    """
    if name is None:
        name = args[0]

    if env is None:
        env = os.environ
    env = env.copy()

    # When running a localized python script, we need to tell it that we're
    # using utf-8 for stdout, otherwise it can't tell because of the pipe.
    env['PYTHONIOENCODING'] = 'utf8'

    process = subprocess.Popen(args, env=env,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
    while True:
        line = process.stdout.readline().decode('utf-8')
        if line:
            LOG.info(line.rstrip())
        if line == '' and process.poll() is not None:
            break
    if process.returncode != 0:
        raise RuntimeError('%s failed. See log for details.' % name)


def _check_hostname():
    """Check system hostname configuration

    Rabbit and Puppet require pretty specific hostname configuration. This
    function ensures that the system hostname settings are valid before
    continuing with the installation.
    """
    if CONF.undercloud_hostname is not None:
        args = ['sudo', 'hostnamectl', 'set-hostname',
                CONF.undercloud_hostname]
        _run_command(args, name='hostnamectl')

    LOG.info('Checking for a FQDN hostname...')
    args = ['sudo', 'hostnamectl', '--static']
    detected_static_hostname = _run_command(args, name='hostnamectl').rstrip()
    LOG.info('Static hostname detected as %s', detected_static_hostname)
    args = ['sudo', 'hostnamectl', '--transient']
    detected_transient_hostname = _run_command(args,
                                               name='hostnamectl').rstrip()
    LOG.info('Transient hostname detected as %s', detected_transient_hostname)
    if detected_static_hostname != detected_transient_hostname:
        LOG.error('Static hostname "%s" does not match transient hostname '
                  '"%s".', detected_static_hostname,
                  detected_transient_hostname)
        LOG.error('Use hostnamectl to set matching hostnames.')
        raise RuntimeError('Static and transient hostnames do not match')
    with open('/etc/hosts') as hosts_file:
        for line in hosts_file:
            if (not line.lstrip().startswith('#') and
                    detected_static_hostname in line.split()):
                break
        else:
            short_hostname = detected_static_hostname.split('.')[0]
            if short_hostname == detected_static_hostname:
                raise RuntimeError('Configured hostname is not fully '
                                   'qualified.')
            sed_cmd = ('sed -i "s/127.0.0.1\(\s*\)/127.0.0.1\\1%s %s /" '
                       '/etc/hosts' %
                       (detected_static_hostname, short_hostname))
            args = ['sudo', '/bin/bash', '-c', sed_cmd]
            _run_command(args, name='hostname-to-etc-hosts')
            LOG.info('Added hostname %s to /etc/hosts',
                     detected_static_hostname)


def _check_memory():
    """Check system memory

    The undercloud will not run properly in less than 8 GB of memory.
    This function verifies that at least that much is available before
    proceeding with install.
    """
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    total_mb = (mem.total + swap.total) / 1024 / 1024
    if total_mb < REQUIRED_MB:
        LOG.error('At least %d MB of memory is required for undercloud '
                  'installation.  A minimum of 8 GB is recommended. '
                  'Only detected %d MB' % (REQUIRED_MB, total_mb))
        raise RuntimeError('Insufficient memory available')


def _check_ipv6_enabled():
    """Test if IPv6 is enabled

    If /proc/net/if_inet6 exist ipv6 sysctl settings are available.
    """
    return os.path.isfile('/proc/net/if_inet6')


def _wrap_ipv6(ip):
    """Wrap a IP address in square brackets if IPv6
    """
    if netutils.is_valid_ipv6(ip):
        return "[%s]" % ip
    return ip


def _check_sysctl():
    """Check sysctl option availability

    The undercloud will not install properly if some of the expected sysctl
    values are not available to be set.
    """
    options = ['net.ipv4.ip_forward', 'net.ipv4.ip_nonlocal_bind']
    if _check_ipv6_enabled():
        options.append('net.ipv6.ip_nonlocal_bind')

    not_available = []
    for option in options:
        path = '/proc/sys/{opt}'.format(opt=option.replace('.', '/'))
        if not os.path.isfile(path):
            not_available.append(option)

    if not_available:
        LOG.error('Required sysctl options are not available. Check '
                  'that your kernel is up to date. Missing: '
                  '{options}'.format(options=", ".join(not_available)))
        raise RuntimeError('Missing sysctl options')


def _cidr_overlaps(a, b):
    return a.first <= b.last and b.first <= a.last


def _validate_network():
    def error_handler(message):
        LOG.error('Undercloud configuration validation failed: %s', message)
        raise validator.FailedValidation(message)

    if (len(CONF.subnets) > 1 and not CONF.enable_routed_networks):
        message = ('Multiple subnets specified: %s but routed networks are '
                   'not enabled.' % CONF.subnets)
        error_handler(message)

    params = {opt.name: CONF[opt.name] for opt in _opts}
    # Get parameters of "local_subnet", pass to validator to ensure parameters
    # such as "local_ip", "undercloud_public_host" and "undercloud_admin_host"
    # are valid
    local_subnet_opts = CONF.get(CONF.local_subnet)
    params.update({opt.name: local_subnet_opts[opt.name]
                   for opt in _subnets_opts})
    validator.validate_config(params, error_handler)

    # Validate subnet parameters
    subnet_cidrs = []
    for subnet in CONF.subnets:
        subnet_opts = CONF.get(subnet)
        params = {opt.name: subnet_opts[opt.name] for opt in _subnets_opts}

        if any(_cidr_overlaps(x, netaddr.IPNetwork(subnet_opts.cidr))
               for x in subnet_cidrs):
            message = ('CIDR of %s, %s, overlaps with another subnet.' %
                       (subnet, subnet_opts.cidr))
            error_handler(message)
        subnet_cidrs.append(netaddr.IPNetwork(subnet_opts.cidr))

        validator.validate_subnet(subnet, params, error_handler)


def _validate_no_ip_change():
    """Disallow provisioning interface IP changes

    Changing the provisioning network IP causes a number of issues, so we
    need to disallow it early in the install before configurations start to
    be changed.
    """
    os_net_config_file = '/etc/os-net-config/config.json'
    # Nothing to do if we haven't already installed
    if not os.path.isfile(
            os.path.expanduser(os_net_config_file)):
        return
    with open(os_net_config_file) as f:
        network_config = json.loads(f.read())
    try:
        ctlplane = [i for i in network_config.get('network_config', [])
                    if i['name'] == 'br-ctlplane'][0]
    except IndexError:
        # Nothing to check if br-ctlplane wasn't configured
        return
    existing_ip = ctlplane['addresses'][0]['ip_netmask']
    if existing_ip != CONF.local_ip:
        message = ('Changing the local_ip is not allowed.  Existing IP: '
                   '%s, Configured IP: %s') % (existing_ip,
                                               CONF.local_ip)
        LOG.error(message)
        raise validator.FailedValidation(message)


def _validate_passwords_file():
    """Disallow updates if the passwords file is missing

    If the undercloud was already deployed, the passwords file needs to be
    present so passwords that can't be changed are persisted.  If the file
    is missing it will break the undercloud, so we should fail-fast and let
    the user know about the problem.
    """
    if (os.path.isfile(os.path.expanduser('~/stackrc')) and
            not os.path.isfile(PATHS.PASSWORD_PATH)):
        message = ('The %s file is missing.  This will cause all service '
                   'passwords to change and break the existing undercloud. ' %
                   PATHS.PASSWORD_PATH)
        raise validator.FailedValidation(message)


def _validate_architecure_options():
    def error_handler(message):
        LOG.error('Undercloud configuration validation failed: %s', message)
        raise validator.FailedValidation(message)

    params = {opt.name: CONF[opt.name] for opt in _opts}
    validator._validate_additional_architectures(params, error_handler)
    validator._validate_ppc64le_exclusive_opts(params, error_handler)


def _validate_configuration():
    try:
        _check_hostname()
        _check_memory()
        _check_sysctl()
        _validate_network()
        _validate_no_ip_change()
        _validate_passwords_file()
        _validate_architecure_options()
    except RuntimeError as e:
        LOG.error('An error occurred during configuration validation, '
                  'please check your host configuration and try again. '
                  'Error message: {error}'.format(error=e))
        sys.exit(1)


def _generate_password(length=40):
    """Create a random password

    Copied from rdomanager-oscplugin.  This should eventually live in
    tripleo-common.
    """
    uuid_str = six.text_type(uuid.uuid4()).encode("UTF-8")
    return hashlib.sha1(uuid_str).hexdigest()[:length]


def _get_service_endpoints(name, format_str, public, internal, admin=None,
                           public_proto='http', internal_proto='http'):
    endpoints = {}
    upper_name = name.upper().replace('-', '_')
    public_port_key = 'port'

    if not admin:
        admin = internal
    if public_proto in ['https', 'wss']:
        public_port_key = 'ssl_port'

    endpoints['UNDERCLOUD_ENDPOINT_%s_PUBLIC' % upper_name] = (
        format_str % (public_proto, _wrap_ipv6(public['host']),
                      public[public_port_key]))
    endpoints['UNDERCLOUD_ENDPOINT_%s_INTERNAL' % upper_name] = (
        format_str % (internal_proto, _wrap_ipv6(internal['host']),
                      internal['port']))
    endpoints['UNDERCLOUD_ENDPOINT_%s_ADMIN' % upper_name] = (
        format_str % (internal_proto, _wrap_ipv6(admin['host']),
                      admin['port']))
    return endpoints


def _generate_endpoints(instack_env):
    local_host = instack_env['LOCAL_IP']
    public_host = local_host
    public_proto = 'http'
    internal_host = local_host
    internal_proto = 'http'
    zaqar_ws_public_proto = 'ws'
    zaqar_ws_internal_proto = 'ws'

    if (CONF.undercloud_service_certificate or
            CONF.generate_service_certificate):
        public_host = CONF.undercloud_public_host
        internal_host = CONF.undercloud_admin_host
        public_proto = 'https'
        zaqar_ws_public_proto = 'wss'

    endpoints = {}

    endpoint_list = [
        ('heat',
            '%s://%s:%d/v1/%%(tenant_id)s',
            {'host': public_host, 'port': 8004, 'ssl_port': 13004},
            {'host': internal_host, 'port': 8004}),
        ('heat-cfn',
            '%s://%s:%d/v1/%%(tenant_id)s',
            {'host': public_host, 'port': 8000, 'ssl_port': 13800},
            {'host': internal_host, 'port': 8000}),
        ('heat-ui-proxy',
            '%s://%s:%d',
            {'host': public_host, 'port': 8004, 'ssl_port': 13004},
            {'host': internal_host, 'port': 8004}),
        ('heat-ui-config',
            '%s://%s:%d/heat/v1/%%(project_id)s',
            {'host': public_host, 'port': 3000, 'ssl_port': 443},
            {'host': internal_host, 'port': 3000}),
        ('neutron',
            '%s://%s:%d',
            {'host': public_host, 'port': 9696, 'ssl_port': 13696},
            {'host': internal_host, 'port': 9696}),
        ('glance',
            '%s://%s:%d',
            {'host': public_host, 'port': 9292, 'ssl_port': 13292},
            {'host': internal_host, 'port': 9292}),
        ('nova',
            '%s://%s:%d/v2.1',
            {'host': public_host, 'port': 8774, 'ssl_port': 13774},
            {'host': internal_host, 'port': 8774}),
        ('nova-ui-proxy',
            '%s://%s:%d',
            {'host': public_host, 'port': 8774, 'ssl_port': 13774},
            {'host': internal_host, 'port': 8774}),
        ('nova-ui-config',
            '%s://%s:%d/nova/v2.1',
            {'host': public_host, 'port': 3000, 'ssl_port': 443},
            {'host': internal_host, 'port': 3000}),
        ('placement',
            '%s://%s:%d/placement',
            {'host': public_host, 'port': 8778, 'ssl_port': 13778},
            {'host': internal_host, 'port': 8778}),
        ('keystone',
            '%s://%s:%d',
            {'host': public_host, 'port': 5000, 'ssl_port': 13000},
            {'host': internal_host, 'port': 5000},
            {'host': internal_host, 'port': 35357}),
        ('keystone-ui-config',
            '%s://%s:%d/keystone/v3',
            {'host': public_host, 'port': 3000, 'ssl_port': 443},
            {'host': internal_host, 'port': 3000},
            {'host': internal_host, 'port': 35357}),
        ('swift',
            '%s://%s:%d/v1/AUTH_%%(tenant_id)s',
            {'host': public_host, 'port': 8080, 'ssl_port': 13808},
            {'host': internal_host, 'port': 8080}),
        ('swift-ui-proxy',
            '%s://%s:%d',
            {'host': public_host, 'port': 8080, 'ssl_port': 13808},
            {'host': internal_host, 'port': 8080}),
        ('swift-ui-config',
            '%s://%s:%d/swift/v1/AUTH_%%(project_id)s',
            {'host': public_host, 'port': 3000, 'ssl_port': 443},
            {'host': internal_host, 'port': 3000}),
        ('ironic',
            '%s://%s:%d',
            {'host': public_host, 'port': 6385, 'ssl_port': 13385},
            {'host': internal_host, 'port': 6385}),
        ('ironic-ui-config',
            '%s://%s:%d/ironic',
            {'host': public_host, 'port': 3000, 'ssl_port': 443},
            {'host': internal_host, 'port': 3000}),
        ('ironic_inspector',
            '%s://%s:%d',
            {'host': public_host, 'port': 5050, 'ssl_port': 13050},
            {'host': internal_host, 'port': 5050}),
        ('ironic_inspector-ui-config',
            '%s://%s:%d/ironic-inspector',
            {'host': public_host, 'port': 3000, 'ssl_port': 443},
            {'host': internal_host, 'port': 3000}),
        ('aodh',
            '%s://%s:%d',
            {'host': public_host, 'port': 8042, 'ssl_port': 13042},
            {'host': internal_host, 'port': 8042}),
        ('gnocchi',
            '%s://%s:%d',
            {'host': public_host, 'port': 8041, 'ssl_port': 13041},
            {'host': internal_host, 'port': 8041}),
        ('panko',
            '%s://%s:%d',
            {'host': public_host, 'port': 8977, 'ssl_port': 13977},
            {'host': internal_host, 'port': 8977}),
        ('mistral',
            '%s://%s:%d/v2',
            {'host': public_host, 'port': 8989, 'ssl_port': 13989},
            {'host': internal_host, 'port': 8989}),
        ('mistral-ui-proxy',
            '%s://%s:%d',
            {'host': public_host, 'port': 8989, 'ssl_port': 13989},
            {'host': internal_host, 'port': 8989}),
        ('mistral-ui-config',
            '%s://%s:%d/mistral/v2',
            {'host': public_host, 'port': 3000, 'ssl_port': 443},
            {'host': internal_host, 'port': 3000}),
        ('zaqar',
            '%s://%s:%d',
            {'host': public_host, 'port': 8888, 'ssl_port': 13888},
            {'host': internal_host, 'port': 8888}),
        ('cinder',
            '%s://%s:%d/v1/%%(tenant_id)s',
            {'host': public_host, 'port': 8776, 'ssl_port': 13776},
            {'host': internal_host, 'port': 8776}),
        ('cinder_v2',
            '%s://%s:%d/v2/%%(tenant_id)s',
            {'host': public_host, 'port': 8776, 'ssl_port': 13776},
            {'host': internal_host, 'port': 8776}),
        ('cinder_v3',
            '%s://%s:%d/v3/%%(tenant_id)s',
            {'host': public_host, 'port': 8776, 'ssl_port': 13776},
            {'host': internal_host, 'port': 8776}),
    ]
    for endpoint_data in endpoint_list:
        endpoints.update(
            _get_service_endpoints(*endpoint_data,
                                   public_proto=public_proto,
                                   internal_proto=internal_proto))

    # Zaqar's websocket endpoint
    # NOTE(jaosorior): Zaqar's websocket endpoint doesn't support being proxied
    # on a different port. If that's done it will ignore the handshake and
    # won't work.
    endpoints.update(_get_service_endpoints(
        'zaqar-websocket',
        '%s://%s:%d',
        {'host': public_host, 'port': 9000, 'ssl_port': 9000},
        {'host': internal_host, 'port': 9000},
        public_proto=zaqar_ws_public_proto,
        internal_proto=zaqar_ws_internal_proto))

    endpoints.update(_get_service_endpoints(
        'zaqar-ui-proxy',
        '%s://%s:%d',
        {'host': public_host, 'port': 9000, 'ssl_port': 443,
         'zaqar_ws_public_proto': 'ws'},
        {'host': internal_host, 'port': 9000},
        public_proto=zaqar_ws_public_proto,
        internal_proto=zaqar_ws_internal_proto))

    endpoints.update(_get_service_endpoints(
        'zaqar-ui-config',
        '%s://%s:%d/zaqar',
        {'host': public_host, 'port': 3000, 'ssl_port': 443,
         'zaqar_ws_public_proto': 'wss'},
        {'host': internal_host, 'port': 3000},
        public_proto=zaqar_ws_public_proto,
        internal_proto=zaqar_ws_internal_proto))

    # The swift admin endpoint has a different format from the others
    endpoints['UNDERCLOUD_ENDPOINT_SWIFT_ADMIN'] = (
        '%s://%s:%s' % (internal_proto, internal_host, 8080))
    instack_env.update(endpoints)


def _write_password_file(instack_env):
    with open(PATHS.PASSWORD_PATH, 'w') as password_file:
        password_file.write('[auth]\n')
        for opt in _auth_opts:
            env_name = opt.name.upper()
            value = CONF.auth[opt.name]
            if not value:
                # Heat requires this encryption key to be a specific length
                if env_name == 'UNDERCLOUD_HEAT_ENCRYPTION_KEY':
                    value = _generate_password(32)
                else:
                    value = _generate_password()
                LOG.info('Generated new password for %s', opt.name)
            instack_env[env_name] = value
            password_file.write('%s=%s\n' % (opt.name, value))
    os.chmod(PATHS.PASSWORD_PATH, 0o600)


def _member_role_exists():
    # This is a workaround for puppet removing the deprecated _member_
    # role on upgrade - if it exists we must restore role assignments
    # or trusts stored in the undercloud heat will break
    user, password, project, auth_url = _get_auth_values()
    auth_kwargs = {
        'auth_url': auth_url,
        'username': user,
        'password': password,
        'project_name': project,
        'project_domain_name': 'Default',
        'user_domain_name': 'Default',
    }
    auth_plugin = ks_auth.Password(**auth_kwargs)
    sess = session.Session(auth=auth_plugin)
    disc = discover.Discover(session=sess)
    c = disc.create_client()
    try:
        member_role = [r for r in c.roles.list() if r.name == '_member_'][0]
    except IndexError:
        # Do nothing if there is no _member_ role
        return
    if c.version == 'v2.0':
        client_projects = c.tenants
    else:
        client_projects = c.projects
    admin_project = [t for t in client_projects.list() if t.name == 'admin'][0]
    admin_user = [u for u in c.users.list() if u.name == 'admin'][0]
    if c.version == 'v2.0':
        try:
            c.roles.add_user_role(admin_user, member_role, admin_project.id)
            LOG.info('Added _member_ role to admin user')
        except ks_exceptions.http.Conflict:
            # They already had the role
            pass
    else:
        try:
            c.roles.grant(member_role,
                          user=admin_user,
                          project=admin_project.id)
            LOG.info('Added _member_ role to admin user')
        except ks_exceptions.http.Conflict:
            # They already had the role
            pass


class InstackEnvironment(dict):
    """An environment to pass to Puppet with some safety checks.

    Keeps lists of variables we add to the operating system environment,
    and ensures that we don't anything not defined there.
    """

    INSTACK_KEYS = {'HOSTNAME', 'ELEMENTS_PATH', 'NODE_DIST', 'JSONFILE',
                    'REG_METHOD', 'REG_HALT_UNREGISTER', 'PUBLIC_INTERFACE_IP'}
    """The variables instack and/or used elements can read."""

    DYNAMIC_KEYS = {'INSPECTION_COLLECTORS', 'INSPECTION_KERNEL_ARGS',
                    'INSPECTION_NODE_NOT_FOUND_HOOK',
                    'TRIPLEO_INSTALL_USER', 'TRIPLEO_UNDERCLOUD_CONF_FILE',
                    'TRIPLEO_UNDERCLOUD_PASSWORD_FILE',
                    'ENABLED_BOOT_INTERFACES', 'ENABLED_POWER_INTERFACES',
                    'ENABLED_RAID_INTERFACES', 'ENABLED_VENDOR_INTERFACES',
                    'ENABLED_MANAGEMENT_INTERFACES', 'SYSCTL_SETTINGS',
                    'LOCAL_IP_WRAPPED', 'ENABLE_ARCHITECTURE_PPC64LE',
                    'INSPECTION_SUBNETS', 'SUBNETS_CIDR_NAT_RULES',
                    'SUBNETS_STATIC_ROUTES', 'MASQUERADE_NETWORKS'}
    """The variables we calculate in _generate_environment call."""

    PUPPET_KEYS = DYNAMIC_KEYS | {opt.name.upper() for _, group in list_opts()
                                  for opt in group}
    """Keys we pass for formatting the resulting hieradata."""

    SET_ALLOWED_KEYS = DYNAMIC_KEYS | INSTACK_KEYS | PUPPET_KEYS
    """Keys which we allow to add/change in this environment."""

    def __init__(self):
        super(InstackEnvironment, self).__init__(os.environ)

    def __setitem__(self, key, value):
        if key not in self.SET_ALLOWED_KEYS:
            raise KeyError('Key %s is not allowed for an InstackEnvironment' %
                           key)
        return super(InstackEnvironment, self).__setitem__(key, value)


def _make_list(values):
    """Generate a list suitable to pass to templates."""
    return '[%s]' % ', '.join('"%s"' % item for item in values)


def _generate_sysctl_settings():
    sysctl_settings = {}
    sysctl_settings.update({"net.ipv4.ip_nonlocal_bind": {"value": 1}})
    if _check_ipv6_enabled():
        sysctl_settings.update({"net.ipv6.ip_nonlocal_bind": {"value": 1}})
    return json.dumps(sysctl_settings)


def _is_classic_driver(name):
    """Poor man's way to detect if something is a driver or a hardware type.

    To be removed when we remove support for classic drivers.
    """
    return (name == 'fake' or
            name.startswith('fake_') or
            name.startswith('pxe_') or
            name.startswith('agent_') or
            name.startswith('iscsi_'))


def _process_drivers_and_hardware_types(instack_env):
    """Populate the environment with ironic driver information."""
    # Ensure correct rendering of the list and uniqueness of the items
    enabled_drivers = set(CONF.enabled_drivers)
    enabled_hardware_types = set(CONF.enabled_hardware_types)
    if CONF.enable_node_discovery:
        if _is_classic_driver(CONF.discovery_default_driver):
            if CONF.discovery_default_driver not in enabled_drivers:
                enabled_drivers.add(CONF.discovery_default_driver)
        else:
            if CONF.discovery_default_driver not in enabled_hardware_types:
                enabled_hardware_types.add(CONF.discovery_default_driver)
        instack_env['INSPECTION_NODE_NOT_FOUND_HOOK'] = 'enroll'
    else:
        instack_env['INSPECTION_NODE_NOT_FOUND_HOOK'] = ''

    # In most cases power and management interfaces are called the same, so we
    # use one variable for them.
    mgmt_interfaces = {'fake', 'ipmitool'}
    # TODO(dtantsur): can we somehow avoid hardcoding hardware types here?
    for hw_type in ('redfish', 'idrac', 'ilo', 'irmc', 'staging-ovirt'):
        if hw_type in enabled_hardware_types:
            mgmt_interfaces.add(hw_type)
    for (hw_type, iface) in [('cisco-ucs-managed', 'ucsm'),
                             ('cisco-ucs-standalone', 'cimc')]:
        if hw_type in enabled_hardware_types:
            mgmt_interfaces.add(iface)

    # Two hardware types use non-default boot interfaces.
    boot_interfaces = {'pxe'}
    for hw_type in ('ilo', 'irmc'):
        if hw_type in enabled_hardware_types:
            boot_interfaces.add('%s-pxe' % hw_type)

    raid_interfaces = {'no-raid'}
    if 'idrac' in enabled_hardware_types:
        raid_interfaces.add('idrac')

    vendor_interfaces = {'no-vendor'}
    for (hw_type, iface) in [('ipmi', 'ipmitool'),
                             ('idrac', 'idrac')]:
        if hw_type in enabled_hardware_types:
            vendor_interfaces.add(iface)

    instack_env['ENABLED_DRIVERS'] = _make_list(enabled_drivers)
    instack_env['ENABLED_HARDWARE_TYPES'] = _make_list(enabled_hardware_types)

    instack_env['ENABLED_BOOT_INTERFACES'] = _make_list(boot_interfaces)
    instack_env['ENABLED_MANAGEMENT_INTERFACES'] = _make_list(mgmt_interfaces)
    instack_env['ENABLED_RAID_INTERFACES'] = _make_list(raid_interfaces)
    instack_env['ENABLED_VENDOR_INTERFACES'] = _make_list(vendor_interfaces)

    # The snmp hardware type uses fake management and snmp power
    if 'snmp' in enabled_hardware_types:
        mgmt_interfaces.add('snmp')
    instack_env['ENABLED_POWER_INTERFACES'] = _make_list(mgmt_interfaces)


def _generate_masquerade_networks():
    env_list = []
    for subnet in CONF.subnets:
        s = CONF.get(subnet)
        if s.masquerade:
            env_list.append(s.cidr)

    # NOTE(hjensas): Remove once deprecated masquerade_network option is gone
    if CONF.masquerade_network and (CONF.masquerade_network not in env_list):
        env_list.append(CONF.masquerade_network)

    return json.dumps(env_list)


def _generate_inspection_subnets():
    env_list = []
    for subnet in CONF.subnets:
        env_dict = {}
        s = CONF.get(subnet)
        env_dict['tag'] = subnet
        env_dict['ip_range'] = s.inspection_iprange
        env_dict['netmask'] = str(netaddr.IPNetwork(s.cidr).netmask)
        env_dict['gateway'] = s.gateway
        env_list.append(env_dict)
    return json.dumps(env_list)


def _generate_subnets_static_routes():
    env_list = []
    local_router = CONF.get(CONF.local_subnet).gateway
    for subnet in CONF.subnets:
        if subnet == str(CONF.local_subnet):
            continue
        s = CONF.get(subnet)
        env_list.append({'ip_netmask': s.cidr,
                         'next_hop': local_router})
    return json.dumps(env_list)


def _generate_subnets_cidr_nat_rules():
    env_list = []
    for subnet in CONF.subnets:
        s = CONF.get(subnet)
        data_format = '"140 {direction} {name} cidr nat": ' \
                      '{{"chain": "FORWARD", "{direction}": "{cidr}", ' \
                      '"proto": "all", "action": "accept"}}'
        env_list.append(data_format.format(
            name=subnet, direction='destination', cidr=s.cidr))
        env_list.append(data_format.format(
            name=subnet, direction='source', cidr=s.cidr))
    # Whitespace after newline required for indentation in templated yaml
    return '\n  '.join(env_list)


def _generate_environment(instack_root):
    """Generate an environment dict for instack

    The returned dict will have the necessary values for use as the env
    parameter when calling instack via the subprocess module.

    :param instack_root: The path containing the instack-undercloud elements
        and json files.
    """
    instack_env = InstackEnvironment()
    # Rabbit uses HOSTNAME, so we need to make sure it's right
    instack_env['HOSTNAME'] = CONF.undercloud_hostname or socket.gethostname()

    # Find the paths we need
    json_file_dir = '/usr/share/instack-undercloud/json-files'
    if not os.path.isdir(json_file_dir):
        json_file_dir = os.path.join(instack_root, 'json-files')
    instack_undercloud_elements = '/usr/share/instack-undercloud'
    if not os.path.isdir(instack_undercloud_elements):
        instack_undercloud_elements = os.path.join(instack_root, 'elements')
    tripleo_puppet_elements = '/usr/share/tripleo-puppet-elements'
    if not os.path.isdir(tripleo_puppet_elements):
        tripleo_puppet_elements = os.path.join(os.getcwd(),
                                               'tripleo-puppet-elements',
                                               'elements')
    if 'ELEMENTS_PATH' in os.environ:
        instack_env['ELEMENTS_PATH'] = os.environ['ELEMENTS_PATH']
    else:
        instack_env['ELEMENTS_PATH'] = (
            '%s:%s:'
            '/usr/share/tripleo-image-elements:'
            '/usr/share/diskimage-builder/elements'
        ) % (tripleo_puppet_elements, instack_undercloud_elements)

    # Distro-specific values
    distro = platform.linux_distribution()[0]
    if distro.startswith('Red Hat Enterprise Linux'):
        instack_env['NODE_DIST'] = os.environ.get('NODE_DIST') or 'rhel7'
        instack_env['JSONFILE'] = (
            os.environ.get('JSONFILE') or
            os.path.join(json_file_dir, 'rhel-7-undercloud-packages.json')
        )
        instack_env['REG_METHOD'] = 'disable'
        instack_env['REG_HALT_UNREGISTER'] = '1'
    elif distro.startswith('CentOS'):
        instack_env['NODE_DIST'] = os.environ.get('NODE_DIST') or 'centos7'
        instack_env['JSONFILE'] = (
            os.environ.get('JSONFILE') or
            os.path.join(json_file_dir, 'centos-7-undercloud-packages.json')
        )
    elif distro.startswith('Fedora'):
        instack_env['NODE_DIST'] = os.environ.get('NODE_DIST') or 'fedora'
        raise RuntimeError('Fedora is not currently supported')
    else:
        raise RuntimeError('%s is not supported' % distro)

    if CONF['additional_architectures']:
        for arch in CONF['additional_architectures']:
            env_name = ('enable_architecture_%s' % arch).upper()
            instack_env[env_name] = six.text_type(True)

    # Convert conf opts to env values
    for opt in _opts:
        env_name = opt.name.upper()
        instack_env[env_name] = six.text_type(CONF[opt.name])

    # Opts that needs extra processing
    if CONF.inspection_runbench and not CONF.inspection_extras:
        raise RuntimeError('inspection_extras must be enabled for '
                           'inspection_runbench to work')
    if CONF.inspection_extras:
        instack_env['INSPECTION_COLLECTORS'] = ('default,extra-hardware,'
                                                'numa-topology,logs')
    else:
        instack_env['INSPECTION_COLLECTORS'] = 'default,logs'

    inspection_kernel_args = []
    if CONF.undercloud_debug:
        inspection_kernel_args.append('ipa-debug=1')
    if CONF.inspection_runbench:
        inspection_kernel_args.append('ipa-inspection-benchmarks=cpu,mem,disk')
    if CONF.inspection_extras:
        inspection_kernel_args.append('ipa-inspection-dhcp-all-interfaces=1')
        inspection_kernel_args.append('ipa-collect-lldp=1')

    instack_env['INSPECTION_KERNEL_ARGS'] = ' '.join(inspection_kernel_args)

    _process_drivers_and_hardware_types(instack_env)
    instack_env['INSPECTION_SUBNETS'] = _generate_inspection_subnets()
    instack_env['SUBNETS_CIDR_NAT_RULES'] = _generate_subnets_cidr_nat_rules()
    instack_env['MASQUERADE_NETWORKS'] = _generate_masquerade_networks()
    instack_env['SUBNETS_STATIC_ROUTES'] = _generate_subnets_static_routes()

    instack_env['SYSCTL_SETTINGS'] = _generate_sysctl_settings()

    instack_env['PUBLIC_INTERFACE_IP'] = instack_env['LOCAL_IP']
    instack_env['LOCAL_IP'] = instack_env['LOCAL_IP'].split('/')[0]
    instack_env['LOCAL_IP_WRAPPED'] = _wrap_ipv6(instack_env['LOCAL_IP'])

    if CONF.docker_registry_mirror:
        instack_env['DOCKER_REGISTRY_MIRROR'] = CONF.docker_registry_mirror
    if CONF.docker_insecure_registries:
        instack_env['DOCKER_INSECURE_REGISTRIES'] = json.dumps(
                CONF.docker_insecure_registries)
    else:
        # For backward compatibility with previous defaults
        instack_env['DOCKER_INSECURE_REGISTRIES'] = json.dumps(
                [instack_env['LOCAL_IP'] + ':' + '8787',
                 CONF.undercloud_admin_host + ':' + '8787'])

    # We're not in a chroot so this doesn't make sense, and it causes weird
    # errors if it's set.
    if instack_env.get('DIB_YUM_REPO_CONF'):
        del instack_env['DIB_YUM_REPO_CONF']

    instack_env['TRIPLEO_INSTALL_USER'] = getpass.getuser()
    instack_env['TRIPLEO_UNDERCLOUD_CONF_FILE'] = PATHS.CONF_PATH
    instack_env['TRIPLEO_UNDERCLOUD_PASSWORD_FILE'] = PATHS.PASSWORD_PATH

    # Mustache conditional logic requires ENABLE_NOVAJOIN to be undefined
    # when novajoin is not enabled.
    if instack_env['ENABLE_NOVAJOIN'].lower() == 'false':
        del instack_env['ENABLE_NOVAJOIN']

    _generate_endpoints(instack_env)

    _write_password_file(instack_env)

    if CONF.generate_service_certificate:
        public_host = CONF.undercloud_public_host
        instack_env['UNDERCLOUD_SERVICE_CERTIFICATE'] = (
            '/etc/pki/tls/certs/undercloud-%s.pem' % public_host)
    elif instack_env['UNDERCLOUD_SERVICE_CERTIFICATE']:
        raw_value = instack_env['UNDERCLOUD_SERVICE_CERTIFICATE']
        abs_cert = os.path.abspath(raw_value)
        if abs_cert != raw_value:
            home_dir = os.path.expanduser('~')
            if os.getcwd() != home_dir and os.path.exists(abs_cert):
                LOG.warning('Using undercloud_service_certificate from '
                            'current directory, please use an absolute path '
                            'to remove ambiguity')
                instack_env['UNDERCLOUD_SERVICE_CERTIFICATE'] = abs_cert
            else:
                instack_env['UNDERCLOUD_SERVICE_CERTIFICATE'] = os.path.join(
                    home_dir, raw_value)

    return instack_env


def _get_template_path(template):
    local_template_path = os.path.join(
        os.path.dirname(__file__),
        '..',
        'templates',
        template)
    installed_template_path = os.path.join(
        '/usr/share/instack-undercloud/templates',
        template)
    if os.path.exists(local_template_path):
        return local_template_path
    else:
        return installed_template_path


def _generate_init_data(instack_env):
    context = instack_env.copy()

    if CONF.hieradata_override:
        data_file = CONF.hieradata_override
        hiera_entry = os.path.splitext(os.path.basename(data_file))[0]
        dst = os.path.join('/etc/puppet/hieradata',
                           os.path.basename(data_file))
        if os.path.abspath(CONF.hieradata_override) != data_file:
            # If we don't have an absolute path, compute it
            data_file = os.path.join(os.path.expanduser('~'), data_file)

        if not os.path.exists(data_file):
            raise RuntimeError(
                "Could not find hieradata_override file '%s'" % data_file)

        _run_command(['sudo', 'mkdir', '-p', '/etc/puppet/hieradata'])
        _run_command(['sudo', 'cp', data_file, dst])
        _run_command(['sudo', 'chmod', '0644', dst])
    else:
        hiera_entry = ''

    if CONF.net_config_override:
        net_config_json = open(CONF.net_config_override).read()
    else:
        net_config_json = \
            open(_get_template_path('net-config.json.template')).read()

    context['HIERADATA_OVERRIDE'] = hiera_entry
    context['UNDERCLOUD_NAMESERVERS'] = json.dumps(
        CONF.undercloud_nameservers)
    partials = {'net_config': net_config_json}
    renderer = pystache.Renderer(partials=partials)
    template = _get_template_path('config.json.template')

    with open(template) as f:
        config_json = renderer.render(f.read(), context)

    config_json = config_json.replace('&quot;', '"')
    cfn_path = '/var/lib/heat-cfntools/cfn-init-data'
    tmp_json = tempfile.mkstemp()[1]
    with open(tmp_json, 'w') as f:
        print(config_json, file=f)

    if not os.path.exists(os.path.dirname(cfn_path)):
        _run_command(['sudo', 'mkdir', '-p', os.path.dirname(cfn_path)])

    _run_command(['sudo', 'mv', tmp_json, cfn_path])
    _run_command(['sudo', 'chmod', '0644', cfn_path])


def _run_instack(instack_env):
    args = ['sudo', '-E', 'instack', '-p', instack_env['ELEMENTS_PATH'],
            '-j', instack_env['JSONFILE'],
            ]
    LOG.info('Running instack')
    _run_live_command(args, instack_env, 'instack')
    LOG.info('Instack completed successfully')


def _run_yum_clean_all(instack_env):
    args = ['sudo', 'yum', 'clean', 'all']
    LOG.info('Running yum clean all')
    _run_live_command(args, instack_env, 'yum-clean-all')
    LOG.info('yum-clean-all completed successfully')


def _run_yum_update(instack_env):
    args = ['sudo', 'yum', 'update', '-y']
    LOG.info('Running yum update')
    _run_live_command(args, instack_env, 'yum-update')
    LOG.info('yum-update completed successfully')


def _get_ovs_interfaces():
    interfaces = glob.glob('/etc/sysconfig/network-scripts/ifcfg-*')
    pattern = "OVSIntPort"
    ovs_interfaces = []
    for interface in interfaces:
        with open(interface, "r") as text:
            for line in text:
                if re.findall(pattern, line):
                    # FIXME (holser). It might be better to get interface from
                    # DEVICE rather than name of file.
                    ovs_interfaces.append(interface.split('-')[-1])
    return ovs_interfaces


def _run_restore_ovs_interfaces(interfaces):
    for interface in interfaces:
        LOG.info('Running restart OVS interface %s', interface)
        _run_command(['sudo', 'ifup', interface])
        LOG.info('Restart OVS interface %s completed successfully', interface)


def _run_orc(instack_env):
    args = ['sudo', 'os-refresh-config']
    LOG.info('Running os-refresh-config')
    _run_live_command(args, instack_env, 'os-refresh-config')
    LOG.info('os-refresh-config completed successfully')


def _extract_from_stackrc(name):
    """Extract authentication values from stackrc

    :param name: The value to be extracted.  For example: OS_USERNAME or
        OS_AUTH_URL.
    """
    with open(os.path.expanduser('~/stackrc')) as f:
        for line in f:
            if name in line:
                parts = line.split('=')
                return parts[1].rstrip()


def _ensure_user_identity(id_path):
    if not os.path.isfile(id_path):
        args = ['ssh-keygen', '-t', 'rsa', '-N', '', '-f', id_path]
        _run_command(args)
        LOG.info('Generated new ssh key in ~/.ssh/id_rsa')


def _get_auth_values():
    """Get auth values from stackrc

    Returns the user, password, project and auth_url as read from stackrc,
    in that order as a tuple.
    """
    user = _extract_from_stackrc('OS_USERNAME')
    password = _run_command(['sudo', 'hiera', 'admin_password']).rstrip()
    project = _extract_from_stackrc('OS_PROJECT_NAME')
    auth_url = _extract_from_stackrc('OS_AUTH_URL')
    return user, password, project, auth_url


def _configure_ssh_keys(nova):
    """Configure default ssh keypair in Nova

    Generates a new ssh key for the current user if one does not already
    exist, then uploads that to Nova as the 'default' keypair.
    """
    id_path = os.path.expanduser('~/.ssh/id_rsa')
    _ensure_user_identity(id_path)

    try:
        nova.keypairs.get('default')
    except exceptions.NotFound:
        with open(id_path + '.pub') as pubkey:
            nova.keypairs.create('default', pubkey.read().rstrip())


def _ensure_ssh_selinux_permission():
    ssh_path = os.path.expanduser('~/.ssh')
    try:
        enforcing = _run_command(['getenforce'])
        if os.path.isdir(ssh_path):
            if 'Enforcing' in enforcing:
                file_perms = _run_command(
                    ['find', ssh_path, '-exec', 'ls', '-lZ', '{}', ';'])
                wrong_perm = False
                for line in file_perms.splitlines():
                    if 'ssh_home_t' not in line:
                        wrong_perm = True
                        break
                if wrong_perm:
                    cmd = ['sudo', 'semanage',
                           'fcontext', '-a', '-t', 'ssh_home_t',
                           "{}(/.*)?".format(ssh_path)]
                    _run_command(cmd)
                    _run_command(['restorecon', '-R', ssh_path])
    except OSError as e:
        if e.errno == os.errno.ENOENT:
            LOG.debug("Not a SeLinux platform")
        else:
            raise


def _delete_default_flavors(nova):
    """Delete the default flavors from Nova

    The m1.tiny, m1.small, etc. flavors are not useful on an undercloud.
    """
    to_delete = ['m1.tiny', 'm1.small', 'm1.medium', 'm1.large', 'm1.xlarge']
    for f in nova.flavors.list():
        if f.name in to_delete:
            nova.flavors.delete(f.id)


def _ensure_flavor(nova, existing, name, profile=None):
    rc_key_name = 'resources:CUSTOM_%s' % DEFAULT_NODE_RESOURCE_CLASS.upper()
    keys = {
        # First, make it request the default resource class
        rc_key_name: "1",
        # Then disable scheduling based on everything else
        "resources:DISK_GB": "0",
        "resources:MEMORY_MB": "0",
        "resources:VCPU": "0"
    }

    if existing is None:
        flavor = nova.flavors.create(name, 4096, 1, 40)

        keys['capabilities:boot_option'] = 'local'
        if profile is not None:
            keys['capabilities:profile'] = profile
        flavor.set_keys(keys)
        message = 'Created flavor "%s" with profile "%s"'

        LOG.info(message, name, profile)
    else:
        LOG.info('Not creating flavor "%s" because it already exists.', name)

        # NOTE(dtantsur): it is critical to ensure that the flavors request
        # the correct resource class, otherwise scheduling will fail.
        old_keys = existing.get_keys()
        for key in old_keys:
            if key.startswith('resources:CUSTOM_') and key != rc_key_name:
                LOG.warning('Not updating flavor %s, as it already has a '
                            'custom resource class %s. Make sure you have '
                            'enough nodes with this resource class.',
                            existing.name, key)
                return

        # Keep existing values
        keys.update(old_keys)
        existing.set_keys(keys)
        LOG.info('Flavor %s updated to use custom resource class %s',
                 name, DEFAULT_NODE_RESOURCE_CLASS)


def _ensure_node_resource_classes(ironic):
    for node in ironic.node.list(limit=0, fields=['uuid', 'resource_class']):
        if node.resource_class:
            if node.resource_class != DEFAULT_NODE_RESOURCE_CLASS:
                LOG.warning('Node %s is using a resource class %s instead '
                            'of the default %s. Make sure you use the correct '
                            'flavor for it.', node.uuid, node.resource_class,
                            DEFAULT_NODE_RESOURCE_CLASS)
            continue

        ironic.node.update(node.uuid,
                           [{'path': '/resource_class', 'op': 'add',
                             'value': DEFAULT_NODE_RESOURCE_CLASS}])
        LOG.info('Node %s resource class was set to %s',
                 node.uuid, DEFAULT_NODE_RESOURCE_CLASS)


def _copy_stackrc():
    args = ['sudo', 'cp', '/root/stackrc', os.path.expanduser('~')]
    try:
        _run_command(args, name='Copy stackrc')
    except subprocess.CalledProcessError:
        LOG.info("/root/stackrc not found, this is OK on initial deploy")
    args = ['sudo', 'chown', getpass.getuser() + ':',
            os.path.expanduser('~/stackrc')]
    _run_command(args, name='Chown stackrc')


def _clean_os_refresh_config():
    orc_dirs = glob.glob('/usr/libexec/os-refresh-config/*')
    args = ['sudo', 'rm', '-rf'] + orc_dirs
    _run_command(args, name='Clean os-refresh-config')


def _clean_os_collect_config():
    occ_dir = '/var/lib/os-collect-config'
    args = ['sudo', 'rm', '-fr', occ_dir]
    _run_command(args, name='Clean os-collect-config')


def _create_mistral_config_environment(instack_env, mistral):
    # Store all the required passwords from the Undercloud
    # in a Mistral environment so they can be accessed
    # by the Mistral actions.

    config_data = {
        'undercloud_ceilometer_snmpd_password':
            instack_env['UNDERCLOUD_CEILOMETER_SNMPD_PASSWORD'],
        'undercloud_db_password':
            instack_env['UNDERCLOUD_DB_PASSWORD']
    }
    env_name = 'tripleo.undercloud-config'
    try:
        env_data = mistral.environments.get(env_name).variables
    except (ks_exceptions.NotFound, mistralclient_exc.APIException):
        # If the environment is not created, we need to
        # create it with the information in config_data
        mistral.environments.create(
            name=env_name,
            description='Undercloud configuration parameters',
            variables=json.dumps(config_data, sort_keys=True)
        )
        return

    # If we are upgrading from an environment without
    # variables defined in config_data, we need to update
    # the environment variables.

    for var, value in iter(config_data.items()):
        if var in env_data:
            if env_data[var] != config_data[var]:
                # Value in config_data is different
                # need to update
                env_data[var] = value
        else:
            # The value in config_data
            # is new, we need to add it
            env_data[var] = value

    # Here we update the current environment
    # with the variables updated
    mistral.environments.update(
        name=env_name,
        description='Undercloud configuration parameters',
        variables=json.dumps(env_data, sort_keys=True)
    )


def _wait_for_mistral_execution(timeout_at, mistral, execution, message='',
                                fail_on_error=False):
    while time.time() < timeout_at:
        exe = mistral.executions.get(execution.id)
        if exe.state == "RUNNING":
            time.sleep(5)
            continue
        if exe.state == "SUCCESS":
            return
        else:
            exe_out = ""
            exe_created_at = time.strptime(exe.created_at,
                                           "%Y-%m-%d %H:%M:%S")
            ae_list = mistral.action_executions.list()
            for ae in ae_list:
                if ((ae.task_name == "run_validation") and
                    (ae.state == "ERROR") and
                    (time.strptime(ae.created_at,  "%Y-%m-%d %H:%M:%S") >
                     exe_created_at)):
                    task = mistral.tasks.get(ae.task_execution_id)
                    task_res = task.to_dict().get('result')
                    exe_out = "%s %s" % (exe_out, task_res)
            error_message = "ERROR %s %s Mistral execution ID: %s" % (
                message, exe_out, execution.id)
            LOG.error(error_message)
            if fail_on_error:
                raise RuntimeError(error_message)
            return
    else:
        exe = mistral.executions.get(execution.id)
        error_message = ("TIMEOUT waiting for execution %s to finish. "
                         "State: %s" % (exe.id, exe.state))
        LOG.error(error_message)
        if fail_on_error:
            raise RuntimeError(error_message)


def _get_session():
    user, password, project, auth_url = _get_auth_values()
    auth_kwargs = {
        'auth_url': auth_url,
        'username': user,
        'password': password,
        'project_name': project,
        'project_domain_name': 'Default',
        'user_domain_name': 'Default',
    }
    auth_plugin = ks_auth.Password(**auth_kwargs)
    return session.Session(auth=auth_plugin)


def _run_validation_groups(groups=[], mistral_url='', timeout=540,
                           fail_on_error=False):
    sess = _get_session()
    mistral = mistralclient.client(mistral_url=mistral_url, session=sess)
    LOG.info('Starting and waiting for validation groups %s ', groups)
    execution = mistral.executions.create(
        'tripleo.validations.v1.run_groups',
        workflow_input={'group_names': groups}
    )
    fail_message = ("error running the validation groups %s " % groups)
    timeout_at = time.time() + timeout
    _wait_for_mistral_execution(timeout_at, mistral, execution, fail_message,
                                fail_on_error)


def _create_default_plan(mistral, plans, timeout=360):
    plan_name = 'overcloud'
    queue_name = str(uuid.uuid4())

    if plan_name in plans:
        LOG.info('Not creating default plan "%s" because it already exists.',
                 plan_name)
        return

    execution = mistral.executions.create(
        'tripleo.plan_management.v1.create_deployment_plan',
        workflow_input={
            'container': plan_name,
            'queue_name': queue_name,
            'use_default_templates': True,
        }
    )
    timeout_at = time.time() + timeout
    fail_message = ("error creating the default Deployment Plan %s "
                    "Check the create_default_deployment_plan execution "
                    "in Mistral with openstack workflow execution list " %
                    plan_name)
    _wait_for_mistral_execution(timeout_at, mistral, execution, fail_message,
                                fail_on_error=True)


def _prepare_ssh_environment(mistral):
    mistral.executions.create('tripleo.validations.v1.copy_ssh_key')


def _create_logging_cron(mistral):
    LOG.info('Configuring an hourly cron trigger for tripleo-ui logging')
    mistral.cron_triggers.create(
        'publish-ui-logs-hourly',
        'tripleo.plan_management.v1.publish_ui_logs_to_swift',
        pattern='0 * * * *'
    )


def _post_config_mistral(instack_env, mistral, swift):
    LOG.info('Configuring Mistral workbooks')

    for workbook in [w for w in mistral.workbooks.list()
                     if w.name.startswith('tripleo')]:
        mistral.workbooks.delete(workbook.name)

    managed_tag = 'tripleo-common-managed'

    all_workflows = mistral.workflows.list()
    workflow_tags = set()
    for workflow in all_workflows:
        workflow_tags.update(workflow.tags)

    # If at least one workflow is tagged, then we should only delete those.
    # Otherwise we should revert to the previous behaviour - this is required
    # for the initial upgrade.
    # TODO(d0ugal): From Q onwards we should only ever delete workflows with
    # the tripleo-common tag.
    if 'tripleo-common-managed' in workflow_tags:
        workflows_delete = [w.name for w in all_workflows
                            if managed_tag in w.tags]
    else:
        workflows_delete = [w.name for w in all_workflows
                            if w.name.startswith('tripleo')]

    # in order to delete workflows they should have no triggers associated
    for trigger in [t for t in mistral.cron_triggers.list()
                    if t.workflow_name in workflows_delete]:
        mistral.cron_triggers.delete(trigger.name)

    for workflow_name in workflows_delete:
        mistral.workflows.delete(workflow_name)

    for workbook in [f for f in os.listdir(PATHS.WORKBOOK_PATH)
                     if os.path.isfile(os.path.join(PATHS.WORKBOOK_PATH, f))]:
        mistral.workbooks.create(os.path.join(PATHS.WORKBOOK_PATH, workbook))
    LOG.info('Mistral workbooks configured successfully')

    plans = [container["name"] for container in swift.get_account()[1]]

    _create_mistral_config_environment(instack_env, mistral)
    _create_default_plan(mistral, plans)
    _create_logging_cron(mistral)

    if CONF.enable_validations:
        _prepare_ssh_environment(mistral)


def _migrate_to_convergence(heat):
    """Migrate all active stacks to use the convergence engine

    This appears to be a noop if the stack has already been migrated, so it
    should be safe to run unconditionally.

    :param heat: A heat client instance
    """
    for stack in heat.stacks.list():
        LOG.info('Migrating stack "%s" to convergence engine', stack.id)
        args = ['sudo', '-E', 'heat-manage', 'migrate_convergence_1', stack.id]
        _run_command(args, name='heat-manage')
        LOG.info('Finished migrating stack "%s"', stack.id)


def _post_config(instack_env, upgrade):
    _copy_stackrc()
    user, password, project, auth_url = _get_auth_values()
    sess = _get_session()
    nova = novaclient.Client(2, session=sess)

    ironic = ir_client.get_client(1, session=sess,
                                  os_ironic_api_version='1.21')

    sdk = os_client_config.make_sdk(auth_url=auth_url,
                                    project_name=project,
                                    username=user,
                                    password=password,
                                    project_domain_name='Default',
                                    user_domain_name='Default')

    network = _ensure_neutron_network(sdk)
    _config_neutron_segments_and_subnets(sdk, network.id)

    _configure_ssh_keys(nova)
    _ensure_ssh_selinux_permission()
    _delete_default_flavors(nova)

    _ensure_node_resource_classes(ironic)

    all_flavors = {f.name: f for f in nova.flavors.list()}
    for name, profile in [('baremetal', None),
                          ('control', 'control'),
                          ('compute', 'compute'),
                          ('ceph-storage', 'ceph-storage'),
                          ('block-storage', 'block-storage'),
                          ('swift-storage', 'swift-storage')]:
        _ensure_flavor(nova, all_flavors.get(name), name, profile)

    mistral_url = instack_env['UNDERCLOUD_ENDPOINT_MISTRAL_PUBLIC']
    mistral = mistralclient.client(
        mistral_url=mistral_url,
        session=sess)
    swift = swiftclient.Connection(
        authurl=auth_url,
        session=sess
    )
    _post_config_mistral(instack_env, mistral, swift)
    _member_role_exists()

    # NOTE(bnemec): We are turning on the convergence engine in Queens, so we
    # need to migrate all existing stacks on upgrade.  This functionality can
    # be removed in Rocky as all stacks should have been migrated by then.
    if upgrade:
        heat = os_client_config.make_client('orchestration',
                                            auth_url=auth_url,
                                            username=user,
                                            password=password,
                                            project_name=project,
                                            project_domain_name='Default',
                                            user_domain_name='Default')
        _migrate_to_convergence(heat)


def _ensure_neutron_network(sdk):
    try:
        network = list(sdk.network.networks(name=PHYSICAL_NETWORK))
        if not network:
            mtu = CONF.get("local_mtu")
            network = sdk.network.create_network(
                name=PHYSICAL_NETWORK, provider_network_type='flat',
                provider_physical_network=PHYSICAL_NETWORK, mtu=mtu)
            LOG.info("Network created %s", network)
            # (hjensas) Delete the default segment, we create a new segment
            # per subnet later.
            segments = list(sdk.network.segments(network_id=network.id))
            sdk.network.delete_segment(segments[0].id)
            LOG.info("Default segment on network %s deleted.", network.name)
        else:
            LOG.info("Not creating %s network, because it already exists.",
                     PHYSICAL_NETWORK)
            network = network[0]
    except Exception as e:
        LOG.info("Network create/update failed %s", e)
        raise

    return network


def _neutron_subnet_create(sdk, network_id, cidr, gateway, host_routes,
                           allocation_pool, name, segment_id):
    try:
        # DHCP_START contains a ":" then assume a IPv6 subnet
        if ':' in allocation_pool[0]['start']:
            host_routes = ''
            subnet = sdk.network.create_subnet(
                name=name,
                cidr=cidr,
                gateway_ip=gateway,
                host_routes=host_routes,
                enable_dhcp=True,
                ip_version='6',
                ipv6_address_mode='dhcpv6-stateless',
                ipv6_ra_mode='dhcpv6-stateless',
                allocation_pools=allocation_pool,
                network_id=network_id,
                segment_id=segment_id)
        else:
            subnet = sdk.network.create_subnet(
                name=name,
                cidr=cidr,
                gateway_ip=gateway,
                host_routes=host_routes,
                enable_dhcp=True,
                ip_version='4',
                allocation_pools=allocation_pool,
                network_id=network_id,
                segment_id=segment_id)
        LOG.info("Subnet created %s", subnet)
    except Exception as e:
        LOG.error("Create subnet %s failed: %s", name, e)
        raise

    return subnet


def _neutron_subnet_update(sdk, subnet_id, gateway, host_routes,
                           allocation_pool, name):
    try:
        # DHCP_START contains a ":" then assume a IPv6 subnet
        if ':' in allocation_pool[0]['start']:
            host_routes = ''
        subnet = sdk.network.update_subnet(
                   subnet_id,
                   name=name,
                   gateway_ip=gateway,
                   host_routes=host_routes,
                   allocation_pools=allocation_pool)
        LOG.info("Subnet updated %s", subnet)
    except Exception as e:
        LOG.error("Update subnet %s failed: %s", name, e)
        raise


def _neutron_segment_create(sdk, name, network_id, phynet):
    try:
        segment = sdk.network.create_segment(
                    name=name,
                    network_id=network_id,
                    physical_network=phynet,
                    network_type='flat')
        LOG.info("Neutron Segment created %s", segment)
    except Exception as e:
        LOG.info("Neutron Segment %s create failed %s", name, e)
        raise

    return segment


def _neutron_segment_update(sdk, segment_id, name):
    try:
        segment = sdk.network.update_segment(segment_id, name=name)
        LOG.info("Neutron Segment updated %s", segment)
    except Exception as e:
        LOG.info("Neutron Segment %s update failed %s", name, e)
        raise


def _ensure_neutron_router(sdk, name, subnet_id):
    try:
        router = sdk.network.create_router(name=name, admin_state_up='true')
        sdk.network.add_interface_to_router(router.id, subnet_id=subnet_id)
    except Exception as e:
        LOG.error("Create router for subnet %s failed: %s", name, e)
        raise


def _get_subnet(sdk, cidr, network_id):
    try:
        subnet = list(sdk.network.subnets(cidr=cidr, network_id=network_id))
    except Exception:
        raise

    return False if not subnet else subnet[0]


def _get_segment(sdk, phy, network_id):
    try:
        segment = list(sdk.network.segments(physical_network=phy,
                                            network_id=network_id))
    except Exception:
        raise

    return False if not segment else segment[0]


def _config_neutron_segments_and_subnets(sdk, ctlplane_id):
    s = CONF.get(CONF.local_subnet)
    subnet = _get_subnet(sdk, s.cidr, ctlplane_id)
    if subnet and not subnet.segment_id:
        LOG.warn("Local subnet %s already exists and is not associated with a "
                 "network segment. Any additional subnets will be ignored.",
                 CONF.local_subnet)
        host_routes = [{'destination': '169.254.169.254/32',
                        'nexthop': str(netaddr.IPNetwork(CONF.local_ip).ip)}]
        allocation_pool = [{'start': s.dhcp_start, 'end': s.dhcp_end}]
        _neutron_subnet_update(sdk, subnet.id, s.gateway, host_routes,
                               allocation_pool, CONF.local_subnet)
        # If the subnet is IPv6 we need to start a router so that router
        # advertisments are sent out for stateless IP addressing to work.
        if ':' in s.dhcp_start:
            _ensure_neutron_router(sdk, CONF.local_subnet, subnet.id)
    else:
        for name in CONF.subnets:
            s = CONF.get(name)

            phynet = name
            metadata_nexthop = s.gateway
            if name == CONF.local_subnet:
                phynet = PHYSICAL_NETWORK
                metadata_nexthop = str(netaddr.IPNetwork(CONF.local_ip).ip)

            host_routes = [{'destination': '169.254.169.254/32',
                            'nexthop': metadata_nexthop}]
            allocation_pool = [{'start': s.dhcp_start, 'end': s.dhcp_end}]

            subnet = _get_subnet(sdk, s.cidr, ctlplane_id)
            segment = _get_segment(sdk, phynet, ctlplane_id)

            if name == CONF.local_subnet:
                if ((subnet and not segment) or
                   (subnet and segment and subnet.segment_id != segment.id)):
                    LOG.error(
                      'The cidr: %s of the local subnet is already used in '
                      'subnet: %s associated with segment_id: %s.' %
                      (s.cidr, subnet.id, subnet.segment_id))
                    raise RuntimeError('Local subnet cidr already associated.')

            if subnet:
                _neutron_segment_update(sdk, subnet.segment_id, name)
                _neutron_subnet_update(sdk, subnet.id, s.gateway, host_routes,
                                       allocation_pool, name)
            else:
                if segment:
                    _neutron_segment_update(sdk, segment.id, name)
                else:
                    segment = _neutron_segment_create(sdk, name,
                                                      ctlplane_id, phynet)
                if CONF.enable_routed_networks:
                    subnet = _neutron_subnet_create(sdk, ctlplane_id, s.cidr,
                                                    s.gateway, host_routes,
                                                    allocation_pool, name,
                                                    segment.id)
                elif name == CONF.local_subnet:
                    # Create subnet with segment_id: None if routed networks
                    # is not enabled.
                    # TODO(hjensas): Deprecate option and remove this once
                    # tripleo-ui can support managing baremetal port
                    # attributes.
                    subnet = _neutron_subnet_create(sdk, ctlplane_id, s.cidr,
                                                    s.gateway, host_routes,
                                                    allocation_pool, name,
                                                    None)

            # If the subnet is IPv6 we need to start a router so that router
            # advertisments are sent out for stateless IP addressing to work.
            if ':' in s.dhcp_start:
                _ensure_neutron_router(sdk, name, subnet.id)


def _handle_upgrade_fact(upgrade=False):
    """Create an upgrade fact for use in puppet

    Since we don't run different puppets depending on if it's an upgrade or
    not, we need to be able to pass a flag into puppet to let it know if
    we're doing an upgrade. This is helpful when trying to handle state
    transitions from an already installed undercloud. This function creates
    a static fact named undercloud_upgrade only after the install has occurred.
    When invoked with upgrade=True, the $::undercloud_upgrade fact should
    be set to true.

    :param upgrade: Boolean indicating if this is an upgrade action or not
    """

    fact_string = 'undercloud_upgrade={}'.format(upgrade)
    fact_path = '/etc/facter/facts.d/undercloud_upgrade.txt'
    if not os.path.exists(os.path.dirname(fact_path)) and upgrade:
        _run_command(['sudo', 'mkdir', '-p', os.path.dirname(fact_path)])

    # We only need to ensure the fact is correct when we've already installed
    # the undercloud.
    if os.path.exists(os.path.dirname(fact_path)):
        tmp_fact = tempfile.mkstemp()[1]
        with open(tmp_fact, 'w') as f:
            f.write(fact_string.lower())
        _run_command(['sudo', 'mv', tmp_fact, fact_path])
        _run_command(['sudo', 'chmod', '0644', fact_path])


def _die_tuskar_die():
    """Remove tuskar* packages

    Make sure to remove tuskar https://bugs.launchpad.net/tripleo/+bug/1691744
    # openstack-[tuskar, tuskar-ui, tuskar-ui-extras] & python-tuskarclient
    """
    try:
        _run_command(['sudo', 'yum', 'remove', '-y', '*tuskar*'])
    except subprocess.CalledProcessError as e:
        LOG.error('Error with tuskar removal task %s - continuing', e.output)


def install(instack_root, upgrade=False):
    """Install the undercloud

    :param instack_root: The path containing the instack-undercloud elements
        and json files.
    """
    undercloud_operation = "upgrade" if upgrade else "install"
    try:
        _configure_logging(DEFAULT_LOG_LEVEL, PATHS.LOG_FILE)
        LOG.info('Logging to %s', PATHS.LOG_FILE)
        _load_config()
        _load_subnets_config_groups()
        # Since 'subnets' parameter in opts is used to dynamically
        # add per network groups, re-load config.
        _load_config()
        _clean_os_refresh_config()
        _clean_os_collect_config()
        _validate_configuration()
        instack_env = _generate_environment(instack_root)
        _generate_init_data(instack_env)
        ovs_interfaces = _get_ovs_interfaces()
        if upgrade:
            # Even if we backport https://review.openstack.org/#/c/457478/
            # into stable branches of puppet-ironic, we still need a way
            # to handle existing deployments.
            # This task will fix ironic-dbsync.log ownership on existing
            # deployments during an upgrade. It can be removed after we
            # release Pike.
            _run_command(['sudo', '/usr/bin/chown', 'ironic:ironic',
                          '/var/log/ironic/ironic-dbsync.log'])
            _die_tuskar_die()
        if CONF.undercloud_update_packages:
            _run_yum_clean_all(instack_env)
            if ovs_interfaces:
                _run_restore_ovs_interfaces(ovs_interfaces)
            _run_yum_update(instack_env)
        _handle_upgrade_fact(upgrade)
        _run_instack(instack_env)
        _run_orc(instack_env)
        # FIXME (holser). The RC of issue is in OVS flow restore. Once
        # 'systemctl reload openvswitch' is fixed ovs port restoration can be
        # removed.
        if ovs_interfaces:
            _run_restore_ovs_interfaces(ovs_interfaces)
        _post_config(instack_env, upgrade)
        _run_command(['sudo', 'rm', '-f', '/tmp/svc-map-services'], None, 'rm')
        if upgrade and CONF.enable_validations:  # Run post-upgrade validations
            mistral_url = instack_env['UNDERCLOUD_ENDPOINT_MISTRAL_PUBLIC']
            _run_validation_groups(["post-upgrade"], mistral_url)
    except Exception as e:
        LOG.debug("An exception occurred", exc_info=True)
        LOG.error(FAILURE_MESSAGE,
                  {'undercloud_operation': undercloud_operation,
                   'exception': six.text_type(e),
                   'log_file': PATHS.LOG_FILE})
        if CONF.undercloud_debug:
            raise
        sys.exit(1)
    else:
        LOG.info(COMPLETION_MESSAGE,
                 {'undercloud_operation': undercloud_operation,
                  'password_path': PATHS.PASSWORD_PATH,
                  'stackrc_path': os.path.expanduser('~/stackrc')})


def _is_database_upgrade_needed():
    """Check whether a yum update will cause an major version update
       for the database.

    :return whether an update will happen
    :rtype bool
    """
    need_upgrade = False
    try:
        args = ['sudo', 'rpm', '--query',
                '--queryformat', '%{VERSION}', 'mariadb-server']
        installed = subprocess.check_output(args).strip()
        LOG.info('Current mariadb version is: %s' % installed)
        args = ['sudo', 'repoquery', '--pkgnarrow=updates',
                '--queryformat', '%{VERSION}', 'mariadb-server']
        available = subprocess.check_output(args).strip()
        LOG.info('Available mariadb version is: %s' %
                 (available or "(no new version available)"))
        if available:
            # compare major versions majorX.majorY.minor
            major_installed, major_available = \
                [re.sub(r'^(\d+\.\d+)\..*', r'\1', ver) for
                 ver in [installed, available]]

            if not major_installed or not major_available:
                raise RuntimeError('Could not determine mariadb versions '
                                   '(installed:"%s", available:"%s"' %
                                   (major_installed, major_available))

            need_upgrade = (major_available != major_installed)
            if need_upgrade:
                LOG.info('Major versions differ (%s vs %s), '
                         'database needs an upgrade' %
                         (major_installed, major_available))
    except subprocess.CalledProcessError:
        LOG.error('Could not determine if mariadb will be updated')
        raise
    return need_upgrade


def pre_upgrade():
    _configure_logging(DEFAULT_LOG_LEVEL, PATHS.LOG_FILE)

    # Don't upgrade undercloud unless overcloud is in *_COMPLETE.
    # As we're migrating overcloud stack to convergence in post_config,
    # which would fail otherwise. It's better to fail fast.
    user, password, project, auth_url = _get_auth_values()
    heat = os_client_config.make_client('orchestration',
                                        auth_url=auth_url,
                                        username=user,
                                        password=password,
                                        project_name=project,
                                        project_domain_name='Default',
                                        user_domain_name='Default')
    for stack in heat.stacks.list():
        if stack.status != 'COMPLETE':
            LOG.error('Can not upgrade undercloud with FAILED overcloud')
            sys.exit(1)

    args = ['sudo', 'systemctl', 'stop', 'openstack-*', 'neutron-*',
            'openvswitch', 'httpd']
    LOG.info('Stopping OpenStack and related services')
    _run_live_command(args, name='systemctl stop')
    LOG.info('Services stopped successfully')

    # Ensure nova data migrations are complete before upgrading packages
    LOG.info('Running Nova online data migration')
    _run_command(['sudo', '-E', '/usr/bin/nova-manage', 'db',
                  'online_data_migrations'])
    LOG.info('Nova online data migration completed')

    args = ['sudo', 'yum', 'install', '-y', 'ansible-pacemaker']
    LOG.info('Installing Ansible Pacemaker module')
    _run_live_command(args, name='install ansible')
    LOG.info('Ansible pacemaker install completed successfully')

    # Check whether a major version upgrade is pending for the database
    mariadb_upgrade = _is_database_upgrade_needed()

    if mariadb_upgrade:
        args = ['sudo', 'systemctl', 'stop', 'mariadb']
        LOG.info('Stopping OpenStack database before upgrade')
        _run_live_command(args, name='systemctl stop mariadb')
        LOG.info('Database stopped successfully')

    args = ['sudo', 'yum', 'update', '-y']
    LOG.info('Updating full system')
    _run_live_command(args, name='yum update')
    LOG.info('Update completed successfully')

    if mariadb_upgrade:
        args = ['sudo', 'systemctl', 'start', 'mariadb']
        LOG.info('Start OpenStack database after upgrade')
        _run_live_command(args, name='systemctl start mariadb')
        LOG.info('Database started successfully')

        args = ['sudo', 'mysql_upgrade']
        LOG.info('Run online upgrade of the database')
        _run_live_command(args, name='mysql_upgrade')
        LOG.info('Database upgraded successfully')

        args = ['sudo', 'systemctl', 'restart', 'mariadb']
        LOG.info('Restart OpenStack database for upgrade to take effect')
        _run_live_command(args, name='systemctl restart mariadb')
        LOG.info('Database restarted successfully')

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
import os
import platform
import socket
import subprocess
import sys
import tempfile
import time
import uuid

from keystoneclient import exceptions as ks_exceptions
from keystoneclient import auth
from keystoneclient import session
from keystoneclient import discover
from mistralclient.api import client as mistralclient
from mistralclient.api import base as mistralclient_base
from novaclient import client as novaclient
from novaclient import exceptions
from oslo_config import cfg
import psutil
import pystache
import six

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


PATHS = Paths()
DEFAULT_LOG_LEVEL = logging.DEBUG
DEFAULT_LOG_FORMAT = '%(asctime)s %(levelname)s: %(message)s'
LOG = None
CONF = cfg.CONF
COMPLETION_MESSAGE = """
#############################################################################
Undercloud install complete.

The file containing this installation's passwords is at
%(password_path)s.

There is also a stackrc file at %(stackrc_path)s.

These files are needed to interact with the OpenStack services, and should be
secured.

#############################################################################
"""
CIDR_DEPRECATION_MESSAGE = """
*****************************************************************************
The old default CIDR of 192.0.2.0/24 is deprecated due to it being an
unroutable address range under RFC 5737.  This default will change in the
Ocata release of OpenStack, so you should stop using the default CIDR and set
a valid, routable CIDR instead.

Note that if you have already deployed an overcloud with the 192.0.2.0/24
CIDR, it will not be possible to change it without re-deploying.  If the
overcloud cannot be re-deployed, you must explicitly set the network values
in undercloud.conf to ensure continued use of the 192.0.2.0/24 CIDR during
future upgrades.
*****************************************************************************
"""
# We need 4 GB, leave a little room for variation in what 4 GB means on
# different platforms.
REQUIRED_MB = 3750


# Allow logging of a warning at the end of the deploy if the deprecated cidr
# is in use.
deprecated_cidr = False


# When adding new options to the lists below, make sure to regenerate the
# sample config by running "tox -e genconfig" in the project root.
_opts = [
    cfg.StrOpt('image_path',
               default='.',
               help=('Local file path to the necessary images. The path '
                     'should be a directory readable by the current user '
                     'that contains the full set of images.'),
               ),
    cfg.StrOpt('undercloud_hostname',
               help=('Fully qualified hostname (including domain) to set on '
                     'the Undercloud. If left unset, the '
                     'current hostname will be used, but the user is '
                     'responsible for configuring all system hostname '
                     'settings appropriately.  If set, the undercloud install '
                     'will configure all system hostname settings.'),
               ),
    cfg.StrOpt('local_ip',
               default='192.0.2.1/24',
               help=('IP information for the interface on the Undercloud '
                     'that will be handling the PXE boots and DHCP for '
                     'Overcloud instances.  The IP portion of the value will '
                     'be assigned to the network interface defined by '
                     'local_interface, with the netmask defined by the '
                     'prefix portion of the value.')
               ),
    cfg.StrOpt('network_gateway',
               default='192.0.2.1',
               help=('Network gateway for the Neutron-managed network for '
                     'Overcloud instances. This should match the local_ip '
                     'above when using masquerading.')
               ),
    cfg.StrOpt('undercloud_public_vip',
               default='192.0.2.2',
               help=('Virtual IP address to use for the public endpoints of '
                     'Undercloud services. Only used with SSL.')
               ),
    cfg.StrOpt('undercloud_admin_vip',
               default='192.0.2.3',
               help=('Virtual IP address to use for the admin endpoints of '
                     'Undercloud services. Only used with SSL.')
               ),
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
                      '/etc/pki/tls/certs/undercloud-[undercloud_public_vip].'
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
    cfg.StrOpt('network_cidr',
               sample_default='192.0.2.0/24',
               help=('Network CIDR for the Neutron-managed network for '
                     'Overcloud instances. This should be the subnet used '
                     'for PXE booting. The current default for this value '
                     'is 192.0.2.0/24, but this is deprecated due to it being '
                     'a non-routable CIDR under RFC 5737. The default value '
                     'for this option will be changed in the Ocata release. '
                     'A different, valid CIDR should be selected to avoid '
                     'problems. If an overcloud has already been deployed '
                     'with the 192.0.2.0/24 CIDR and therefore the CIDR '
                     'cannot be changed, you must set this option to '
                     '192.0.2.0/24 explicitly to avoid it changing in future '
                     'releases, and all other network options related to the '
                     'CIDR (e.g. local_ip) must also be set to maintain a '
                     'valid configuration.')
               ),
    cfg.StrOpt('masquerade_network',
               default='192.0.2.0/24',
               help=('Network that will be masqueraded for external access, '
                     'if required. This should be the subnet used for PXE '
                     'booting.')
               ),
    cfg.StrOpt('dhcp_start',
               default='192.0.2.5',
               help=('Start of DHCP allocation range for PXE and DHCP of '
                     'Overcloud instances.')
               ),
    cfg.StrOpt('dhcp_end',
               default='192.0.2.24',
               help=('End of DHCP allocation range for PXE and DHCP of '
                     'Overcloud instances.')
               ),
    cfg.StrOpt('hieradata_override',
               default='',
               help=('Path to hieradata override file. If set, the file will '
                     'be copied under /etc/puppet/hieradata and set as the '
                     'first file in the hiera hierarchy. This can be used to '
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
    cfg.StrOpt('inspection_iprange',
               default='192.0.2.100,192.0.2.120',
               deprecated_name='discovery_iprange',
               help=('Temporary IP range that will be given to nodes during '
                     'the inspection process.  Should not overlap with the '
                     'range defined by dhcp_start and dhcp_end, but should '
                     'be in the same network.')
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
    cfg.BoolOpt('undercloud_debug',
                default=True,
                help=('Whether to enable the debug log level for Undercloud '
                      'OpenStack services.')
                ),
    cfg.BoolOpt('enable_tempest',
                default=True,
                help=('Whether to install Tempest in the Undercloud.')
                ),
    cfg.BoolOpt('enable_mistral',
                default=True,
                help=('Whether to install Mistral services in the Undercloud.')
                ),
    cfg.BoolOpt('enable_zaqar',
                default=True,
                help=('Whether to install Zaqar services in the Undercloud.')
                ),
    cfg.BoolOpt('enable_telemetry',
                default=True,
                help=('Whether to install Telemetry services '
                      '(ceilometer, aodh) in the Undercloud.')
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
    cfg.BoolOpt('ipxe_enabled',
                default=True,
                help=('Whether to use iPXE for deploy and inspection.'),
                deprecated_name='ipxe_deploy',
                ),
    cfg.BoolOpt('store_events',
                default=False,
                help=('Whether to store events in the Undercloud Ceilometer.')
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
]

# Passwords, tokens, hashes
_auth_opts = [
    cfg.StrOpt('undercloud_db_password',
               help=('Password used for MySQL databases. '
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
    cfg.StrOpt('undercloud_ceilometer_password',
               help=('Ceilometer service password. '
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
]
CONF.register_opts(_opts)
CONF.register_opts(_auth_opts, group='auth')


def list_opts():
    return [(None, copy.deepcopy(_opts)),
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
    LOG.addHandler(logging.StreamHandler())


def _load_config():
    conf_params = []
    if os.path.isfile(PATHS.PASSWORD_PATH):
        conf_params += ['--config-file', PATHS.PASSWORD_PATH]
    if os.path.isfile(PATHS.CONF_PATH):
        conf_params += ['--config-file', PATHS.CONF_PATH]
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
            echo_cmd = ('echo 127.0.0.1 %s %s >> /etc/hosts' %
                        (detected_static_hostname, short_hostname))
            args = ['sudo', '/bin/bash', '-c', echo_cmd]
            _run_command(args, name='hostname-to-etc-hosts')
            LOG.info('Added hostname %s to /etc/hosts',
                     detected_static_hostname)


def _check_memory():
    """Check system memory

    The undercloud will not run properly in less than 4 GB of memory.
    This function verifies that at least that much is available before
    proceeding with install.
    """
    mem = psutil.virtual_memory()
    total_mb = mem.total / 1024 / 1024
    if total_mb < REQUIRED_MB:
        LOG.error('At least 4 GB of memory is required for undercloud '
                  'installation.  A minimum of 6 GB is recommended. '
                  'Only detected %d MB' % total_mb)
        raise RuntimeError('Insufficient memory available')


def _check_sysctl():
    """Check sysctl option availability

    The undercloud will not install properly if some of the expected sysctl
    values are not available to be set.
    """
    options = ['net.ipv4.ip_forward', 'net.ipv4.ip_nonlocal_bind',
               'net.ipv6.ip_nonlocal_bind']

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


def _validate_network():
    def error_handler(message):
        LOG.error('Undercloud configuration validation failed: %s', message)
        raise validator.FailedValidation(message)

    _validate_cidr()
    params = {opt.name: CONF[opt.name] for opt in _opts}
    validator.validate_config(params, error_handler)


def _validate_cidr():
    """Check for default network_cidr

    The old default cidr of 192.0.2.0/24 is deprecated due to being unroutable
    under RFC 5737.  However, since we need to give users notice of the
    change, we need some logic to warn them of the problem before actually
    changing the default, which could be a breaking change on upgrades.

    This function handles the sentinel value of None, which indicates that
    the user has not overridden the default value, and sets an override on the
    conf opt to match the previous default.  It also sets a global flag so we
    can warn about the deprecation at the end of the deploy.
    """
    if CONF.network_cidr is None:
        global deprecated_cidr
        deprecated_cidr = True
        CONF.set_override('network_cidr', '192.0.2.0/24')


def _validate_configuration():
    try:
        _check_hostname()
        _check_memory()
        _check_sysctl()
        _validate_network()
    except RuntimeError as e:
        LOG.error('ERROR: An error occured during configuration validation, '
                  'please check your host configuration and try again. '
                  '{error}'.format(error=e))
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
        format_str % (public_proto, public['host'], public[public_port_key]))
    endpoints['UNDERCLOUD_ENDPOINT_%s_INTERNAL' % upper_name] = (
        format_str % (internal_proto, internal['host'], internal['port']))
    endpoints['UNDERCLOUD_ENDPOINT_%s_ADMIN' % upper_name] = (
        format_str % (internal_proto, admin['host'], admin['port']))
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
        public_host = CONF.undercloud_public_vip
        public_proto = 'https'
        zaqar_ws_public_proto = 'wss'

    endpoints = {}

    endpoint_list = [
        ('heat',
            '%s://%s:%d/v1/%%(tenant_id)s',
            {'host': public_host, 'port': 8004, 'ssl_port': 13004},
            {'host': internal_host, 'port': 8004}),
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
        ('ceilometer',
            '%s://%s:%d',
            {'host': public_host, 'port': 8777, 'ssl_port': 13777},
            {'host': internal_host, 'port': 8777}),
        ('keystone',
            '%s://%s:%d',
            {'host': public_host, 'port': 5000, 'ssl_port': 13000},
            {'host': internal_host, 'port': 5000},
            {'host': internal_host, 'port': 35357}),
        ('swift',
            '%s://%s:%d/v1/AUTH_%%(tenant_id)s',
            {'host': public_host, 'port': 8080, 'ssl_port': 13808},
            {'host': internal_host, 'port': 8080}),
        ('ironic',
            '%s://%s:%d',
            {'host': public_host, 'port': 6385, 'ssl_port': 13385},
            {'host': internal_host, 'port': 6385}),
        ('ironic_inspector',
            '%s://%s:%d',
            {'host': public_host, 'port': 5050, 'ssl_port': 13050},
            {'host': internal_host, 'port': 5050}),
        ('aodh',
            '%s://%s:%d',
            {'host': public_host, 'port': 8042, 'ssl_port': 13042},
            {'host': internal_host, 'port': 8042}),
        ('mistral',
            '%s://%s:%d/v2',
            {'host': public_host, 'port': 8989, 'ssl_port': 13989},
            {'host': internal_host, 'port': 8989}),
        ('zaqar',
            '%s://%s:%d',
            {'host': public_host, 'port': 8888, 'ssl_port': 13888},
            {'host': internal_host, 'port': 8888}),
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


def _member_role_exists(instack_env):
    # This is a workaround for puppet removing the deprecated _member_
    # role on upgrade - if it exists we must not remove role assignments
    # or trusts stored in the undercloud heat will break
    if not _stackrc_exists():
        instack_env['MEMBER_ROLE_EXISTS'] = 'False'
        return
    user, password, tenant, auth_url = _get_auth_values()
    role_exists = False
    try:
        # Note this is made somewhat verbose due to trying to handle
        # any format auth_url (versionless, v2,0/v3 suffix)
        auth_plugin_class = auth.get_plugin_class('password')
        auth_kwargs = {
            'auth_url': auth_url,
            'username': user,
            'password': password,
            'project_name': tenant}
        if 'v2.0' not in auth_url:
            auth_kwargs.update({
                'project_domain_name': 'default',
                'user_domain_name': 'default'})
        auth_plugin = auth_plugin_class(**auth_kwargs)
        sess = session.Session(auth=auth_plugin)
        disc = discover.Discover(session=sess)
        c = disc.create_client()
        role_names = [r.name for r in c.roles.list()]
        role_exists = '_member_' in role_names
    except ks_exceptions.ConnectionError:
        # This will happen on initial deployment, assume False
        # as no new deployments should have _member_
        role_exists = False
    instack_env['MEMBER_ROLE_EXISTS'] = six.text_type(role_exists)


def _generate_environment(instack_root):
    """Generate an environment dict for instack

    The returned dict will have the necessary values for use as the env
    parameter when calling instack via the subprocess module.

    :param instack_root: The path containing the instack-undercloud elements
        and json files.
    """
    instack_env = dict(os.environ)
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

    # Convert conf opts to env values
    for opt in _opts:
        env_name = opt.name.upper()
        instack_env[env_name] = six.text_type(CONF[opt.name])
    # Opts that needs extra processing
    if CONF.inspection_runbench and not CONF.inspection_extras:
        raise RuntimeError('inspection_extras must be enabled for '
                           'inspection_runbench to work')
    if CONF.inspection_extras:
        instack_env['INSPECTION_COLLECTORS'] = 'default,extra-hardware,logs'
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

    instack_env['PUBLIC_INTERFACE_IP'] = instack_env['LOCAL_IP']
    instack_env['LOCAL_IP'] = instack_env['LOCAL_IP'].split('/')[0]
    if instack_env['UNDERCLOUD_SERVICE_CERTIFICATE']:
        instack_env['UNDERCLOUD_SERVICE_CERTIFICATE'] = os.path.abspath(
            instack_env['UNDERCLOUD_SERVICE_CERTIFICATE'])
    # We're not in a chroot so this doesn't make sense, and it causes weird
    # errors if it's set.
    if instack_env.get('DIB_YUM_REPO_CONF'):
        del instack_env['DIB_YUM_REPO_CONF']

    instack_env['TRIPLEO_INSTALL_USER'] = getpass.getuser()
    instack_env['TRIPLEO_UNDERCLOUD_CONF_FILE'] = PATHS.CONF_PATH
    instack_env['TRIPLEO_UNDERCLOUD_PASSWORD_FILE'] = PATHS.PASSWORD_PATH

    _generate_endpoints(instack_env)

    _write_password_file(instack_env)

    if CONF.generate_service_certificate:
        public_vip = CONF.undercloud_public_vip
        instack_env['UNDERCLOUD_SERVICE_CERTIFICATE'] = (
            '/etc/pki/tls/certs/undercloud-%s.pem' % public_vip)

    _member_role_exists(instack_env)

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
        hiera_entry = os.path.splitext(
            os.path.basename(CONF.hieradata_override))[0]
        dst = os.path.join('/etc/puppet/hieradata',
                           os.path.basename(CONF.hieradata_override))
        _run_command(['sudo', 'mkdir', '-p', '/etc/puppet/hieradata'])
        _run_command(['sudo', 'cp', CONF.hieradata_override, dst])
        _run_command(['sudo', 'chmod', '0644', dst])
    else:
        hiera_entry = ''

    if CONF.net_config_override:
        net_config_json = open(CONF.net_config_override).read()
    else:
        net_config_json = \
            open(_get_template_path('net-config.json.template')).read()

    context['HIERADATA_OVERRIDE'] = hiera_entry

    partials = {'net_config': net_config_json}
    renderer = pystache.Renderer(partials=partials)
    template = _get_template_path('config.json.template')

    with open(template) as f:
        config_json = renderer.render(f.read(), context)

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


def _run_yum_update(instack_env):
    args = ['sudo', 'yum', 'update', '-y']
    LOG.info('Running yum update')
    _run_live_command(args, instack_env, 'yum-update')
    LOG.info('yum-update completed successfully')


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

    Returns the user, password, tenant and auth_url as read from stackrc,
    in that order as a tuple.
    """
    user = _extract_from_stackrc('OS_USERNAME')
    password = _run_command(['sudo', 'hiera', 'admin_password']).rstrip()
    tenant = _extract_from_stackrc('OS_TENANT_NAME')
    auth_url = _extract_from_stackrc('OS_AUTH_URL')
    return user, password, tenant, auth_url


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


def _delete_default_flavors(nova):
    """Delete the default flavors from Nova

    The m1.tiny, m1.small, etc. flavors are not useful on an undercloud.
    """
    to_delete = ['m1.tiny', 'm1.small', 'm1.medium', 'm1.large', 'm1.xlarge']
    for f in nova.flavors.list():
        if f.name in to_delete:
            nova.flavors.delete(f.id)


def _ensure_flavor(nova, name, profile=None):
    try:
        flavor = nova.flavors.create(name, 4096, 1, 40)
    except exceptions.Conflict:
        LOG.info('Not creating flavor "%s" because it already exists.', name)
        return
    keys = {'capabilities:boot_option': 'local'}
    if profile is not None:
        keys['capabilities:profile'] = profile
    flavor.set_keys(keys)
    message = 'Created flavor "%s" with profile "%s"'
    LOG.info(message, name, profile)


def _stackrc_exists():
    user_stackrc = os.path.expanduser('~/stackrc')
    # We gotta check if the copying of stackrc has already been done.
    if os.path.isfile('/root/stackrc') and os.path.isfile(user_stackrc):
        return True
    return False


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


def _create_mistral_config_environment(instack_env, mistral):
    # Store the snmpd password in a Mistral environment so it can be accessed
    # by the Mistral actions.
    snmpd_password = instack_env["UNDERCLOUD_CEILOMETER_SNMPD_PASSWORD"]

    env_name = "tripleo.undercloud-config"
    try:
        mistral.environments.get(env_name)
    except mistralclient_base.APIException:
        mistral.environments.create(
            name=env_name,
            variables=json.dumps({
                "undercloud_ceilometer_snmpd_password": snmpd_password
            }))


def _create_default_plan(mistral, timeout=180):
    plan_name = 'overcloud'
    queue_name = str(uuid.uuid4())

    if plan_name in [env.name for env in mistral.environments.list()]:
        LOG.info('Not creating default plan "%s" because it already exists.',
                 plan_name)
        return

    execution = mistral.executions.create(
        'tripleo.plan_management.v1.create_default_deployment_plan',
        workflow_input={'container': plan_name, 'queue_name': queue_name}
    )

    timeout_at = time.time() + timeout

    while time.time() < timeout_at:
        exe = mistral.executions.get(execution.id)
        if exe.state == "RUNNING":
            time.sleep(5)
            continue
        if exe.state == "SUCCESS":
            return
        else:
            raise RuntimeError(
                "Failed to create the default Deployment Plan. Please check "
                "the create_default_deployment_plan execution in Mistral with "
                "`openstack workflow execution list`.")
    else:
        exe = mistral.executions.get(execution.id)
        LOG.error("Timed out waiting for execution %s to finish. State: %s",
                  exe.id, exe.state)
        raise RuntimeError(
            "Timed out creating the default Deployment Plan. Please check "
            "the create_default_deployment_plan execution in Mistral with "
            "`openstack workflow execution list`.")


def _prepare_ssh_environment(mistral):
    mistral.executions.create('tripleo.validations.v1.copy_ssh_key')


def _post_config_mistral(instack_env, mistral):

    _create_mistral_config_environment(instack_env, mistral)
    _create_default_plan(mistral)

    if CONF.enable_validations:
        _prepare_ssh_environment(mistral)


def _post_config(instack_env):
    _copy_stackrc()
    user, password, tenant, auth_url = _get_auth_values()
    nova = novaclient.Client(2, user, password, tenant, auth_url)

    _configure_ssh_keys(nova)
    _delete_default_flavors(nova)

    _ensure_flavor(nova, 'baremetal')
    _ensure_flavor(nova, 'control', 'control')
    _ensure_flavor(nova, 'compute', 'compute')
    _ensure_flavor(nova, 'ceph-storage', 'ceph-storage')
    _ensure_flavor(nova, 'block-storage', 'block-storage')
    _ensure_flavor(nova, 'swift-storage', 'swift-storage')

    if CONF.enable_mistral:
        mistral_url = instack_env['UNDERCLOUD_ENDPOINT_MISTRAL_PUBLIC']
        mistral = mistralclient.client(
            mistral_url=mistral_url,
            username=user,
            api_key=password,
            project_name=tenant,
            auth_url=auth_url)
        _post_config_mistral(instack_env, mistral)


def install(instack_root):
    """Install the undercloud

    :param instack_root: The path containing the instack-undercloud elements
        and json files.
    """
    _configure_logging(DEFAULT_LOG_LEVEL, PATHS.LOG_FILE)
    LOG.info('Logging to %s', PATHS.LOG_FILE)
    _load_config()
    _clean_os_refresh_config()
    _validate_configuration()
    instack_env = _generate_environment(instack_root)
    _generate_init_data(instack_env)
    _run_yum_update(instack_env)
    _run_instack(instack_env)
    _run_orc(instack_env)
    _post_config(instack_env)
    _run_command(['sudo', 'rm', '-f', '/tmp/svc-map-services'], None, 'rm')
    LOG.info(COMPLETION_MESSAGE, {'password_path': PATHS.PASSWORD_PATH,
             'stackrc_path': os.path.expanduser('~/stackrc')})
    if deprecated_cidr:
        LOG.warning(CIDR_DEPRECATION_MESSAGE)

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

import copy
import errno
import getpass
import glob
import hashlib
import logging
import os
import platform
import socket
import subprocess
import tempfile
import uuid

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
# We need 4 GB, leave a little room for variation in what 4 GB means on
# different platforms.
REQUIRED_MB = 3750


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
                     'Undercloud services.  Only used if '
                     'undercloud_service_certficate is set.')
               ),
    cfg.StrOpt('undercloud_admin_vip',
               default='192.0.2.3',
               help=('Virtual IP address to use for the admin endpoints of '
                     'Undercloud services.  Only used if '
                     'undercloud_service_certficate is set.')
               ),
    cfg.StrOpt('undercloud_service_certificate',
               default='',
               help=('Certificate file to use for OpenStack service SSL '
                     'connections.  Setting this enables SSL for the '
                     'OpenStack API endpoints, leaving it unset disables SSL.')
               ),
    cfg.BoolOpt('generate_service_certificate',
                default=False,
                help=('When set to True, a self-signed SSL certificate will '
                      'be generated as part of the undercloud install and '
                      'this certificate will be used in place of the value '
                      'for undercloud_service_certificate.  The resulting '
                      'certificate will be written to '
                      '~/undercloud-[undercloud_public_vip].pem.  Note that '
                      'this certificate will also be added to the system\'s '
                      'trusted certificate store.')
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
               default='192.0.2.0/24',
               help=('Network CIDR for the Neutron-managed network for '
                     'Overcloud instances. This should be the subnet used '
                     'for PXE booting.')
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
                default=False,
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
                default=False,
                help=('Whether to install Telemetry services '
                      '(ceilometer, aodh) in the Undercloud.')
                ),
    cfg.BoolOpt('ipxe_deploy',
                default=True,
                help=('Whether to use iPXE for deploy by default.')
                ),
    cfg.BoolOpt('enable_monitoring',
                default=False,
                help=('Whether to install Monitoring services in the '
                      'Undercloud.')
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
    cfg.StrOpt('undercloud_sensu_password',
               help=('Sensu service password. '
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


def _validate_network():
    def error_handler(message):
        LOG.error('Undercloud configuration validation failed: %s', message)
        raise validator.FailedValidation(message)

    params = {opt.name: CONF[opt.name] for opt in _opts}
    validator.validate_config(params, error_handler)


def _validate_configuration():
    _check_hostname()
    _check_memory()
    _validate_network()


def _generate_password(length=40):
    """Create a random password

    Copied from rdomanager-oscplugin.  This should eventually live in
    tripleo-common.
    """
    uuid_str = six.text_type(uuid.uuid4()).encode("UTF-8")
    return hashlib.sha1(uuid_str).hexdigest()[:length]


def _generate_endpoints(instack_env):
    local_host = instack_env['LOCAL_IP']
    public_host = local_host
    proto = 'http'
    heat_public_port = 8004
    neutron_public_port = 9696
    glance_public_port = 9292
    nova_public_port = 8774
    ceilo_public_port = 8777
    keystone_public_port = 5000
    swift_public_port = 8080
    ironic_public_port = 6385
    aodh_public_port = 8042

    if CONF.undercloud_service_certificate:
        public_host = CONF.undercloud_public_vip
        proto = 'https'
        heat_public_port = 13004
        neutron_public_port = 13696
        glance_public_port = 13292
        nova_public_port = 13774
        ceilo_public_port = 13777
        keystone_public_port = 13000
        swift_public_port = 13808
        ironic_public_port = 13385
        aodh_public_port = 13042

    heat_public_params = (proto, public_host, heat_public_port)
    heat_internal_params = ('http', local_host, 8004)
    heat_admin_params = heat_internal_params
    neutron_public_params = (proto, public_host, neutron_public_port)
    neutron_internal_params = ('http', local_host, 9696)
    neutron_admin_params = neutron_internal_params
    glance_public_params = (proto, public_host, glance_public_port)
    glance_internal_params = ('http', local_host, 9292)
    glance_admin_params = glance_internal_params
    nova_public_params = (proto, public_host, nova_public_port)
    nova_internal_params = ('http', local_host, 8774)
    nova_admin_params = nova_internal_params
    ceilo_public_params = (proto, public_host, ceilo_public_port)
    ceilo_internal_params = ('http', local_host, 8777)
    ceilo_admin_params = ceilo_internal_params
    keystone_public_params = (proto, public_host, keystone_public_port)
    keystone_internal_params = ('http', local_host, 5000)
    keystone_admin_params = ('http', local_host, 35357)
    swift_public_params = (proto, public_host, swift_public_port)
    swift_internal_params = ('http', local_host, 8080)
    swift_admin_params = swift_internal_params
    ironic_public_params = (proto, public_host, ironic_public_port)
    ironic_internal_params = ('http', local_host, 6385)
    ironic_admin_params = ironic_internal_params
    aodh_public_params = (proto, public_host, aodh_public_port)
    aodh_internal_params = ('http', local_host, 8042)
    aodh_admin_params = aodh_internal_params

    endpoints = {}

    def add_endpoint(name, format_str, public, internal, admin):
        upper_name = name.upper()
        endpoints['UNDERCLOUD_ENDPOINT_%s_PUBLIC' % upper_name] = (format_str %
                                                                   public)
        endpoints['UNDERCLOUD_ENDPOINT_%s_INTERNAL' % upper_name] = (
            format_str % internal)
        endpoints['UNDERCLOUD_ENDPOINT_%s_ADMIN' % upper_name] = (format_str %
                                                                  admin)

    add_endpoint('heat',
                 '%s://%s:%d/v1/%%(tenant_id)s',
                 heat_public_params,
                 heat_internal_params,
                 heat_admin_params,
                 )
    add_endpoint('neutron',
                 '%s://%s:%d',
                 neutron_public_params,
                 neutron_internal_params,
                 neutron_admin_params,
                 )
    add_endpoint('glance',
                 '%s://%s:%d',
                 glance_public_params,
                 glance_internal_params,
                 glance_admin_params,
                 )
    add_endpoint('nova',
                 '%s://%s:%d/v2.1',
                 nova_public_params,
                 nova_internal_params,
                 nova_admin_params,
                 )
    add_endpoint('ceilometer',
                 '%s://%s:%d',
                 ceilo_public_params,
                 ceilo_internal_params,
                 ceilo_admin_params,
                 )
    add_endpoint('keystone',
                 '%s://%s:%d',
                 keystone_public_params,
                 keystone_internal_params,
                 keystone_admin_params,
                 )
    add_endpoint('swift',
                 '%s://%s:%d/v1/AUTH_%%(tenant_id)s',
                 swift_public_params,
                 swift_internal_params,
                 swift_admin_params,
                 )
    # The swift admin endpoint has a different format from the others
    endpoints['UNDERCLOUD_ENDPOINT_SWIFT_ADMIN'] = ('%s://%s:%s' %
                                                    swift_admin_params)
    add_endpoint('ironic',
                 '%s://%s:%d',
                 ironic_public_params,
                 ironic_internal_params,
                 ironic_admin_params,
                 )
    add_endpoint('aodh',
                 '%s://%s:%d',
                 aodh_public_params,
                 aodh_internal_params,
                 aodh_admin_params,
                 )

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


SSL_CONFIG_TEMPLATE = '''[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_req
prompt = no

[req_distinguished_name]
C = xx
ST = xx
L = xxxx
O = xxxx
CN = %(public_vip)s

[v3_req]
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid,issuer
basicConstraints = CA:TRUE
subjectAltName = @alt_names

[alt_names]
IP = %(public_vip)s
'''


def _generate_certificate(instack_env):
    public_vip = CONF.undercloud_public_vip
    home_pem = os.path.expanduser('~/undercloud-%s.pem' % public_vip)
    if os.path.exists(home_pem):
        LOG.info('%s already exists. Not generating a new '
                 'certificate', home_pem)
        return
    ssl_config = SSL_CONFIG_TEMPLATE % {'public_vip': public_vip}
    ssl_config_file = tempfile.mkstemp()[1]
    try:
        with open(ssl_config_file, 'w') as f:
            f.write(ssl_config)
        privkey = tempfile.mkstemp()[1]
        cacert = tempfile.mkstemp()[1]
        undercloud_pem = ('/etc/pki/instack-certs/undercloud-%s.pem' %
                          public_vip)
        args = ['openssl', 'genrsa', '-out', privkey, '2048']
        _run_command(args, name='openssl private key')
        args = ['openssl', 'req', '-new', '-x509', '-key', privkey, '-out',
                cacert, '-days', '3650', '-config', ssl_config_file]
        _run_command(args, name='openssl cacert')
        with open(home_pem, 'w') as u:
            with open(cacert) as c:
                u.write(c.read())
            with open(privkey) as p:
                u.write(p.read())
        args = ['sudo', 'mkdir', '-p', '/etc/pki/instack-certs']
        _run_command(args, name='mkdir instack-certs')
        args = ['sudo', 'cp', '-f', home_pem, undercloud_pem]
        _run_command(args, name='cp undercloud.pem')
        args = ['sudo', 'semanage', 'fcontext', '-a', '-t', 'etc_t',
                '"/etc/pki/instack-certs(/.*)?"']
        _run_command(args, name='semanage')
        args = ['sudo', 'restorecon', '-R', '/etc/pki/instack-certs']
        _run_command(args, name='restorecon')
        instack_env['UNDERCLOUD_SERVICE_CERTIFICATE'] = undercloud_pem
        LOG.info('Generated new service certificate in %s', undercloud_pem)
        cacert_path = ('/etc/pki/ca-trust/source/anchors/cacert-%s.pem' %
                       public_vip)
        args = ['sudo', 'cp', '-f', cacert, cacert_path]
        _run_command(args, name='copy cacert')
        args = ['sudo', 'update-ca-trust', 'extract']
        _run_command(args, name='update-ca-trust')
        LOG.info('Added %s to system certificate store', cacert_path)
    finally:
        os.remove(ssl_config_file)
        if os.path.exists(privkey):
            os.remove(privkey)
        if os.path.exists(cacert):
            os.remove(cacert)


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

    _generate_endpoints(instack_env)

    _write_password_file(instack_env)

    if CONF.generate_service_certificate:
        _generate_certificate(instack_env)

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
        print >>f, config_json

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
    tenant = _extract_from_stackrc('OS_TENANT')
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


def _copy_stackrc():
    args = ['sudo', 'cp', '/root/stackrc', os.path.expanduser('~')]
    _run_command(args, name='Copy stackrc')
    args = ['sudo', 'chown', getpass.getuser() + ':',
            os.path.expanduser('~/stackrc')]
    _run_command(args, name='Chown stackrc')


def _clean_os_refresh_config():
    orc_dirs = glob.glob('/usr/libexec/os-refresh-config/*')
    args = ['sudo', 'rm', '-rf'] + orc_dirs
    _run_command(args, name='Clean os-refresh-config')


def _post_config():
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
    _run_instack(instack_env)
    _run_orc(instack_env)
    _post_config()
    _run_command(['sudo', 'rm', '-f', '/tmp/svc-map-services'], None, 'rm')
    LOG.info(COMPLETION_MESSAGE, {'password_path': PATHS.PASSWORD_PATH,
             'stackrc_path': os.path.expanduser('~/stackrc')})

# Copyright 2015 Red Hat, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

if count(hiera('ntp::servers')) > 0 {
  include ::ntp
}

# TODO Galara
class { 'mysql::server':
    override_options => {
      'mysqld' => {
        'bind-address' => hiera('controller_host'),
        'max_connections' => hiera('mysql_max_connections'),
        'open_files_limit' => '-1',
      }
  }
}

# FIXME: this should only occur on the bootstrap host (ditto for db syncs)
# Create all the database schemas
# Example DSN format: mysql://user:password@host/dbname
$allowed_hosts = ['%',hiera('controller_host')]
$keystone_dsn = split(hiera('keystone::database_connection'), '[@:/?]')
class { 'keystone::db::mysql':
  user          => $keystone_dsn[3],
  password      => $keystone_dsn[4],
  host          => $keystone_dsn[5],
  dbname        => $keystone_dsn[6],
  allowed_hosts => $allowed_hosts,
}
$glance_dsn = split(hiera('glance::api::database_connection'), '[@:/?]')
class { 'glance::db::mysql':
  user          => $glance_dsn[3],
  password      => $glance_dsn[4],
  host          => $glance_dsn[5],
  dbname        => $glance_dsn[6],
  allowed_hosts => $allowed_hosts,
}
$nova_dsn = split(hiera('nova::database_connection'), '[@:/?]')
class { 'nova::db::mysql':
  user          => $nova_dsn[3],
  password      => $nova_dsn[4],
  host          => $nova_dsn[5],
  dbname        => $nova_dsn[6],
  allowed_hosts => $allowed_hosts,
}
$neutron_dsn = split(hiera('neutron::server::database_connection'), '[@:/?]')
class { 'neutron::db::mysql':
  user          => $neutron_dsn[3],
  password      => $neutron_dsn[4],
  host          => $neutron_dsn[5],
  dbname        => $neutron_dsn[6],
  allowed_hosts => $allowed_hosts,
}
$heat_dsn = split(hiera('heat_dsn'), '[@:/?]')
class { 'heat::db::mysql':
  user          => $heat_dsn[3],
  password      => $heat_dsn[4],
  host          => $heat_dsn[5],
  dbname        => $heat_dsn[6],
  allowed_hosts => $allowed_hosts,
}
$ceilometer_dsn = split(hiera('ceilometer::db::database_connection'), '[@:/?]')
class { 'ceilometer::db::mysql':
  user          => $ceilometer_dsn[3],
  password      => $ceilometer_dsn[4],
  host          => $ceilometer_dsn[5],
  dbname        => $ceilometer_dsn[6],
  allowed_hosts => $allowed_hosts,
}
$ironic_dsn = split(hiera('ironic::database_connection'), '[@:/?]')
class { 'ironic::db::mysql':
user          => $ironic_dsn[3],
password      => $ironic_dsn[4],
host          => $ironic_dsn[5],
dbname        => $ironic_dsn[6],
allowed_hosts => $allowed_hosts,
}

if $::osfamily == 'RedHat' {
  $rabbit_provider = 'yum'
} else {
  $rabbit_provider = undef
}

# TODO Rabbit HA
class { 'rabbitmq':
  package_provider  => $rabbit_provider,
  config_cluster    => false,
  node_ip_address   => hiera('controller_host'),
}

rabbitmq_vhost { '/':
  provider => 'rabbitmqctl',
}
rabbitmq_user {[
  hiera(rabbit_username)
]:
  admin    => true,
  password => hiera('rabbit_password'),
  provider => 'rabbitmqctl',
}

rabbitmq_user_permissions {[
  join([hiera(rabbit_username), '@/'])
]:
  configure_permission => '.*',
  write_permission     => '.*',
  read_permission      => '.*',
  provider             => 'rabbitmqctl',
}

# pre-install swift here so we can build rings
include ::swift

class { 'keystone':
  debug => hiera('debug'),
}

#TODO: need a cleanup-keystone-tokens.sh solution here
keystone_config {
  'ec2/driver': value => 'keystone.contrib.ec2.backends.sql.Ec2';
}
file { [ '/etc/keystone/ssl', '/etc/keystone/ssl/certs', '/etc/keystone/ssl/private' ]:
  ensure  => 'directory',
  owner   => 'keystone',
  group   => 'keystone',
  require => Package['keystone'],
}
file { '/etc/keystone/ssl/certs/signing_cert.pem':
  content => hiera('keystone_signing_certificate'),
  owner   => 'keystone',
  group   => 'keystone',
  notify  => Service['keystone'],
  require => File['/etc/keystone/ssl/certs'],
}
file { '/etc/keystone/ssl/private/signing_key.pem':
  content => hiera('keystone_signing_key'),
  owner   => 'keystone',
  group   => 'keystone',
  notify  => Service['keystone'],
  require => File['/etc/keystone/ssl/private'],
}
file { '/etc/keystone/ssl/certs/ca.pem':
  content => hiera('keystone_ca_certificate'),
  owner   => 'keystone',
  group   => 'keystone',
  notify  => Service['keystone'],
  require => File['/etc/keystone/ssl/certs'],
}

# TODO: notifications, scrubber, etc.
class { '::glance::api':
  debug => hiera('debug'),
}
class { '::glance::registry':
  debug => hiera('debug'),
}
include ::glance::backend::file

class { 'nova':
  rabbit_hosts           => [hiera('controller_host')],
  glance_api_servers     => join([hiera('glance_protocol'), '://', hiera('controller_host'), ':', hiera('glance_port')]),
  debug                  => hiera('debug'),
}

include ::nova::api
include ::nova::cert
include ::nova::compute
include ::nova::conductor
include ::nova::consoleauth
include ::nova::vncproxy
include ::nova::scheduler
include ::nova::scheduler::filter

class {'neutron':
  rabbit_hosts => [hiera('controller_host')],
  debug        => hiera('debug'),
}

include ::neutron::server
include ::neutron::quota

# NOTE(lucasagomes): This bit might be superseded by
# https://review.openstack.org/#/c/172040/
file { "dnsmasq-ironic.conf":
  path    => "/etc/dnsmasq-ironic.conf",
  ensure  => present,
  owner   => "ironic",
  group   => "ironic",
  mode    => 0644,
  replace => false,
  content => "dhcp-match=ipxe,175";
}

class { 'neutron::agents::dhcp':
  dnsmasq_config_file => '/etc/dnsmasq-ironic.conf';
}

class { 'neutron::plugins::ml2':
  flat_networks        => split(hiera('neutron_flat_networks'), ','),
}

class { 'neutron::agents::ml2::ovs':
  bridge_mappings  => split(hiera('neutron_bridge_mappings'), ','),
}

# swift proxy
include ::memcached
include ::swift::proxy
include ::swift::ringbuilder
include ::swift::proxy::proxy_logging
include ::swift::proxy::healthcheck
include ::swift::proxy::cache
include ::swift::proxy::keystone
include ::swift::proxy::authtoken
include ::swift::proxy::staticweb
include ::swift::proxy::ceilometer
include ::swift::proxy::ratelimit
include ::swift::proxy::catch_errors
include ::swift::proxy::tempauth
include ::swift::proxy::tempurl
include ::swift::proxy::formpost

# swift storage
class {'swift::storage::all':
  mount_check => str2bool(hiera('swift_mount_check'))
}
if(!defined(File['/srv/node'])) {
  file { '/srv/node':
    ensure  => directory,
    owner   => 'swift',
    group   => 'swift',
    require => Package['openstack-swift'],
  }
}
$swift_components = ['account', 'container', 'object']
swift::storage::filter::recon { $swift_components : }
swift::storage::filter::healthcheck { $swift_components : }

$controller_host = hiera('controller_host')
ring_object_device { "${controller_host}:6000/1":
  zone   => 1,
  weight => 1,
}
ring_container_device { "${controller_host}:6001/1":
  zone   => 1,
  weight => 1,
}
ring_account_device { "${controller_host}:6002/1":
  zone   => 1,
  weight => 1,
}

# Ceilometer
include ::ceilometer
include ::ceilometer::api
include ::ceilometer::db
include ::ceilometer::agent::notification
include ::ceilometer::agent::central
include ::ceilometer::alarm::notifier
include ::ceilometer::alarm::evaluator
include ::ceilometer::expirer
include ::ceilometer::collector
class { 'ceilometer::agent::auth':
  auth_url => join(['http://', hiera('controller_host'), ':5000/v2.0']),
}

Cron <| title == 'ceilometer-expirer' |> { command => "sleep $((\$(od -A n -t d -N 3 /dev/urandom) % 86400)) && ${::ceilometer::params::expirer_command}" }

# Heat
class {'heat':
  debug => hiera('debug'),
}
include ::heat::api
include ::heat::api_cfn
include ::heat::api_cloudwatch
include ::heat::engine
include ::heat::keystone::domain

# We're creating the admin role and heat domain user in puppet and need
# to make sure they are done in order.
include ::keystone::roles::admin
Service['keystone'] -> Class['::keystone::roles::admin'] -> Keystone_domain['heat_domain']

$snmpd_user = hiera('snmpd_readonly_user_name')
snmp::snmpv3_user { $snmpd_user:
  authtype => 'MD5',
  authpass => hiera('snmpd_readonly_user_password'),
}
class { 'snmp':
  agentaddress => ['udp:161','udp6:[::1]:161'],
  snmpd_config => [ join(['rouser ', hiera('snmpd_readonly_user_name')]), 'proc  cron', 'includeAllDisks  10%', 'master agentx', 'trapsink localhost public', 'iquerySecName internalUser', 'rouser internalUser', 'defaultMonitors yes', 'linkUpDownNotifications yes' ],
}

nova_config {
  'DEFAULT/my_ip':                     value => $ipaddress;
  'DEFAULT/linuxnet_interface_driver': value => 'nova.network.linux_net.LinuxOVSInterfaceDriver';
  'DEFAULT/rpc_response_timeout':      value => '600';
}


class { 'nova::compute::ironic':
  admin_user        => 'ironic',
  admin_passwd    => hiera('ironic::api::admin_password'),
  admin_tenant_name => hiera('ironic::api::admin_tenant_name'),
  api_endpoint      => join(['http://', hiera('controller_host'), ':6385/v1']),
}

class { 'nova::network::neutron':
  neutron_admin_auth_url    => join(['http://', hiera('controller_host'), ':35357/v2.0']),
  neutron_url               => join(['http://', hiera('controller_host'), ':9696']),
  neutron_admin_password    => hiera('neutron::server::auth_password'),
  neutron_admin_tenant_name => hiera('neutron::server::auth_tenant'),
  neutron_region_name       => '',
}

class { 'ironic::conductor':
  force_power_state_during_sync => hiera('ironic::conductor::force_power_state_during_sync'),
}

# dependency of pxe_drac
package{'openwsman-python': }
# dependency of pxe_ilo
package{'python-proliantutils': }

class { 'ironic':
  enabled_drivers => ['pxe_ipmitool', 'pxe_ssh', 'pxe_drac', 'pxe_ilo', 'pxe_wol'],
  debug           => hiera('debug'),
}

class { 'ironic::api':
  host_ip => hiera('controller_host'),
}

class { 'ironic::drivers::ipmi':
  retry_timeout => 15
}

ironic_config {
  'DEFAULT/my_ip':                           value => hiera('controller_host');
  'DEFAULT/rpc_response_timeout':            value => '600';
  'glance/host':                             value => hiera('glance::api::bind_host');
  'discoverd/enabled':                       value => 'true';
  'pxe/pxe_config_template':                 value => '$pybasedir/drivers/modules/ipxe_config.template';
  'pxe/pxe_bootfile_name':                   value => 'undionly.kpxe';
  'pxe/http_url':                            value => 'http://$my_ip:8088';
  'pxe/http_root':                           value => '/httpboot';
  'pxe/ipxe_enabled':                        value => 'True';
}

if str2bool(hiera('enable_tuskar', 'true')) {
  class { 'horizon':
    secret_key   => hiera('horizon_secret_key'),
    keystone_url => join(['http://', hiera('controller_host'), ':5000/v2.0']),
    allowed_hosts => [hiera('controller_host'), $::fqdn, 'localhost'],
    server_aliases => [hiera('controller_host'), $::fqdn, 'localhost'],
    tuskar_ui => true,
    tuskar_ui_ironic_discoverd_url => join(['http://', hiera('controller_host'), ':5050']),
    tuskar_ui_undercloud_admin_password => hiera('admin_password')
  }

  # Install python-tuskarclient so we can deploy a stack with tuskar
  package{'python-tuskarclient': }

  class { 'tuskar::ui':
    extras => true
  }
}

if str2bool(hiera('enable_tempest', 'true')) {
  # tempest
  # TODO: when puppet-tempest supports install by package, do that instead
  package{'openstack-tempest': }
  # needed for /bin/subunit-2to1 (called by run_tempest.sh)
  package{'subunit-filters': }
}

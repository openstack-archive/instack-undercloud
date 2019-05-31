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

# Deploy os-net-config before everything in the catalog
include ::stdlib
class { '::tripleo::network::os_net_config':
  stage => 'setup',
}

# enable ip forwarding for the overcloud nodes to access the outside internet
# in cases where they are on an isolated network
ensure_resource('sysctl::value', 'net.ipv4.ip_forward', { 'value' => 1 })
# NOTE(aschultz): clear up old file as this used to be managed via DIB
file { '/etc/sysctl.d/ip-forward.conf':
  ensure => absent
}
# NOTE(aschultz): LP#1750194 - docker will switch FORWARD to DROP if ip_forward
# is not enabled first.
Sysctl::Value['net.ipv4.ip_forward'] -> Package<| title == 'docker' |>

# NOTE(aschultz): LP#1754426 - remove cloud-init and disable os-collect-config
package { 'cloud-init':
  ensure => 'absent',
}
service { 'os-collect-config':
  ensure => stopped,
  enable => false,
}

# Run  OpenStack db-sync at every puppet run, in any case.
Exec<| title == 'neutron-db-sync' |> { refreshonly => false }
Exec<| title == 'keystone-manage db_sync' |> { refreshonly => false }
Exec<| title == 'glance-manage db_sync' |> { refreshonly => false }
Exec<| title == 'nova-db-sync-api' |> { refreshonly => false }
Exec<| title == 'nova-db-sync' |> { refreshonly => false }
Exec<| title == 'nova-db-online-data-migrations' |> { refreshonly => false }
Exec<| title == 'ironic-db-online-data-migrations' |> { refreshonly => false }
Exec<| title == 'heat-dbsync' |> {
  refreshonly => false,
  # Heat database on the undercloud can be really big, db-sync take usually at least 10 min.
  timeout     => 900,
}
Exec<| title == 'aodh-db-sync' |> { refreshonly => false }
Exec<| title == 'ironic-dbsync' |> { refreshonly => false }
Exec<| title == 'mistral-db-sync' |> { refreshonly => false }
Exec<| title == 'mistral-db-populate' |> { refreshonly => false }
Exec<| title == 'zaqar-manage db_sync' |> { refreshonly => false }
Exec<| title == 'cinder-manage db_sync' |> { refreshonly => false }

Keystone::Resource::Service_identity {
  default_domain => hiera('keystone_default_domain'),
}

include ::tripleo::profile::base::time::ntp

include ::rabbitmq
Class['::rabbitmq'] -> Service['httpd']

include ::tripleo::firewall
include ::tripleo::selinux
include ::tripleo::profile::base::kernel

if hiera('tripleo::haproxy::service_certificate', undef) {
  if str2bool(hiera('generate_service_certificates')) {
    include ::tripleo::profile::base::certmonger_user
  }
  class {'::tripleo::profile::base::haproxy':
    enable_load_balancer => true,
  }
  include ::tripleo::keepalived
  # NOTE: The following is required because we need to make sure that keepalived
  # is up and running before rabbitmq. The reason is that when the undercloud is
  # with ssl the hostname is configured to one of the VIPs so rabbit will try to
  # connect to it at startup and if the VIP is not up it will fail (LP#1782814)
  Class['::tripleo::keepalived'] -> Class['::rabbitmq']

  # NOTE: This is required because the haproxy configuration should be changed
  # before any keystone operations are triggered. Without this, it will try to
  # access the new endpoints that point to haproxy even if haproxy hasn't
  # started yet. The same is the case for ironic and ironic-inspector.
  Class['::tripleo::haproxy'] -> Anchor['keystone::install::begin']
}

# MySQL
include ::tripleo::profile::base::database::mysql
# Raise the mysql file limit
exec { 'systemctl-daemon-reload-undercloud':
  command     => '/bin/systemctl daemon-reload',
  refreshonly => true,
}
file { '/etc/systemd/system/mariadb.service.d':
  ensure => 'directory',
  owner  => 'root',
  group  => 'root',
  mode   => '0755',
}
file { '/etc/systemd/system/mariadb.service.d/limits.conf':
  ensure  => 'file',
  owner   => 'root',
  group   => 'root',
  mode    => '0644',
  content => "[Service]\nLimitNOFILE=16384\n",
  require => File['/etc/systemd/system/mariadb.service.d'],
  notify  => [Exec['systemctl-daemon-reload-undercloud'], Service['mysqld']],
}
Exec['systemctl-daemon-reload-undercloud'] -> Service['mysqld']

file { '/var/log/journal':
  ensure => 'directory',
  owner  => 'root',
  group  => 'root',
  mode   => '0755',
  notify => Service['systemd-journald'],
}
service { 'systemd-journald':
  ensure => 'running'
}

# FIXME: this should only occur on the bootstrap host (ditto for db syncs)
# Create all the database schemas
# Example DSN format: mysql+pymysql://user:password@host/dbname
$allowed_hosts = ['%',hiera('controller_host')]
$re_dsn = '//([^:]+):([^@]+)@\[?([^/]+?)\]?/([a-z_-]+)'
$keystone_dsn = match(hiera('keystone::database_connection'), $re_dsn)
class { '::keystone::db::mysql':
  user          => $keystone_dsn[1],
  password      => $keystone_dsn[2],
  host          => $keystone_dsn[3],
  dbname        => $keystone_dsn[4],
  allowed_hosts => $allowed_hosts,
}
$glance_dsn = match(hiera('glance::api::database_connection'), $re_dsn)
class { '::glance::db::mysql':
  user          => $glance_dsn[1],
  password      => $glance_dsn[2],
  host          => $glance_dsn[3],
  dbname        => $glance_dsn[4],
  allowed_hosts => $allowed_hosts,
}
$nova_dsn = match(hiera('nova::database_connection'), $re_dsn)
class { '::nova::db::mysql':
  user          => $nova_dsn[1],
  password      => $nova_dsn[2],
  host          => $nova_dsn[3],
  dbname        => $nova_dsn[4],
  allowed_hosts => $allowed_hosts,
}
$nova_api_dsn = match(hiera('nova::api_database_connection'), $re_dsn)
class { '::nova::db::mysql_api':
  user          => $nova_api_dsn[1],
  password      => $nova_api_dsn[2],
  host          => $nova_api_dsn[3],
  dbname        => $nova_api_dsn[4],
  allowed_hosts => $allowed_hosts,
}
$nova_placement_dsn = match(hiera('nova::placement_database_connection'), $re_dsn)
class { '::nova::db::mysql_placement':
  user          => $nova_placement_dsn[1],
  password      => $nova_placement_dsn[2],
  host          => $nova_placement_dsn[3],
  dbname        => $nova_placement_dsn[4],
  allowed_hosts => $allowed_hosts,
}
$neutron_dsn = match(hiera('neutron::server::database_connection'), $re_dsn)
class { '::neutron::db::mysql':
  user          => $neutron_dsn[1],
  password      => $neutron_dsn[2],
  host          => $neutron_dsn[3],
  dbname        => $neutron_dsn[4],
  allowed_hosts => $allowed_hosts,
}
$heat_dsn = match(hiera('heat_dsn'), $re_dsn)
class { '::heat::db::mysql':
  user          => $heat_dsn[1],
  password      => $heat_dsn[2],
  host          => $heat_dsn[3],
  dbname        => $heat_dsn[4],
  allowed_hosts => $allowed_hosts,
}
if str2bool(hiera('enable_telemetry', false)) {

  # Ceilometer

  include ::ceilometer::keystone::auth
  include ::aodh::keystone::auth
  include ::ceilometer
  include ::ceilometer::agent::notification
  include ::ceilometer::agent::central
  include ::ceilometer::agent::auth
  include ::ceilometer::dispatcher::gnocchi

  # We need to use exec as the keystone dependency wouldnt allow
  # us to wait until service is up before running upgrade. This
  # is because both keystone, gnocchi and ceilometer run under apache.
  exec { 'ceilo-gnocchi-upgrade':
    command => 'ceilometer-upgrade --skip-metering-database',
    path    => ['/usr/bin', '/usr/sbin'],
  }

  # This ensures we can do service validation on gnocchi api before
  # running ceilometer-upgrade
  $command = join(['curl -s',
                  hiera('gnocchi_healthcheck_url')], ' ')

  openstacklib::service_validation { 'gnocchi-status':
    command     => $command,
    tries       => 20,
    refreshonly => true,
    subscribe   => Anchor['gnocchi::service::end']
  }

# Ensure all endpoint exists and only then run the upgrade.
  Keystone::Resource::Service_identity<||>
  -> Openstacklib::Service_validation['gnocchi-status']
  -> Exec['ceilo-gnocchi-upgrade']

  # Aodh
  $aodh_dsn = match(hiera('aodh::db::database_connection'), $re_dsn)
  class { '::aodh::db::mysql':
    user          => $aodh_dsn[1],
    password      => $aodh_dsn[2],
    host          => $aodh_dsn[3],
    dbname        => $aodh_dsn[4],
    allowed_hosts => $allowed_hosts,
  }
  include ::aodh
  include ::aodh::api
  include ::aodh::wsgi::apache
  include ::aodh::evaluator
  include ::aodh::notifier
  include ::aodh::listener
  include ::aodh::client
  include ::aodh::db::sync
  include ::aodh::auth
  include ::aodh::config

  # Gnocchi
  $gnocchi_dsn = match(hiera('gnocchi::db::database_connection'), $re_dsn)
  class { '::gnocchi::db::mysql':
    user          => $gnocchi_dsn[1],
    password      => $gnocchi_dsn[2],
    host          => $gnocchi_dsn[3],
    dbname        => $gnocchi_dsn[4],
    allowed_hosts => $allowed_hosts,
  }
  include ::gnocchi
  include ::gnocchi::keystone::auth
  include ::gnocchi::api
  include ::gnocchi::wsgi::apache
  include ::gnocchi::client
  include ::gnocchi::db::sync
  include ::gnocchi::storage
  include ::gnocchi::metricd
  include ::gnocchi::statsd
  include ::gnocchi::config
  $gnocchi_backend = downcase(hiera('gnocchi_backend', 'swift'))
  case $gnocchi_backend {
      'swift': { include ::gnocchi::storage::swift }
      'file': { include ::gnocchi::storage::file }
      'rbd': { include ::gnocchi::storage::ceph }
      default: { fail('Unrecognized gnocchi_backend parameter.') }
  }

  # Panko
  $panko_dsn = match(hiera('panko::db::database_connection'), $re_dsn)
  class { '::panko::db::mysql':
    user          => $panko_dsn[1],
    password      => $panko_dsn[2],
    host          => $panko_dsn[3],
    dbname        => $panko_dsn[4],
    allowed_hosts => $allowed_hosts,
  }
  include ::panko
  include ::panko::keystone::auth
  include ::panko::config
  include ::panko::db
  include ::panko::db::sync
  include ::panko::api
  include ::panko::wsgi::apache
  include ::panko::client
} else {
  # If Telemetry is disabled, ensure we tear down everything:
  # packages, services, configuration files.
  Package { [
    'python-aodh',
    'python-ceilometer',
    'python-gnocchi',
    'python-panko'
  ]:
    ensure => 'purged',
    notify => Service['httpd'],
  }
  File { [
    '/etc/httpd/conf.d/10-aodh_wsgi.conf',
    '/etc/httpd/conf.d/10-ceilometer_wsgi.conf',
    '/etc/httpd/conf.d/10-gnocchi_wsgi.conf',
    '/etc/httpd/conf.d/10-panko_wsgi.conf',
  ]:
    ensure => absent,
    notify => Service['httpd'],
  }
}

$ironic_dsn = match(hiera('ironic::database_connection'), $re_dsn)
class { '::ironic::db::mysql':
  user          => $ironic_dsn[1],
  password      => $ironic_dsn[2],
  host          => $ironic_dsn[3],
  dbname        => $ironic_dsn[4],
  allowed_hosts => $allowed_hosts,
}

$ironic_inspector_dsn = match(hiera('ironic::inspector::db::database_connection'), $re_dsn)
class { '::ironic::inspector::db::mysql':
  user          => $ironic_inspector_dsn[1],
  password      => $ironic_inspector_dsn[2],
  host          => $ironic_inspector_dsn[3],
  dbname        => $ironic_inspector_dsn[4],
  allowed_hosts => $allowed_hosts,
}

# pre-install swift here so we can build rings
include ::swift

if hiera('tripleo::haproxy::service_certificate', undef) {
  $keystone_public_endpoint = join(['https://', hiera('controller_public_host'), ':13000'])
  $enable_proxy_headers_parsing = true
} else {
  $keystone_public_endpoint = undef
  $enable_proxy_headers_parsing = false
}

if str2bool(hiera('enable_telemetry', false)) {
  $notification_topics = ['notifications']
} else {
  $notification_topics = []
}

class { '::keystone':
  enable_proxy_headers_parsing => $enable_proxy_headers_parsing,
  notification_topics          => $notification_topics,
}
include ::keystone::wsgi::apache
include ::keystone::cron::token_flush
include ::keystone::roles::admin
include ::keystone::endpoint
include ::keystone::cors
include ::keystone::config

include ::heat::keystone::auth
include ::heat::keystone::auth_cfn
include ::neutron::keystone::auth
include ::glance::keystone::auth
include ::nova::keystone::auth
include ::nova::keystone::auth_placement
include ::swift::keystone::auth
include ::ironic::keystone::auth
include ::ironic::keystone::auth_inspector

#TODO: need a cleanup-keystone-tokens.sh solution here
keystone_config {
  'ec2/driver': value => 'keystone.contrib.ec2.backends.sql.Ec2';
}

# TODO: notifications, scrubber, etc.
class { '::glance::api':
  enable_proxy_headers_parsing => $enable_proxy_headers_parsing,
}
include ::glance::backend::swift
include ::glance::notify::rabbitmq

class { '::nova':
  debug               => hiera('debug'),
  notification_format => 'unversioned',
}

class { '::nova::api':
  enable_proxy_headers_parsing => $enable_proxy_headers_parsing,
}
include ::nova::wsgi::apache_api
include ::nova::cell_v2::simple_setup
include ::nova::placement
include ::nova::wsgi::apache_placement
include ::nova::cron::archive_deleted_rows
include ::nova::config
include ::nova::conductor
include ::nova::scheduler
include ::nova::scheduler::filter
include ::nova::compute

class { '::neutron':
  rabbit_hosts => [hiera('controller_host')],
  debug        => hiera('debug'),
}

include ::neutron::server
include ::neutron::server::notifications
include ::neutron::quota
include ::neutron::plugins::ml2
include ::neutron::plugins::ml2::networking_baremetal
include ::neutron::agents::ml2::networking_baremetal
include ::neutron::config

# Make sure ironic endpoint exists before starting the service
Keystone_endpoint <||> -> Service['ironic-neutron-agent']

# NOTE(lucasagomes): This bit might be superseded by
# https://review.openstack.org/#/c/172040/
file { 'dnsmasq-ironic.conf':
  ensure  => present,
  path    => '/etc/dnsmasq-ironic.conf',
  owner   => 'ironic',
  group   => 'ironic',
  mode    => '0644',
  replace => false,
  content => 'dhcp-match=ipxe,175';
}
Package['openstack-ironic-common'] -> File['dnsmasq-ironic.conf']

class { '::neutron::agents::dhcp':
  dnsmasq_config_file => '/etc/dnsmasq-ironic.conf',
}

class { '::neutron::agents::l3':
}

class { '::neutron::agents::ml2::ovs':
  bridge_mappings => split(hiera('neutron_bridge_mappings'), ','),
}

neutron_config {
  'DEFAULT/notification_driver': value => 'messaging';
}

# swift proxy
include ::memcached
include ::swift::proxy
include ::swift::ringbuilder
include ::swift::proxy::proxy_logging
include ::swift::proxy::healthcheck
include ::swift::proxy::bulk
include ::swift::proxy::cache
include ::swift::proxy::keystone
include ::swift::proxy::authtoken
include ::swift::proxy::staticweb
include ::swift::proxy::copy
include ::swift::proxy::slo
include ::swift::proxy::dlo
include ::swift::proxy::versioned_writes
include ::swift::proxy::ratelimit
include ::swift::proxy::catch_errors
include ::swift::proxy::tempurl
include ::swift::proxy::formpost
include ::swift::objectexpirer
include ::swift::config

# swift storage
class { '::swift::storage::all':
  mount_check    => str2bool(hiera('swift_mount_check')),
  allow_versions => true,
}
if(!defined(File['/srv/node'])) {
  file { '/srv/node':
    ensure  => directory,
    owner   => 'swift',
    group   => 'swift',
    require => Package['swift'],
  }
}
# This is no longer automatically created by Swift itself
file { '/srv/node/1':
    ensure  => directory,
    owner   => 'swift',
    group   => 'swift',
    require => File['/srv/node'],
}
$swift_components = ['account', 'container', 'object']
swift::storage::filter::recon { $swift_components : }
swift::storage::filter::healthcheck { $swift_components : }

$controller_host = hiera('controller_host_wrapped')
ring_object_device { "${controller_host}:6000/1":
  zone   => 1,
  weight => 1,
}
Ring_object_device<||> ~> Service['swift-proxy-server']
ring_container_device { "${controller_host}:6001/1":
  zone   => 1,
  weight => 1,
}
Ring_container_device<||> ~> Service['swift-proxy-server']
ring_account_device { "${controller_host}:6002/1":
  zone   => 1,
  weight => 1,
}
Ring_account_device<||> ~> Service['swift-proxy-server']

# Ensure rsyslog catches up change in /etc/rsyslog.d and forwards logs
exec { 'restart rsyslog':
  command => '/bin/systemctl restart rsyslog',
}

# Apache
include ::apache

# Heat
class { '::heat':
  debug                        => hiera('debug'),
  keystone_ec2_uri             => join([hiera('keystone_auth_uri'), '/ec2tokens']),
  enable_proxy_headers_parsing => $enable_proxy_headers_parsing,
  heat_clients_endpoint_type   => hiera('heat_clients_endpoint_type', 'internal'),
}
include ::heat::api
include ::heat::wsgi::apache_api
include ::heat::api_cfn
include ::heat::wsgi::apache_api_cfn
include ::heat::engine
include ::heat::keystone::domain
include ::heat::cron::purge_deleted
include ::heat::cors
include ::heat::config

include ::keystone::roles::admin

nova_config {
  'DEFAULT/sync_power_state_interval': value => hiera('nova_sync_power_state_interval');
}

include ::nova::compute::ironic
include ::nova::network::neutron
include ::nova::cors

# Ironic

include ::ironic
include ::ironic::api
include ::ironic::wsgi::apache
include ::ironic::conductor
include ::ironic::drivers::ansible
include ::ironic::drivers::drac
include ::ironic::drivers::ilo
include ::ironic::drivers::inspector
include ::ironic::drivers::interfaces
include ::ironic::drivers::ipmi
include ::ironic::drivers::pxe
include ::ironic::drivers::redfish
include ::ironic::drivers::staging
include ::ironic::glance
include ::ironic::inspector
include ::ironic::inspector::cors
include ::ironic::inspector::pxe_filter
include ::ironic::inspector::pxe_filter::dnsmasq
include ::ironic::neutron
include ::ironic::pxe
include ::ironic::service_catalog
include ::ironic::swift
include ::ironic::cors
include ::ironic::config

Keystone_endpoint<||> -> Service['ironic-inspector']

# https://bugs.launchpad.net/tripleo/+bug/1663273
Keystone_endpoint <||> -> Service['nova-compute']
Keystone_service <||> -> Service['nova-compute']

# This is a workaround for a race between nova-compute and ironic
# conductor.  When https://bugs.launchpad.net/tripleo/+bug/1777608 is
# fixed this can be removed.  Currently we wait 1 minutes for the
# ironic conductor service to be ready. As puppet can order thing its
# own way and be slow (especially in CI env) we can have services
# started at more than one minute appart, hence the need for it.
Service[$::ironic::params::conductor_service] -> Service[$::nova::params::compute_service_name]

if str2bool(hiera('enable_tempest', true)) {
  # tempest
  package{'openstack-tempest': }
  # needed for /bin/subunit-2to1 (called by run_tempest.sh)
  package{'subunit-filters': }
}

# Ensure dm thin-pool is never activated. This avoids an issue
# where the instack host (in this case on a VM) was crashing due to
# activation of the docker thin-pool associated with the atomic host.
augeas { 'lvm.conf':
  require => Package['nova-compute'],
  context => '/files/etc/lvm/lvm.conf/devices/dict/',
  changes => 'set global_filter/list/1/str "r|^/dev/disk/by-path/ip.*iscsi.*\.org\.openstack:.*|"'
}

if str2bool(hiera('enable_docker_registry', true)) {
  ensure_resource('group', 'docker', {
    'ensure' => 'present',
  })
  ensure_resource('user', 'docker_user', {
    'name'   => hiera('tripleo_install_user'),
    'groups' => 'docker',
    'notify' => Service['docker'],
  })
  include ::tripleo::profile::base::docker_registry
}

include ::mistral
$mistral_dsn = match(hiera('mistral::database_connection'), $re_dsn)
class { '::mistral::db::mysql':
  user          => $mistral_dsn[1],
  password      => $mistral_dsn[2],
  host          => $mistral_dsn[3],
  dbname        => $mistral_dsn[4],
  allowed_hosts => $allowed_hosts,
}
include ::mistral::keystone::auth
include ::mistral::db::sync
include ::mistral::api
include ::mistral::engine
include ::mistral::executor
include ::mistral::cors
include ::mistral::cron_trigger
include ::mistral::config

# ensure TripleO common entrypoints for custom Mistral actions
# are installed before performing the Mistral action population
package {'openstack-tripleo-common': }
Package['openstack-tripleo-common'] ~> Exec['mistral-db-populate']
# If ironic inspector is not running, mistral-db-populate will have invalid
# actions for it.
Class['::ironic::inspector'] ~> Exec['mistral-db-populate']
# db-populate calls inspectorclient, which will use the keystone endpoint to
# check inspector's version. So that's needed before db-populate is executed.
Class['::ironic::keystone::auth_inspector']  ~> Exec['mistral-db-populate']

if str2bool(hiera('enable_ui', true)) {
  include ::tripleo::ui
}

if str2bool(hiera('enable_validations', true)) {
  include ::tripleo::profile::base::validations
}

include ::zaqar
$zaqar_dsn = match(hiera('zaqar::management::sqlalchemy::uri'), $re_dsn)
class { '::zaqar::db::mysql':
  user          => $zaqar_dsn[1],
  password      => $zaqar_dsn[2],
  host          => $zaqar_dsn[3],
  dbname        => $zaqar_dsn[4],
  allowed_hosts => $allowed_hosts,
}
include ::zaqar::db::sync
include ::zaqar::management::sqlalchemy
include ::zaqar::messaging::swift
include ::zaqar::keystone::auth
include ::zaqar::keystone::auth_websocket
include ::zaqar::transport::websocket
include ::zaqar::transport::wsgi

include ::zaqar::server
include ::zaqar::wsgi::apache
include ::zaqar::config

zaqar::server_instance{ '1':
  transport => 'websocket'
}

if str2bool(hiera('enable_cinder', true)) {
  $cinder_dsn = match(hiera('cinder::database_connection'), $re_dsn)
  class { '::cinder::db::mysql':
    user          => $cinder_dsn[1],
    password      => $cinder_dsn[2],
    host          => $cinder_dsn[3],
    dbname        => $cinder_dsn[4],
    allowed_hosts => $allowed_hosts,
  }
  include ::cinder::keystone::auth

  include ::cinder
  include ::cinder::api
  include ::cinder::cron::db_purge
  include ::cinder::config
  include ::cinder::glance
  include ::cinder::scheduler
  include ::cinder::volume
  include ::cinder::wsgi::apache

  $cinder_backend_name = hiera('cinder_backend_name')
  cinder::backend::iscsi { $cinder_backend_name:
    iscsi_ip_address => hiera('cinder_iscsi_address'),
    iscsi_helper     => 'lioadm',
    iscsi_protocol   => 'iscsi'
  }

  include ::cinder::backends

  if str2bool(hiera('cinder_enable_test_volume', false)) {
    include ::cinder::setup_test_volume
  }
}

# firewalld is a dependency of some anaconda packages, so we need to use purge
# to ensure all the things that it might be a dependency for are also
# removed. See LP#1669915
ensure_resource('package', 'firewalld', {
  'ensure' => 'purged',
})
ensure_resource('package', 'openstack-selinux')
ensure_resource('package', 'parted')
ensure_resource('package', 'psmisc')

include ::tripleo::profile::base::sshd

# Swift is using only a single replica on the undercloud. Therefore recovering
# from a corrupted or lost object is not possible, and running replicators and
# auditors only wastes resources.
$needless_services = [
  'swift-account-auditor',
  'swift-account-replicator',
  'swift-container-auditor',
  'swift-container-replicator',
  'swift-object-auditor',
  'swift-object-replicator']

Service[$needless_services] {
  enable => false,
  ensure => stopped,
}

# novajoin install
if str2bool(hiera('enable_novajoin', false)) {
  include ::nova::metadata::novajoin::auth
  include ::nova::metadata::novajoin::api
}

# Any special handling that need to be done during the upgrade.
if str2bool($::undercloud_upgrade) {
  # Noop
}

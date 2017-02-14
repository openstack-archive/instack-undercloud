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

# Run  OpenStack db-sync at every puppet run, in any case.
Exec<| title == 'neutron-db-sync' |> { refreshonly => false }
Exec<| title == 'keystone-manage db_sync' |> { refreshonly => false }
Exec<| title == 'glance-manage db_sync' |> { refreshonly => false }
Exec<| title == 'nova-db-sync-api' |> { refreshonly => false }
Exec<| title == 'nova-db-sync' |> { refreshonly => false }
Exec<| title == 'nova-db-online-data-migrations' |> { refreshonly => false }
Exec<| title == 'heat-dbsync' |> { refreshonly => false }
Exec<| title == 'ceilometer-dbsync' |> { refreshonly => false }
Exec<| title == 'aodh-db-sync' |> { refreshonly => false }
Exec<| title == 'ironic-dbsync' |> { refreshonly => false }
Exec<| title == 'mistral-db-sync' |> { refreshonly => false }
Exec<| title == 'mistral-db-populate' |> { refreshonly => false }
Exec<| title == 'zaqar-manage db_sync' |> { refreshonly => false }
Exec<| title == 'cinder-manage db_sync' |> { refreshonly => false }

if count(hiera('ntp::servers')) > 0 {
  include ::tripleo::profile::base::time::ntp
}

include ::rabbitmq
include ::tripleo::firewall
include ::tripleo::selinux
include ::tripleo::profile::base::kernel

if hiera('tripleo::haproxy::service_certificate', undef) {
  class {'::tripleo::profile::base::haproxy':
    enable_load_balancer => true,
  }
  include ::tripleo::keepalived
  # NOTE: This is required because the haproxy configuration should be changed
  # before any keystone operations are triggered. Without this, it will try to
  # access the new endpoints that point to haproxy even if haproxy hasn't
  # started yet. The same is the case for ironic and ironic-inspector.
  Class['::tripleo::haproxy'] -> Anchor['keystone::install::begin']
}

# MySQL
include ::tripleo::profile::base::database::mysql
# Raise the mysql file limit
exec { 'systemctl-daemon-reload':
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
  notify  => [Exec['systemctl-daemon-reload'], Service['mysqld']],
}
Exec['systemctl-daemon-reload'] -> Service['mysqld']

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
$keystone_dsn = split(hiera('keystone::database_connection'), '[@:/?]')
class { '::keystone::db::mysql':
  user          => $keystone_dsn[3],
  password      => $keystone_dsn[4],
  host          => $keystone_dsn[5],
  dbname        => $keystone_dsn[6],
  allowed_hosts => $allowed_hosts,
}
$glance_dsn = split(hiera('glance::api::database_connection'), '[@:/?]')
class { '::glance::db::mysql':
  user          => $glance_dsn[3],
  password      => $glance_dsn[4],
  host          => $glance_dsn[5],
  dbname        => $glance_dsn[6],
  allowed_hosts => $allowed_hosts,
}
$nova_dsn = split(hiera('nova::database_connection'), '[@:/?]')
class { '::nova::db::mysql':
  user          => $nova_dsn[3],
  password      => $nova_dsn[4],
  host          => $nova_dsn[5],
  dbname        => $nova_dsn[6],
  allowed_hosts => $allowed_hosts,
}
$nova_api_dsn = split(hiera('nova::api_database_connection'), '[@:/?]')
class { '::nova::db::mysql_api':
  user          => $nova_api_dsn[3],
  password      => $nova_api_dsn[4],
  host          => $nova_api_dsn[5],
  dbname        => $nova_api_dsn[6],
  allowed_hosts => $allowed_hosts,
}
$nova_placement_dsn = split(hiera('nova::placement_database_connection'), '[@:/?]')
class { '::nova::db::mysql_placement':
  user          => $nova_placement_dsn[3],
  password      => $nova_placement_dsn[4],
  host          => $nova_placement_dsn[5],
  dbname        => $nova_placement_dsn[6],
  allowed_hosts => $allowed_hosts,
}
$neutron_dsn = split(hiera('neutron::server::database_connection'), '[@:/?]')
class { '::neutron::db::mysql':
  user          => $neutron_dsn[3],
  password      => $neutron_dsn[4],
  host          => $neutron_dsn[5],
  dbname        => $neutron_dsn[6],
  allowed_hosts => $allowed_hosts,
}
$heat_dsn = split(hiera('heat_dsn'), '[@:/?]')
class { '::heat::db::mysql':
  user          => $heat_dsn[3],
  password      => $heat_dsn[4],
  host          => $heat_dsn[5],
  dbname        => $heat_dsn[6],
  allowed_hosts => $allowed_hosts,
}
if str2bool(hiera('enable_telemetry', true)) {

  # Ceilometer
  $ceilometer_dsn = split(hiera('ceilometer::db::database_connection'), '[@:/?]')
  class { '::ceilometer::db::mysql':
    user          => $ceilometer_dsn[3],
    password      => $ceilometer_dsn[4],
    host          => $ceilometer_dsn[5],
    dbname        => $ceilometer_dsn[6],
    allowed_hosts => $allowed_hosts,
  }
  include ::ceilometer::keystone::auth
  include ::aodh::keystone::auth
  include ::ceilometer
  if str2bool(hiera('enable_legacy_ceilometer_api', true)) {
    include ::ceilometer::api
  }
  include ::ceilometer::wsgi::apache
  include ::ceilometer::db
  include ::ceilometer::agent::notification
  include ::ceilometer::agent::central
  include ::ceilometer::expirer
  include ::ceilometer::collector
  include ::ceilometer::agent::auth
  include ::ceilometer::dispatcher::gnocchi

  Cron <| title == 'ceilometer-expirer' |> { command =>
    "sleep $((\$(od -A n -t d -N 3 /dev/urandom) % 86400)) && ${::ceilometer::params::expirer_command}" }

  # TODO: add support for setting these to puppet-ceilometer
  ceilometer_config {
    'hardware/readonly_user_name': value => hiera('snmpd_readonly_user_name');
    'hardware/readonly_user_password': value => hiera('snmpd_readonly_user_password');
  }

  # Aodh
  $aodh_dsn = split(hiera('aodh::db::database_connection'), '[@:/?]')
  class { '::aodh::db::mysql':
    user          => $aodh_dsn[3],
    password      => $aodh_dsn[4],
    host          => $aodh_dsn[5],
    dbname        => $aodh_dsn[6],
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

  # Gnocchi
  $gnocchi_dsn = split(hiera('gnocchi::db::database_connection'), '[@:/?]')
  class { '::gnocchi::db::mysql':
    user          => $gnocchi_dsn[3],
    password      => $gnocchi_dsn[4],
    host          => $gnocchi_dsn[5],
    dbname        => $gnocchi_dsn[6],
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
  $gnocchi_backend = downcase(hiera('gnocchi_backend', 'swift'))
  case $gnocchi_backend {
      'swift': { include ::gnocchi::storage::swift }
      'file': { include ::gnocchi::storage::file }
      'rbd': { include ::gnocchi::storage::ceph }
      default: { fail('Unrecognized gnocchi_backend parameter.') }
  }

  # Panko
  $panko_dsn = split(hiera('panko::db::database_connection'), '[@:/?]')
  class { '::panko::db::mysql':
    user          => $panko_dsn[3],
    password      => $panko_dsn[4],
    host          => $panko_dsn[5],
    dbname        => $panko_dsn[6],
    allowed_hosts => $allowed_hosts,
  }
  include ::panko
  include ::panko::keystone::auth
  include ::panko::config
  include ::panko::db
  include ::panko::db::sync
  include ::panko::api
  include ::panko::wsgi::apache
}

$ironic_dsn = split(hiera('ironic::database_connection'), '[@:/?]')
class { '::ironic::db::mysql':
  user          => $ironic_dsn[3],
  password      => $ironic_dsn[4],
  host          => $ironic_dsn[5],
  dbname        => $ironic_dsn[6],
  allowed_hosts => $allowed_hosts,
}

$ironic_inspector_dsn = split(hiera('ironic::inspector::db::database_connection'), '[@:/?]')
class { '::ironic::inspector::db::mysql':
  user          => $ironic_inspector_dsn[3],
  password      => $ironic_inspector_dsn[4],
  host          => $ironic_inspector_dsn[5],
  dbname        => $ironic_inspector_dsn[6],
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

class { '::keystone':
  enable_proxy_headers_parsing => $enable_proxy_headers_parsing,
}
include ::keystone::wsgi::apache
include ::keystone::cron::token_flush
include ::keystone::roles::admin
include ::keystone::endpoint
include ::keystone::cors

include ::heat::keystone::auth
include ::neutron::keystone::auth
include ::glance::keystone::auth
include ::nova::keystone::auth
include ::nova::keystone::auth_placement
include ::swift::keystone::auth
include ::ironic::keystone::auth
include ::ironic::keystone::auth_inspector

# Because os-cloud-config/tree/os_cloud_config/keystone.py already managed
# it but with a different service name than Puppet will do (novav3), we want Puppet
# to making sure computev3 is not here anymore and we will add novav3 later.
keystone_service { 'nova::computev3': ensure => absent }
Keystone_service<||> -> Keystone_endpoint<||>

#TODO: need a cleanup-keystone-tokens.sh solution here
keystone_config {
  'ec2/driver': value => 'keystone.contrib.ec2.backends.sql.Ec2';
}

if str2bool(hiera('member_role_exists', false)) {
  # Old deployments where assigning _member_ role to admin user.
  # The _member_ role is needed because it's delegated via heat trusts in
  # existing deployments, hence existing role assignments can't just be
  # deleted. This Puppet Collector will allow to update deployments with
  # admin role managed by Puppet.
  Keystone_user_role<| title == 'admin@admin' |> { roles +> ['_member_'] }
}

# TODO: notifications, scrubber, etc.
class { '::glance::api':
  enable_proxy_headers_parsing => $enable_proxy_headers_parsing,
}
include ::glance::backend::swift
include ::glance::notify::rabbitmq

class { '::nova':
  debug              => hiera('debug'),
}

class { '::nova::api':
  enable_proxy_headers_parsing => $enable_proxy_headers_parsing,
}
include ::nova::cell_v2::simple_setup
include ::nova::placement
include ::nova::wsgi::apache_placement
include ::nova::cert
include ::nova::cron::archive_deleted_rows
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
include ::swift::proxy::ratelimit
include ::swift::proxy::catch_errors
include ::swift::proxy::tempurl
include ::swift::proxy::formpost

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
$swift_components = ['account', 'container', 'object']
swift::storage::filter::recon { $swift_components : }
swift::storage::filter::healthcheck { $swift_components : }

$controller_host = hiera('controller_host')
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

# Apache
include ::apache

# Heat
class { '::heat':
  debug                        => hiera('debug'),
  keystone_ec2_uri             => join([hiera('keystone_auth_uri_v2'), '/ec2tokens']),
  enable_proxy_headers_parsing => $enable_proxy_headers_parsing,
}
heat_config {
  'clients/endpoint_type': value => 'internal',
}
include ::heat::api
include ::heat::api_cfn
include ::heat::engine
include ::heat::keystone::domain
include ::heat::cron::purge_deleted
include ::heat::cors

# We're creating the admin role and heat domain user in puppet and need
# to make sure they are done in order.
include ::keystone::roles::admin
Service['httpd'] -> Class['::keystone::roles::admin'] -> Class['::heat::keystone::domain']

nova_config {
  'DEFAULT/sync_power_state_interval': value => hiera('nova_sync_power_state_interval');
}

include ::nova::compute::ironic
include ::nova::network::neutron

# Ironic

include ::ironic
include ::ironic::api
include ::ironic::conductor
include ::ironic::drivers::ilo
include ::ironic::drivers::ipmi
include ::ironic::drivers::pxe
include ::ironic::drivers::ssh
include ::ironic::inspector
include ::ironic::pxe
include ::ironic::cors

Keystone_endpoint<||> -> Service['ironic-api']
Keystone_endpoint<||> -> Service['ironic-inspector']

# https://bugs.launchpad.net/tripleo/+bug/1663273
Keystone_endpoint <||> -> Service['nova-compute']
Keystone_service <||> -> Service['nova-compute']

if str2bool(hiera('enable_tempest', true)) {
  # tempest
  # TODO: when puppet-tempest supports install by package, do that instead
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
  package{'docker-registry': }
  package{'docker': }
  augeas { 'docker-registry':
    context => '/files/etc/sysconfig/docker-registry',
    changes => [
      'set REGISTRY_PORT 8787',
      join(['set REGISTRY_ADDRESS ', hiera('controller_host')])
    ],
    notify  => Service['docker-registry'],
  }
  file_line { 'docker insecure registry':
    path   => '/etc/sysconfig/docker',
    line   => join ([
      'INSECURE_REGISTRY="',
      '--insecure-registry ', hiera('controller_host'), ':8787 ',
      '--insecure-registry ', hiera('controller_admin_host'), ':8787"']),
    match  => 'INSECURE_REGISTRY=',
    notify => Service['docker'],
  }
  service { 'docker-registry':
    ensure  => running,
    enable  => true,
    require => Package['docker-registry'],
  }
  service { 'docker':
    ensure  => running,
    enable  => true,
    require => Package['docker'],
  }
}

include ::mistral
$mistral_dsn = split(hiera('mistral::database_connection'), '[@:/?]')
class { '::mistral::db::mysql':
  user          => $mistral_dsn[3],
  password      => $mistral_dsn[4],
  host          => $mistral_dsn[5],
  dbname        => $mistral_dsn[6],
  allowed_hosts => $allowed_hosts,
}
include ::mistral::keystone::auth
include ::mistral::db::sync
include ::mistral::api
include ::mistral::engine
include ::mistral::executor
include ::mistral::cors

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
  include ::tripleo::profile::base::ui
}

if str2bool(hiera('enable_validations', true)) {
  include ::tripleo::profile::base::validations
}

include ::mongodb::globals
include ::mongodb::server
include ::mongodb::client

include ::zaqar
include ::zaqar::management::mongodb
include ::zaqar::messaging::mongodb
include ::zaqar::keystone::auth
include ::zaqar::keystone::auth_websocket
include ::zaqar::transport::websocket
include ::zaqar::transport::wsgi

include ::zaqar::server
zaqar::server_instance{ '1':
  transport => 'websocket'
}

if str2bool(hiera('enable_cinder', true)) {
  $cinder_dsn = split(hiera('cinder::database_connection'), '[@:/?]')
  class { '::cinder::db::mysql':
    user          => $cinder_dsn[3],
    password      => $cinder_dsn[4],
    host          => $cinder_dsn[5],
    dbname        => $cinder_dsn[6],
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

# dependency of pxe_drac
ensure_resource('package', 'python-dracclient')
# dependency of pxe_ilo
ensure_resource('package', 'python-proliantutils')

ensure_resource('package', 'firewalld', {
  'ensure' => 'absent',
})
ensure_resource('package', 'os-cloud-config')
ensure_resource('package', 'openstack-selinux')
ensure_resource('package', 'syslinux-extlinux')
ensure_resource('package', 'tftp-server')
ensure_resource('package', 'parted')
ensure_resource('package', 'psmisc')
ensure_resource('package', 'ipxe-bootimgs')

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
  include ::nova::metadata::novajoin::api
}

# Upgrade Special Snowflakes
if str2bool($::undercloud_upgrade) {
  # NOTE(aschultz): Since we did not deploy cell v2 in newton, we need to be
  # able to run the cell v2 setup prior to the api db sync call. This affects
  # upgrades only.  The normal clean install process requires that the api db
  # sync occur prior to the cell v2 simple setup so we have to reorder these
  # only for upgrades. See LP#1649341
  include ::nova::deps
  include ::nova::cell_v2::map_cell_and_hosts
  class { '::nova::cell_v2::map_instances':
    cell_name => 'default',
  }
  # NOTE(aschultz): this should pull the cell v2 items out and run them before
  # the api db sync.
  # The order should be:
  #  - cell v2 setup
  #  - db sync
  #  - cell v2 map cell and hosts
  #  - cell v2 instances
  #  - api db sync
  Anchor<| title == 'nova::cell_v2::begin' |> {
    subscribe => Anchor['nova::db::end']
  }
  Anchor<| title == 'nova::cell_v2::end' |> {
    notify => Anchor['nova::dbsync_api::begin']
  }
  Anchor<| title == 'nova::dbsync::begin' |> {
    subscribe => Anchor['nova::db::end']
  }

  Class['nova::cell_v2::simple_setup'] ~>
    Anchor['nova::dbsync::begin'] ~>
      Anchor['nova::dbsync::end'] ~>
        Class['nova::cell_v2::map_cell_and_hosts'] ~>
          Class['nova::cell_v2::map_instances'] ~>
            Anchor['nova::dbsync_api::begin']
}

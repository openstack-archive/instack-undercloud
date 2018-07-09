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

import collections
import io
import json
import os
import subprocess
import tempfile
import time

import fixtures
from keystoneauth1 import exceptions as ks_exceptions
import mock
from novaclient import exceptions
from oslo_config import cfg
from oslo_config import fixture as config_fixture
from oslotest import base
from oslotest import log
from six.moves import configparser

from instack_undercloud import undercloud
from instack_undercloud import validator


undercloud._configure_logging(undercloud.DEFAULT_LOG_LEVEL, None)


class BaseTestCase(base.BaseTestCase):
    def setUp(self):
        super(BaseTestCase, self).setUp()
        self.logger = self.useFixture(log.ConfigureLogging()).logger
        self.conf = self.useFixture(config_fixture.Config())
        self.conf.config(enable_routed_networks=True)
        # ctlplane-subnet - config group options
        self.grp0 = cfg.OptGroup(name='ctlplane-subnet',
                                 title='ctlplane-subnet')
        self.opts = [cfg.StrOpt('cidr'),
                     cfg.StrOpt('dhcp_start'),
                     cfg.StrOpt('dhcp_end'),
                     cfg.StrOpt('inspection_iprange'),
                     cfg.StrOpt('gateway'),
                     cfg.BoolOpt('masquerade')]
        self.conf.register_opts(self.opts, group=self.grp0)
        self.grp1 = cfg.OptGroup(name='subnet1', title='subnet1')
        self.gtp2 = cfg.OptGroup(name='subnet2', title='subnet2')
        self.conf.config(cidr='192.168.24.0/24',
                         dhcp_start='192.168.24.5', dhcp_end='192.168.24.24',
                         inspection_iprange='192.168.24.100,192.168.24.120',
                         gateway='192.168.24.1', masquerade=True,
                         group='ctlplane-subnet')


class TestUndercloud(BaseTestCase):
    @mock.patch(
        'instack_undercloud.undercloud._load_subnets_config_groups')
    @mock.patch('instack_undercloud.undercloud._handle_upgrade_fact')
    @mock.patch('instack_undercloud.undercloud._configure_logging')
    @mock.patch('instack_undercloud.undercloud._validate_configuration')
    @mock.patch('instack_undercloud.undercloud._run_command')
    @mock.patch('instack_undercloud.undercloud._post_config')
    @mock.patch('instack_undercloud.undercloud._run_orc')
    @mock.patch('instack_undercloud.undercloud._run_yum_update')
    @mock.patch('instack_undercloud.undercloud._run_yum_clean_all')
    @mock.patch('instack_undercloud.undercloud._run_instack')
    @mock.patch('instack_undercloud.undercloud._generate_environment')
    @mock.patch('instack_undercloud.undercloud._load_config')
    @mock.patch('instack_undercloud.undercloud._run_validation_groups')
    def test_install(self, mock_run_validation_groups, mock_load_config,
                     mock_generate_environment, mock_run_instack,
                     mock_run_clean_all, mock_run_yum_update, mock_run_orc,
                     mock_post_config, mock_run_command,
                     mock_validate_configuration, mock_configure_logging,
                     mock_upgrade_fact, mock_load_subnets_config_groups):
        fake_env = mock.MagicMock()
        mock_generate_environment.return_value = fake_env
        undercloud.install('.')
        self.assertTrue(mock_validate_configuration.called)
        mock_generate_environment.assert_called_with('.')
        mock_run_instack.assert_called_with(fake_env)
        mock_run_orc.assert_called_with(fake_env)
        mock_run_command.assert_called_with(
            ['sudo', 'rm', '-f', '/tmp/svc-map-services'], None, 'rm')
        mock_upgrade_fact.assert_called_with(False)
        mock_run_validation_groups.assert_not_called()

    @mock.patch(
        'instack_undercloud.undercloud._load_subnets_config_groups')
    @mock.patch('instack_undercloud.undercloud._handle_upgrade_fact')
    @mock.patch('instack_undercloud.undercloud._configure_logging')
    @mock.patch('instack_undercloud.undercloud._validate_configuration')
    @mock.patch('instack_undercloud.undercloud._run_command')
    @mock.patch('instack_undercloud.undercloud._post_config')
    @mock.patch('instack_undercloud.undercloud._run_orc')
    @mock.patch('instack_undercloud.undercloud._run_yum_update')
    @mock.patch('instack_undercloud.undercloud._run_yum_clean_all')
    @mock.patch('instack_undercloud.undercloud._run_instack')
    @mock.patch('instack_undercloud.undercloud._generate_environment')
    @mock.patch('instack_undercloud.undercloud._load_config')
    @mock.patch('instack_undercloud.undercloud._run_validation_groups')
    def test_install_upgrade(self, mock_run_validation_groups,
                             mock_load_config,
                             mock_generate_environment,
                             mock_run_instack,
                             mock_run_yum_clean_all,
                             mock_run_yum_update,
                             mock_run_orc,
                             mock_post_config,
                             mock_run_command,
                             mock_validate_configuration,
                             mock_configure_logging,
                             mock_upgrade_fact,
                             mock_load_subnets_config_groups):
        fake_env = mock.MagicMock()
        mock_generate_environment.return_value = fake_env
        undercloud.install('.', upgrade=True)
        self.assertTrue(mock_validate_configuration.called)
        mock_generate_environment.assert_called_with('.')
        mock_run_instack.assert_called_with(fake_env)
        mock_run_orc.assert_called_with(fake_env)
        mock_run_command.assert_called_with(
            ['sudo', 'rm', '-f', '/tmp/svc-map-services'], None, 'rm')
        mock_upgrade_fact.assert_called_with(True)
        mock_run_validation_groups.assert_called_once()

    @mock.patch(
        'instack_undercloud.undercloud._load_subnets_config_groups')
    @mock.patch('instack_undercloud.undercloud._handle_upgrade_fact')
    @mock.patch('instack_undercloud.undercloud._configure_logging')
    @mock.patch('instack_undercloud.undercloud._validate_configuration')
    @mock.patch('instack_undercloud.undercloud._run_command')
    @mock.patch('instack_undercloud.undercloud._post_config')
    @mock.patch('instack_undercloud.undercloud._run_orc')
    @mock.patch('instack_undercloud.undercloud._run_yum_update')
    @mock.patch('instack_undercloud.undercloud._run_yum_clean_all')
    @mock.patch('instack_undercloud.undercloud._run_instack')
    @mock.patch('instack_undercloud.undercloud._generate_environment')
    @mock.patch('instack_undercloud.undercloud._load_config')
    @mock.patch('instack_undercloud.undercloud._run_validation_groups')
    def test_install_upgrade_hieradata(self, mock_run_validation_groups,
                                       mock_load_config,
                                       mock_generate_environment,
                                       mock_run_instack,
                                       mock_run_yum_clean_all,
                                       mock_run_yum_update, mock_run_orc,
                                       mock_post_config, mock_run_command,
                                       mock_validate_configuration,
                                       mock_configure_logging,
                                       mock_upgrade_fact,
                                       mock_load_subnets_config_groups):
        self.conf.config(hieradata_override='override.yaml')
        with open(os.path.expanduser('~/override.yaml'), 'w') as f:
            f.write('Something\n')
        fake_env = mock.MagicMock()
        mock_generate_environment.return_value = fake_env
        undercloud.install('.', upgrade=True)
        self.assertTrue(mock_validate_configuration.called)
        mock_generate_environment.assert_called_with('.')
        mock_run_instack.assert_called_with(fake_env)
        mock_run_orc.assert_called_with(fake_env)
        mock_run_command.assert_called_with(
            ['sudo', 'rm', '-f', '/tmp/svc-map-services'], None, 'rm')
        self.assertNotIn(
            mock.call(
                ['sudo', 'cp', 'override.yaml',
                 '/etc/puppet/hieradata/override.yaml']),
            mock_run_command.mock_calls)
        mock_upgrade_fact.assert_called_with(True)
        mock_run_validation_groups.assert_called_once()

    @mock.patch('instack_undercloud.undercloud._configure_logging')
    def test_install_exception(self, mock_configure_logging):
        mock_configure_logging.side_effect = RuntimeError('foo')
        self.assertRaises(RuntimeError, undercloud.install, '.')
        log_dict = {'undercloud_operation': "install",
                    'exception': 'foo',
                    'log_file': undercloud.PATHS.LOG_FILE
                    }
        self.assertIn(undercloud.FAILURE_MESSAGE % log_dict,
                      self.logger.output)

    @mock.patch('sys.exit')
    @mock.patch('instack_undercloud.undercloud._configure_logging')
    def test_install_exception_no_debug(self, mock_configure_logging,
                                        mock_exit):
        mock_configure_logging.side_effect = RuntimeError('foo')
        self.conf.config(undercloud_debug=False)
        undercloud.install('.')
        log_dict = {'undercloud_operation': "install",
                    'exception': 'foo',
                    'log_file': undercloud.PATHS.LOG_FILE
                    }
        self.assertIn(undercloud.FAILURE_MESSAGE % log_dict,
                      self.logger.output)
        mock_exit.assert_called_with(1)

    def test_generate_password(self):
        first = undercloud._generate_password()
        second = undercloud._generate_password()
        self.assertNotEqual(first, second)

    def test_extract_from_stackrc(self):
        with open(os.path.expanduser('~/stackrc'), 'w') as f:
            f.write('OS_USERNAME=aturing\n')
            f.write('OS_AUTH_URL=https://bletchley:5000/\n')
        self.assertEqual('aturing',
                         undercloud._extract_from_stackrc('OS_USERNAME'))
        self.assertEqual('https://bletchley:5000/',
                         undercloud._extract_from_stackrc('OS_AUTH_URL'))

    @mock.patch('instack_undercloud.undercloud._check_hostname')
    @mock.patch('instack_undercloud.undercloud._check_memory')
    @mock.patch('instack_undercloud.undercloud._check_sysctl')
    @mock.patch('instack_undercloud.undercloud._validate_network')
    @mock.patch('instack_undercloud.undercloud._validate_no_ip_change')
    @mock.patch('instack_undercloud.undercloud._validate_passwords_file')
    def test_validate_configuration(self, mock_vpf, mock_vnic,
                                    mock_validate_network,
                                    mock_check_memory, mock_check_hostname,
                                    mock_check_sysctl):
        undercloud._validate_configuration()
        self.assertTrue(mock_vpf.called)
        self.assertTrue(mock_vnic.called)
        self.assertTrue(mock_validate_network.called)
        self.assertTrue(mock_check_memory.called)
        self.assertTrue(mock_check_hostname.called)
        self.assertTrue(mock_check_sysctl.called)


class TestCheckHostname(BaseTestCase):
    @mock.patch('instack_undercloud.undercloud._run_command')
    def test_correct(self, mock_run_command):
        mock_run_command.side_effect = ['test-hostname', 'test-hostname']
        self.useFixture(fixtures.EnvironmentVariable('HOSTNAME',
                                                     'test-hostname'))
        fake_hosts = io.StringIO(u'127.0.0.1 test-hostname\n')
        with mock.patch('instack_undercloud.undercloud.open',
                        return_value=fake_hosts, create=True):
            undercloud._check_hostname()

    @mock.patch('instack_undercloud.undercloud._run_command')
    def test_static_transient_mismatch(self, mock_run_command):
        mock_run_command.side_effect = ['test-hostname', 'other-hostname']
        self.useFixture(fixtures.EnvironmentVariable('HOSTNAME',
                                                     'test-hostname'))
        fake_hosts = io.StringIO(u'127.0.0.1 test-hostname\n')
        with mock.patch('instack_undercloud.undercloud.open',
                        return_value=fake_hosts, create=True):
            self.assertRaises(RuntimeError, undercloud._check_hostname)

    @mock.patch('instack_undercloud.undercloud._run_command')
    def test_no_substring_match(self, mock_run_command):
        mock_run_command.side_effect = ['test.hostname', 'test.hostname',
                                        None]
        self.useFixture(fixtures.EnvironmentVariable('HOSTNAME',
                                                     'test.hostname'))
        fake_hosts = io.StringIO(u'127.0.0.1 test-hostname-bad\n')
        with mock.patch('instack_undercloud.undercloud.open',
                        return_value=fake_hosts, create=True):
            undercloud._check_hostname()
            mock_run_command.assert_called_with([
                'sudo', '/bin/bash', '-c',
                'sed -i "s/127.0.0.1\(\s*\)/127.0.0.1\\1test.hostname test /" '
                '/etc/hosts'],
                name='hostname-to-etc-hosts')

    @mock.patch('instack_undercloud.undercloud._run_command')
    def test_commented(self, mock_run_command):
        mock_run_command.side_effect = ['test.hostname', 'test.hostname',
                                        None]
        self.useFixture(fixtures.EnvironmentVariable('HOSTNAME',
                                                     'test.hostname'))
        fake_hosts = io.StringIO(u""" #127.0.0.1 test.hostname\n
                                     127.0.0.1 other-hostname\n""")
        with mock.patch('instack_undercloud.undercloud.open',
                        return_value=fake_hosts, create=True):
            undercloud._check_hostname()
            mock_run_command.assert_called_with([
                'sudo', '/bin/bash', '-c',
                'sed -i "s/127.0.0.1\(\s*\)/127.0.0.1\\1test.hostname test /" '
                '/etc/hosts'],
                name='hostname-to-etc-hosts')

    @mock.patch('instack_undercloud.undercloud._run_command')
    def test_set_fqdn(self, mock_run_command):
        mock_run_command.side_effect = [None,
                                        'test-hostname.domain',
                                        'test-hostname.domain',
                                        None]
        self.conf.config(undercloud_hostname='test-hostname.domain')
        fake_hosts = io.StringIO(u'127.0.0.1 other-hostname\n')
        with mock.patch('instack_undercloud.undercloud.open',
                        return_value=fake_hosts, create=True):
            undercloud._check_hostname()
        mock_run_command.assert_called_with([
            'sudo', '/bin/bash', '-c',
            'sed -i "s/127.0.0.1\(\s*\)/'
            '127.0.0.1\\1test-hostname.domain test-hostname /" '
            '/etc/hosts'],
            name='hostname-to-etc-hosts')

    @mock.patch('instack_undercloud.undercloud._run_command')
    def test_set_not_fq(self, mock_run_command):
        mock_run_command.side_effect = [None,
                                        'test-hostname',
                                        'test-hostname',
                                        None]
        self.conf.config(undercloud_hostname='test-hostname')
        self.assertRaises(RuntimeError, undercloud._check_hostname)


class TestCheckMemory(BaseTestCase):
    @mock.patch('psutil.swap_memory')
    @mock.patch('psutil.virtual_memory')
    def test_sufficient_memory(self, mock_vm, mock_sm):
        mock_vm.return_value = mock.Mock()
        mock_vm.return_value.total = 8589934592
        mock_sm.return_value = mock.Mock()
        mock_sm.return_value.total = 0
        undercloud._check_memory()

    @mock.patch('psutil.swap_memory')
    @mock.patch('psutil.virtual_memory')
    def test_insufficient_memory(self, mock_vm, mock_sm):
        mock_vm.return_value = mock.Mock()
        mock_vm.return_value.total = 2071963648
        mock_sm.return_value = mock.Mock()
        mock_sm.return_value.total = 0
        self.assertRaises(RuntimeError, undercloud._check_memory)

    @mock.patch('psutil.swap_memory')
    @mock.patch('psutil.virtual_memory')
    def test_sufficient_swap(self, mock_vm, mock_sm):
        mock_vm.return_value = mock.Mock()
        mock_vm.return_value.total = 6442450944
        mock_sm.return_value = mock.Mock()
        mock_sm.return_value.total = 2147483648
        undercloud._check_memory()


class TestCheckSysctl(BaseTestCase):
    @mock.patch('os.path.isfile')
    def test_missing_options(self, mock_isfile):
        mock_isfile.return_value = False
        self.assertRaises(RuntimeError, undercloud._check_sysctl)

    @mock.patch('os.path.isfile')
    def test_available_option(self, mock_isfile):
        mock_isfile.return_value = True
        undercloud._check_sysctl()


class TestNoIPChange(BaseTestCase):
    @mock.patch('os.path.isfile', return_value=False)
    def test_new_install(self, mock_isfile):
        undercloud._validate_no_ip_change()

    @mock.patch('instack_undercloud.undercloud.open')
    @mock.patch('json.loads')
    @mock.patch('os.path.isfile', return_value=True)
    def test_update_matches(self, mock_isfile, mock_loads, mock_open):
        mock_members = [{'name': 'eth0'},
                        {'name': 'br-ctlplane',
                         'addresses': [{'ip_netmask': '192.168.24.1/24'}]
                         }
                        ]
        mock_config = {'network_config': mock_members}
        mock_loads.return_value = mock_config
        undercloud._validate_no_ip_change()

    @mock.patch('instack_undercloud.undercloud.open')
    @mock.patch('os.path.isfile', return_value=True)
    def test_update_empty(self, mock_isfile, mock_open):
        # This would be a way to disable os-net-config from running
        mock_open.side_effect = [
            mock.mock_open(read_data='').return_value,
        ]
        undercloud._validate_no_ip_change()

    @mock.patch('instack_undercloud.undercloud.open')
    @mock.patch('json.loads')
    @mock.patch('os.path.isfile', return_value=True)
    def test_update_mismatch(self, mock_isfile, mock_loads, mock_open):
        mock_members = [{'name': 'eth0'},
                        {'name': 'br-ctlplane',
                         'addresses': [{'ip_netmask': '192.168.0.1/24'}]
                         }
                        ]
        mock_config = {'network_config': mock_members}
        mock_loads.return_value = mock_config
        self.assertRaises(validator.FailedValidation,
                          undercloud._validate_no_ip_change)

    @mock.patch('instack_undercloud.undercloud.open')
    @mock.patch('json.loads')
    @mock.patch('os.path.isfile', return_value=True)
    def test_update_no_network(self, mock_isfile, mock_loads, mock_open):
        mock_members = [{'name': 'eth0'}]
        mock_config = {'network_config': mock_members}
        mock_loads.return_value = mock_config
        undercloud._validate_no_ip_change()


@mock.patch('os.path.isfile')
class TestPasswordsFileExists(BaseTestCase):
    def test_new_install(self, mock_isfile):
        mock_isfile.side_effect = [False]
        undercloud._validate_passwords_file()

    def test_update_exists(self, mock_isfile):
        mock_isfile.side_effect = [True, True]
        undercloud._validate_passwords_file()

    def test_update_missing(self, mock_isfile):
        mock_isfile.side_effect = [True, False]
        self.assertRaises(validator.FailedValidation,
                          undercloud._validate_passwords_file)


class TestGenerateEnvironment(BaseTestCase):
    def setUp(self):
        super(TestGenerateEnvironment, self).setUp()
        # Things that need to always be mocked out, but that the tests
        # don't want to care about.
        self.useFixture(fixtures.MockPatch(
            'instack_undercloud.undercloud._write_password_file'))
        self.useFixture(fixtures.MockPatch(
            'instack_undercloud.undercloud._load_config'))
        mock_isdir = fixtures.MockPatch('os.path.isdir')
        self.useFixture(mock_isdir)
        mock_isdir.mock.return_value = False
        # Some tests do care about this, but they can override the default
        # return value, and then the tests that don't care can ignore it.
        self.mock_distro = fixtures.MockPatch('platform.linux_distribution')
        self.useFixture(self.mock_distro)
        self.mock_distro.mock.return_value = [
            'Red Hat Enterprise Linux Server 7.1']

    @mock.patch('socket.gethostname')
    def test_hostname_set(self, mock_gethostname):
        fake_hostname = 'crazy-test-hostname-!@#$%12345'
        mock_gethostname.return_value = fake_hostname
        env = undercloud._generate_environment('.')
        self.assertEqual(fake_hostname, env['HOSTNAME'])

    def test_elements_path_input(self):
        test_path = '/test/elements/path'
        self.useFixture(fixtures.EnvironmentVariable('ELEMENTS_PATH',
                                                     test_path))
        env = undercloud._generate_environment('.')
        self.assertEqual(test_path, env['ELEMENTS_PATH'])

    def test_default_elements_path(self):
        env = undercloud._generate_environment('.')
        test_path = ('%s:%s:/usr/share/tripleo-image-elements:'
                     '/usr/share/diskimage-builder/elements' %
                     (os.path.join(os.getcwd(), 'tripleo-puppet-elements',
                                   'elements'),
                      './elements'))
        self.assertEqual(test_path, env['ELEMENTS_PATH'])

    def test_rhel7_distro(self):
        self.useFixture(fixtures.EnvironmentVariable('NODE_DIST', None))
        env = undercloud._generate_environment('.')
        self.assertEqual('rhel7', env['NODE_DIST'])
        self.assertEqual('./json-files/rhel-7-undercloud-packages.json',
                         env['JSONFILE'])
        self.assertEqual('disable', env['REG_METHOD'])
        self.assertEqual('1', env['REG_HALT_UNREGISTER'])

    def test_centos7_distro(self):
        self.useFixture(fixtures.EnvironmentVariable('NODE_DIST', None))
        self.mock_distro.mock.return_value = ['CentOS Linux release 7.1']
        env = undercloud._generate_environment('.')
        self.assertEqual('centos7', env['NODE_DIST'])
        self.assertEqual('./json-files/centos-7-undercloud-packages.json',
                         env['JSONFILE'])

    def test_fedora_distro(self):
        self.useFixture(fixtures.EnvironmentVariable('NODE_DIST', None))
        self.mock_distro.mock.return_value = ['Fedora Infinity + 1']
        self.assertRaises(RuntimeError, undercloud._generate_environment, '.')

    def test_other_distro(self):
        self.useFixture(fixtures.EnvironmentVariable('NODE_DIST', None))
        self.mock_distro.mock.return_value = ['Gentoo']
        self.assertRaises(RuntimeError, undercloud._generate_environment, '.')

    def test_opts_in_env(self):
        env = undercloud._generate_environment('.')
        # Just spot check, we don't want to replicate the entire opt list here
        self.assertEqual(env['INSPECTION_COLLECTORS'],
                         'default,extra-hardware,numa-topology,logs')
        self.assertEqual('192.168.24.1/24', env['PUBLIC_INTERFACE_IP'])
        self.assertEqual('192.168.24.1', env['LOCAL_IP'])
        # The list is generated from a set, so we can't rely on ordering.
        # Instead make sure that it looks like a valid list by parsing it.
        hw_types = json.loads(env['ENABLED_HARDWARE_TYPES'])
        self.assertEqual(sorted(hw_types), ['idrac', 'ilo', 'ipmi', 'redfish'])
        self.assertEqual(
            sorted(json.loads(env['ENABLED_BOOT_INTERFACES'])),
            ['ilo-pxe', 'pxe'])
        self.assertEqual(
            sorted(json.loads(env['ENABLED_POWER_INTERFACES'])),
            ['fake', 'idrac', 'ilo', 'ipmitool', 'redfish'])
        self.assertEqual(
            sorted(json.loads(env['ENABLED_MANAGEMENT_INTERFACES'])),
            ['fake', 'idrac', 'ilo', 'ipmitool', 'redfish'])
        self.assertEqual(
            sorted(json.loads(env['ENABLED_RAID_INTERFACES'])),
            ['idrac', 'no-raid'])
        self.assertEqual(
            sorted(json.loads(env['ENABLED_VENDOR_INTERFACES'])),
            ['idrac', 'ipmitool', 'no-vendor'])
        self.assertEqual(env['INSPECTION_NODE_NOT_FOUND_HOOK'], '')

    def test_all_hardware_types(self):
        self.conf.config(enabled_hardware_types=['ipmi', 'redfish', 'ilo',
                                                 'idrac', 'irmc', 'snmp',
                                                 'cisco-ucs-managed',
                                                 'cisco-ucs-standalone'])
        env = undercloud._generate_environment('.')
        # The list is generated from a set, so we can't rely on ordering.
        # Instead make sure that it looks like a valid list by parsing it.
        hw_types = json.loads(env['ENABLED_HARDWARE_TYPES'])
        self.assertEqual(sorted(hw_types), ['cisco-ucs-managed',
                                            'cisco-ucs-standalone',
                                            'idrac', 'ilo', 'ipmi', 'irmc',
                                            'redfish', 'snmp'])
        self.assertEqual(
            sorted(json.loads(env['ENABLED_BOOT_INTERFACES'])),
            ['ilo-pxe', 'irmc-pxe', 'pxe'])
        self.assertEqual(
            sorted(json.loads(env['ENABLED_POWER_INTERFACES'])),
            ['cimc', 'fake', 'idrac', 'ilo', 'ipmitool', 'irmc',
             'redfish', 'snmp', 'ucsm'])
        self.assertEqual(
            sorted(json.loads(env['ENABLED_MANAGEMENT_INTERFACES'])),
            ['cimc', 'fake', 'idrac', 'ilo', 'ipmitool', 'irmc',
             'redfish', 'ucsm'])
        self.assertEqual(
            sorted(json.loads(env['ENABLED_RAID_INTERFACES'])),
            ['idrac', 'no-raid'])
        self.assertEqual(
            sorted(json.loads(env['ENABLED_VENDOR_INTERFACES'])),
            ['idrac', 'ipmitool', 'no-vendor'])

    def test_enabled_discovery(self):
        self.conf.config(enable_node_discovery=True,
                         discovery_default_driver='foobar',
                         enabled_hardware_types=['ipmi', 'something'])
        env = undercloud._generate_environment('.')
        # The list is generated from a set, so we can't rely on ordering.
        # Instead make sure that it looks like a valid list by parsing it.
        hw_types = json.loads(env['ENABLED_HARDWARE_TYPES'])
        self.assertEqual(sorted(hw_types), ['foobar', 'ipmi', 'something'])

    def test_docker_registry_mirror(self):
        self.conf.config(docker_registry_mirror='http://foo/bar')
        env = undercloud._generate_environment('.')
        # Spot check one service
        self.assertEqual('http://foo/bar',
                         env['DOCKER_REGISTRY_MIRROR'])

    def test_docker_insecure_registries(self):
        self.conf.config(docker_insecure_registries=['http://foo/bar:8787'])
        env = undercloud._generate_environment('.')
        insecure_registries = json.loads(env['DOCKER_INSECURE_REGISTRIES'])
        # Spot check one service
        self.assertEqual(['http://foo/bar:8787'], insecure_registries)

    def test_generate_endpoints(self):
        env = undercloud._generate_environment('.')
        endpoint_vars = {k: v for (k, v) in env.items()
                         if k.startswith('UNDERCLOUD_ENDPOINT')}
        self.assertEqual(96, len(endpoint_vars))
        # Spot check one service
        self.assertEqual('https://192.168.24.2:13000',
                         env['UNDERCLOUD_ENDPOINT_KEYSTONE_PUBLIC'])
        self.assertEqual('http://192.168.24.3:5000',
                         env['UNDERCLOUD_ENDPOINT_KEYSTONE_INTERNAL'])
        self.assertEqual('http://192.168.24.3:35357',
                         env['UNDERCLOUD_ENDPOINT_KEYSTONE_ADMIN'])
        # Also check that the tenant id part is preserved
        self.assertEqual('https://192.168.24.2:13808/v1/AUTH_%(tenant_id)s',
                         env['UNDERCLOUD_ENDPOINT_SWIFT_PUBLIC'])

    def test_generate_endpoints_ssl_manual(self):
        self.conf.config(undercloud_service_certificate='test.pem')
        env = undercloud._generate_environment('.')
        # Spot check one service
        self.assertEqual('https://192.168.24.2:13000',
                         env['UNDERCLOUD_ENDPOINT_KEYSTONE_PUBLIC'])
        self.assertEqual('http://192.168.24.3:5000',
                         env['UNDERCLOUD_ENDPOINT_KEYSTONE_INTERNAL'])
        self.assertEqual('http://192.168.24.3:35357',
                         env['UNDERCLOUD_ENDPOINT_KEYSTONE_ADMIN'])
        self.assertEqual('https://192.168.24.2:443/keystone/v3',
                         env['UNDERCLOUD_ENDPOINT_KEYSTONE_UI_CONFIG_PUBLIC'])
        # Also check that the tenant id part is preserved
        self.assertEqual('https://192.168.24.2:13808/v1/AUTH_%(tenant_id)s',
                         env['UNDERCLOUD_ENDPOINT_SWIFT_PUBLIC'])

    def test_generate_endpoints_ssl_off(self):
        self.conf.config(generate_service_certificate=False)
        env = undercloud._generate_environment('.')
        # Spot check one service
        self.assertEqual('http://192.168.24.1:5000',
                         env['UNDERCLOUD_ENDPOINT_KEYSTONE_PUBLIC'])
        self.assertEqual('http://192.168.24.1:5000',
                         env['UNDERCLOUD_ENDPOINT_KEYSTONE_INTERNAL'])
        self.assertEqual('http://192.168.24.1:35357',
                         env['UNDERCLOUD_ENDPOINT_KEYSTONE_ADMIN'])
        # Also check that the tenant id part is preserved
        self.assertEqual('http://192.168.24.1:8080/v1/AUTH_%(tenant_id)s',
                         env['UNDERCLOUD_ENDPOINT_SWIFT_PUBLIC'])

    def test_absolute_cert_path(self):
        self.conf.config(undercloud_service_certificate='/home/stack/test.pem')
        env = undercloud._generate_environment('.')
        self.assertEqual('/home/stack/test.pem',
                         env['UNDERCLOUD_SERVICE_CERTIFICATE'])

    def test_relative_cert_path(self):
        [cert] = self.create_tempfiles([('test', 'foo')], '.pem')
        rel_cert = os.path.basename(cert)
        cert_path = os.path.dirname(cert)
        cur_dir = os.getcwd()
        try:
            os.chdir(cert_path)
            self.conf.config(undercloud_service_certificate=rel_cert)
            env = undercloud._generate_environment('.')
            self.assertEqual(os.path.join(os.getcwd(), rel_cert),
                             env['UNDERCLOUD_SERVICE_CERTIFICATE'])
        finally:
            os.chdir(cur_dir)

    def test_no_cert_path(self):
        env = undercloud._generate_environment('.')
        self.assertEqual('/etc/pki/tls/certs/undercloud-192.168.24.2.pem',
                         env['UNDERCLOUD_SERVICE_CERTIFICATE'])

    def test_no_ssl(self):
        self.conf.config(generate_service_certificate=False)
        env = undercloud._generate_environment('.')
        self.assertEqual('', env['UNDERCLOUD_SERVICE_CERTIFICATE'])

    def test_remove_dib_yum_repo_conf(self):
        self.useFixture(fixtures.EnvironmentVariable('DIB_YUM_REPO_CONF',
                                                     'rum_yepo.conf'))
        env = undercloud._generate_environment('.')
        self.assertNotIn(env, 'DIB_YUM_REPO_CONF')

    def test_inspection_ip_single_subnet(self):
        env = undercloud._generate_environment('.')
        reference = [{"tag": "ctlplane-subnet", "gateway": "192.168.24.1",
                      "ip_range": "192.168.24.100,192.168.24.120",
                      "netmask": "255.255.255.0"}]
        actual = json.loads(env['INSPECTION_SUBNETS'])
        self.assertEqual(reference, actual)

    def test_inspection_ip_multiple_subnets(self):
        self.conf.config(subnets=['subnet1', 'subnet2'])
        self.conf.config(local_subnet='subnet1')
        self.conf.register_opts(self.opts, group=self.grp1)
        self.conf.register_opts(self.opts, group=self.gtp2)
        self.conf.config(cidr='192.168.10.0/24', dhcp_start='192.168.10.10',
                         dhcp_end='192.168.10.99',
                         inspection_iprange='192.168.10.100,192.168.10.189',
                         gateway='192.168.10.254', masquerade=True,
                         group='subnet1')
        self.conf.config(cidr='192.168.20.0/24', dhcp_start='192.168.20.10',
                         dhcp_end='192.168.20.99',
                         inspection_iprange='192.168.20.100,192.168.20.189',
                         gateway='192.168.20.254', masquerade=True,
                         group='subnet2')
        env = undercloud._generate_environment('.')
        reference = [{"tag": "subnet1", "gateway": "192.168.10.254",
                      "ip_range": "192.168.10.100,192.168.10.189",
                      "netmask": "255.255.255.0"},
                     {"tag": "subnet2", "gateway": "192.168.20.254",
                      "ip_range": "192.168.20.100,192.168.20.189",
                      "netmask": "255.255.255.0"}]
        actual = json.loads(env['INSPECTION_SUBNETS'])
        self.assertEqual(reference, actual)

    def test_subnets_static_routes(self):
        self.conf.config(subnets=['ctlplane-subnet', 'subnet1', 'subnet2'])
        self.conf.register_opts(self.opts, group=self.grp1)
        self.conf.register_opts(self.opts, group=self.gtp2)
        self.conf.config(cidr='192.168.24.0/24',
                         dhcp_start='192.168.24.5', dhcp_end='192.168.24.24',
                         inspection_iprange='192.168.24.100,192.168.24.120',
                         gateway='192.168.24.1', masquerade=True,
                         group='ctlplane-subnet')
        self.conf.config(cidr='192.168.10.0/24', dhcp_start='192.168.10.10',
                         dhcp_end='192.168.10.99',
                         inspection_iprange='192.168.10.100,192.168.10.189',
                         gateway='192.168.10.254', masquerade=True,
                         group='subnet1')
        self.conf.config(cidr='192.168.20.0/24', dhcp_start='192.168.20.10',
                         dhcp_end='192.168.20.99',
                         inspection_iprange='192.168.20.100,192.168.20.189',
                         gateway='192.168.20.254', masquerade=True,
                         group='subnet2')
        env = undercloud._generate_environment('.')
        reference = [{"ip_netmask": "192.168.10.0/24",
                      "next_hop": "192.168.24.1"},
                     {"ip_netmask": "192.168.20.0/24",
                      "next_hop": "192.168.24.1"}]
        actual = json.loads(env['SUBNETS_STATIC_ROUTES'])
        self.assertEqual(reference, actual)

    def test_subnets_subnets_cidr_nat_rules(self):
        self.conf.config(subnets=['ctlplane-subnet', 'subnet1', 'subnet2'])
        self.conf.register_opts(self.opts, group=self.grp1)
        self.conf.register_opts(self.opts, group=self.gtp2)
        self.conf.config(cidr='192.168.24.0/24',
                         dhcp_start='192.168.24.5', dhcp_end='192.168.24.24',
                         inspection_iprange='192.168.24.100,192.168.24.120',
                         gateway='192.168.24.1', group='ctlplane-subnet')
        self.conf.config(cidr='192.168.10.0/24', dhcp_start='192.168.10.10',
                         dhcp_end='192.168.10.99',
                         inspection_iprange='192.168.10.100,192.168.10.189',
                         gateway='192.168.10.254', group='subnet1')
        self.conf.config(cidr='192.168.20.0/24', dhcp_start='192.168.20.10',
                         dhcp_end='192.168.20.99',
                         inspection_iprange='192.168.20.100,192.168.20.189',
                         gateway='192.168.20.254', group='subnet2')

        env = undercloud._generate_environment('.')
        reference = ('"140 destination ctlplane-subnet cidr nat": '
                     '{"chain": "FORWARD", "destination": "192.168.24.0/24", '
                     '"proto": "all", "action": "accept"}'
                     '\n  "140 source ctlplane-subnet cidr nat": '
                     '{"chain": "FORWARD", "source": "192.168.24.0/24", '
                     '"proto": "all", "action": "accept"}'
                     '\n  "140 destination subnet1 cidr nat": '
                     '{"chain": "FORWARD", "destination": "192.168.10.0/24", '
                     '"proto": "all", "action": "accept"}'
                     '\n  "140 source subnet1 cidr nat": '
                     '{"chain": "FORWARD", "source": "192.168.10.0/24", '
                     '"proto": "all", "action": "accept"}'
                     '\n  "140 destination subnet2 cidr nat": '
                     '{"chain": "FORWARD", "destination": "192.168.20.0/24", '
                     '"proto": "all", "action": "accept"}'
                     '\n  "140 source subnet2 cidr nat": '
                     '{"chain": "FORWARD", "source": "192.168.20.0/24", '
                     '"proto": "all", "action": "accept"}')
        actual = env['SUBNETS_CIDR_NAT_RULES']
        self.assertEqual(reference, actual)

    def test_masquerade_networks(self):
        self.conf.config(subnets=['ctlplane-subnet', 'subnet1', 'subnet2'])
        self.conf.register_opts(self.opts, group=self.grp1)
        self.conf.register_opts(self.opts, group=self.gtp2)
        self.conf.config(cidr='192.168.24.0/24',
                         dhcp_start='192.168.24.5', dhcp_end='192.168.24.24',
                         inspection_iprange='192.168.24.100,192.168.24.120',
                         gateway='192.168.24.1', masquerade=True,
                         group='ctlplane-subnet')
        self.conf.config(cidr='192.168.10.0/24', dhcp_start='192.168.10.10',
                         dhcp_end='192.168.10.99',
                         inspection_iprange='192.168.10.100,192.168.10.189',
                         gateway='192.168.10.254', masquerade=True,
                         group='subnet1')
        self.conf.config(cidr='192.168.20.0/24', dhcp_start='192.168.20.10',
                         dhcp_end='192.168.20.99',
                         inspection_iprange='192.168.20.100,192.168.20.189',
                         gateway='192.168.20.254', masquerade=True,
                         group='subnet2')

        env = undercloud._generate_environment('.')
        reference = ['192.168.24.0/24', '192.168.10.0/24', '192.168.20.0/24']
        actual = json.loads(env['MASQUERADE_NETWORKS'])
        self.assertEqual(reference, actual)


class TestWritePasswordFile(BaseTestCase):
    def test_normal(self):
        instack_env = {}
        undercloud._write_password_file(instack_env)
        test_parser = configparser.ConfigParser()
        test_parser.read(undercloud.PATHS.PASSWORD_PATH)
        self.assertTrue(test_parser.has_option('auth',
                                               'undercloud_db_password'))
        self.assertIn('UNDERCLOUD_DB_PASSWORD', instack_env)
        self.assertEqual(32,
                         len(instack_env['UNDERCLOUD_HEAT_ENCRYPTION_KEY']))

    def test_value_set(self):
        instack_env = {}
        self.conf.config(undercloud_db_password='test', group='auth')
        undercloud._write_password_file(instack_env)
        test_parser = configparser.ConfigParser()
        test_parser.read(undercloud.PATHS.PASSWORD_PATH)
        self.assertEqual(test_parser.get('auth', 'undercloud_db_password'),
                         'test')
        self.assertEqual(instack_env['UNDERCLOUD_DB_PASSWORD'], 'test')


class TestRunCommand(BaseTestCase):
    def test_run_command(self):
        output = undercloud._run_command(['echo', 'foo'])
        self.assertEqual('foo\n', output)

    def test_run_live_command(self):
        undercloud._run_live_command(['echo', 'bar'])
        self.assertIn('bar\n', self.logger.output)

    @mock.patch('subprocess.check_output')
    def test_run_command_fails(self, mock_check_output):
        fake_exc = subprocess.CalledProcessError(1, 'nothing', 'fake failure')
        mock_check_output.side_effect = fake_exc
        self.assertRaises(subprocess.CalledProcessError,
                          undercloud._run_command, ['nothing'])
        self.assertIn('nothing failed', self.logger.output)
        self.assertIn('fake failure', self.logger.output)

    @mock.patch('subprocess.check_output')
    def test_run_command_fails_with_name(self, mock_check_output):
        fake_exc = subprocess.CalledProcessError(1, 'nothing', 'fake failure')
        mock_check_output.side_effect = fake_exc
        self.assertRaises(subprocess.CalledProcessError,
                          undercloud._run_command, ['nothing'],
                          name='fake_name')
        self.assertIn('fake_name failed', self.logger.output)
        self.assertIn('fake failure', self.logger.output)

    def test_run_live_command_fails(self):
        exc = self.assertRaises(RuntimeError, undercloud._run_live_command,
                                ['ls', '/nonexistent/path'])
        self.assertIn('ls failed', str(exc))
        self.assertIn('ls', self.logger.output)

    def test_run_live_command_fails_name(self):
        exc = self.assertRaises(RuntimeError, undercloud._run_live_command,
                                ['ls', '/nonexistent/path'],
                                name='fake_name')
        self.assertIn('fake_name failed', str(exc))

    def test_run_command_env(self):
        env = {'FOO': 'foo'}
        output = undercloud._run_command(['env'], env)
        self.assertIn('FOO=foo', output)

    def test_run_live_command_env(self):
        env = {'BAR': 'bar'}
        undercloud._run_live_command(['env'], env)
        self.assertIn('BAR=bar', self.logger.output)


class TestRunTools(base.BaseTestCase):
    @mock.patch('instack_undercloud.undercloud._run_live_command')
    def test_run_instack(self, mock_run):
        instack_env = {'ELEMENTS_PATH': '.', 'JSONFILE': 'file.json'}
        args = ['sudo', '-E', 'instack', '-p', '.', '-j', 'file.json']
        undercloud._run_instack(instack_env)
        mock_run.assert_called_with(args, instack_env, 'instack')

    @mock.patch('instack_undercloud.undercloud._run_live_command')
    def test_run_os_refresh_config(self, mock_run):
        instack_env = {}
        args = ['sudo', 'os-refresh-config']
        undercloud._run_orc(instack_env)
        mock_run.assert_called_with(args, instack_env, 'os-refresh-config')


@mock.patch('instack_undercloud.undercloud._run_command')
class TestConfigureSshKeys(base.BaseTestCase):
    def test_ensure_user_identity(self, mock_run):
        id_path = os.path.expanduser('~/.ssh/id_rsa')
        undercloud._ensure_user_identity(id_path)
        mock_run.assert_called_with(['ssh-keygen', '-t', 'rsa', '-N', '',
                                    '-f', id_path])

    def _create_test_id(self):
        id_path = os.path.expanduser('~/.ssh/id_rsa')
        os.makedirs(os.path.expanduser('~/.ssh'))
        with open(id_path, 'w') as id_rsa:
            id_rsa.write('test private\n')
        with open(id_path + '.pub', 'w') as id_pub:
            id_pub.write('test public\n')
        return id_path

    def test_ensure_user_identity_exists(self, mock_run):
        id_path = self._create_test_id()
        undercloud._ensure_user_identity(id_path)
        self.assertFalse(mock_run.called)

    def _test_configure_ssh_keys(self, mock_eui, exists=True):
        id_path = self._create_test_id()
        mock_client_instance = mock.Mock()
        if not exists:
            get = mock_client_instance.keypairs.get
            get.side_effect = exceptions.NotFound('test')
        undercloud._configure_ssh_keys(mock_client_instance)
        mock_eui.assert_called_with(id_path)
        mock_client_instance.keypairs.get.assert_called_with('default')
        if not exists:
            mock_client_instance.keypairs.create.assert_called_with(
                'default', 'test public')

    @mock.patch('instack_undercloud.undercloud._ensure_user_identity')
    def test_configure_ssh_keys_exists(self, mock_eui, _):
        self._test_configure_ssh_keys(mock_eui)

    @mock.patch('instack_undercloud.undercloud._ensure_user_identity')
    def test_configure_ssh_keys_missing(self, mock_eui, _):
        self._test_configure_ssh_keys(mock_eui, False)


class TestPostConfig(BaseTestCase):
    @mock.patch('os_client_config.make_client')
    @mock.patch('instack_undercloud.undercloud._migrate_to_convergence')
    @mock.patch('instack_undercloud.undercloud._ensure_node_resource_classes')
    @mock.patch(
      'instack_undercloud.undercloud._config_neutron_segments_and_subnets')
    @mock.patch('instack_undercloud.undercloud._ensure_neutron_network')
    @mock.patch('instack_undercloud.undercloud._member_role_exists')
    @mock.patch('instack_undercloud.undercloud._get_session')
    @mock.patch('ironicclient.client.get_client', autospec=True)
    @mock.patch('novaclient.client.Client', autospec=True)
    @mock.patch('swiftclient.client.Connection', autospec=True)
    @mock.patch('mistralclient.api.client.client', autospec=True)
    @mock.patch('instack_undercloud.undercloud._delete_default_flavors')
    @mock.patch('instack_undercloud.undercloud._copy_stackrc')
    @mock.patch('instack_undercloud.undercloud._get_auth_values')
    @mock.patch('instack_undercloud.undercloud._configure_ssh_keys')
    @mock.patch('instack_undercloud.undercloud._ensure_flavor')
    @mock.patch('instack_undercloud.undercloud._post_config_mistral')
    def test_post_config(self, mock_post_config_mistral, mock_ensure_flavor,
                         mock_configure_ssh_keys, mock_get_auth_values,
                         mock_copy_stackrc, mock_delete, mock_mistral_client,
                         mock_swift_client, mock_nova_client, mock_ir_client,
                         mock_get_session, mock_member_role_exists,
                         mock_ensure_neutron_network,
                         mock_config_neutron_segments_and_subnets,
                         mock_resource_classes, mock_migrate_to_convergence,
                         mock_make_client):
        instack_env = {
            'UNDERCLOUD_ENDPOINT_MISTRAL_PUBLIC':
                'http://192.168.24.1:8989/v2',
        }
        mock_get_auth_values.return_value = ('aturing', '3nigma', 'hut8',
                                             'http://bletchley:5000/')
        mock_instance_nova = mock.Mock()
        mock_nova_client.return_value = mock_instance_nova
        mock_get_session.return_value = mock.MagicMock()
        mock_instance_swift = mock.Mock()
        mock_swift_client.return_value = mock_instance_swift
        mock_instance_mistral = mock.Mock()
        mock_mistral_client.return_value = mock_instance_mistral
        mock_instance_ironic = mock_ir_client.return_value
        flavors = [mock.Mock(spec=['name']),
                   mock.Mock(spec=['name'])]
        # The mock library treats "name" attribute differently, and we cannot
        # pass it through __init__
        flavors[0].name = 'baremetal'
        flavors[1].name = 'ceph-storage'
        mock_instance_nova.flavors.list.return_value = flavors
        mock_heat = mock.Mock()
        mock_make_client.return_value = mock_heat

        undercloud._post_config(instack_env, True)
        mock_nova_client.assert_called_with(
            2, session=mock_get_session.return_value)
        self.assertTrue(mock_copy_stackrc.called)
        mock_configure_ssh_keys.assert_called_with(mock_instance_nova)
        calls = [mock.call(mock_instance_nova, flavors[0], 'baremetal', None),
                 mock.call(mock_instance_nova, None, 'control', 'control'),
                 mock.call(mock_instance_nova, None, 'compute', 'compute'),
                 mock.call(mock_instance_nova, flavors[1],
                           'ceph-storage', 'ceph-storage'),
                 mock.call(mock_instance_nova, None,
                           'block-storage', 'block-storage'),
                 mock.call(mock_instance_nova, None,
                           'swift-storage', 'swift-storage'),
                 ]
        mock_ensure_flavor.assert_has_calls(calls)
        mock_resource_classes.assert_called_once_with(mock_instance_ironic)
        mock_post_config_mistral.assert_called_once_with(
            instack_env, mock_instance_mistral, mock_instance_swift)
        mock_migrate_to_convergence.assert_called_once_with(mock_heat)

    @mock.patch('instack_undercloud.undercloud._get_auth_values')
    @mock.patch('instack_undercloud.undercloud._get_session')
    @mock.patch('mistralclient.api.client.client', autospec=True)
    def test_run_validation_groups_success(self, mock_mistral_client,
                                           mock_get_session,
                                           mock_auth_values):
        mock_mistral = mock.Mock()
        mock_mistral_client.return_value = mock_mistral
        mock_mistral.environments.list.return_value = []
        mock_mistral.executions.get.return_value = mock.Mock(state="SUCCESS")
        mock_get_session.return_value = mock.MagicMock()
        undercloud._run_validation_groups(["post-upgrade"])
        mock_mistral.executions.create.assert_called_once_with(
            'tripleo.validations.v1.run_groups',
            workflow_input={
                'group_names': ['post-upgrade'],
            }
        )

    @mock.patch('instack_undercloud.undercloud._get_auth_values')
    @mock.patch('instack_undercloud.undercloud._get_session')
    @mock.patch('mistralclient.api.client.client', autospec=True)
    @mock.patch('time.strptime')
    def test_run_validation_groups_fail(self, mock_strptime,
                                        mock_mistral_client, mock_get_session,
                                        mock_auth_values):
        mock_mistral = mock.Mock()
        mock_mistral_client.return_value = mock_mistral
        mock_mistral.environments.list.return_value = []
        mock_mistral.executions.get.return_value = mock.Mock(state="FAIL")
        mock_mistral.executions.get_output.return_value = "ERROR!"
        mock_mistral.executions.get.id = "1234"
        mock_mistral.action_executions.list.return_value = []
        mock_strptime.return_value = time.mktime(time.localtime())
        mock_get_session.return_value = mock.MagicMock()
        self.assertRaises(
            RuntimeError, undercloud._run_validation_groups, ["post-upgrade"],
            "", 360, True)

    @mock.patch('instack_undercloud.undercloud._get_auth_values')
    @mock.patch('instack_undercloud.undercloud._get_session')
    @mock.patch('mistralclient.api.client.client', autospec=True)
    @mock.patch('time.strptime')
    def test_run_validation_groups_timeout(self, mock_strptime,
                                           mock_mistral_client,
                                           mock_get_session, mock_auth_values):
        mock_mistral = mock.Mock()
        mock_mistral_client.return_value = mock_mistral
        mock_mistral.environments.list.return_value = []
        mock_mistral.executions.get.id = "1234"
        mock_mistral.action_executions.list.return_value = []
        mock_get_session.return_value = mock.MagicMock()
        mock_time = mock.MagicMock()
        mock_time.return_value = time.mktime(time.localtime())
        mock_strptime.return_value = time.mktime(time.localtime())
        with mock.patch('time.time', mock_time):
            self.assertRaisesRegexp(RuntimeError, ("TIMEOUT waiting for "
                                    "execution"),
                                    undercloud._run_validation_groups,
                                    ["post-upgrade"], "", -1, True)

    def test_create_default_plan(self):
        mock_mistral = mock.Mock()
        mock_mistral.environments.list.return_value = []
        mock_mistral.executions.get.return_value = mock.Mock(state="SUCCESS")

        undercloud._create_default_plan(mock_mistral, [])
        mock_mistral.executions.create.assert_called_once_with(
            'tripleo.plan_management.v1.create_deployment_plan',
            workflow_input={
                'container': 'overcloud',
                'use_default_templates': True,
            }
        )

    def test_create_default_plan_existing(self):
        mock_mistral = mock.Mock()
        undercloud._create_default_plan(mock_mistral, ['overcloud'])
        mock_mistral.executions.create.assert_not_called()

    def test_create_config_environment(self):
        mock_mistral = mock.Mock()
        mock_mistral.environments.get.side_effect = (
            ks_exceptions.NotFound)

        env = {
            "UNDERCLOUD_DB_PASSWORD": "root-db-pass",
            "UNDERCLOUD_CEILOMETER_SNMPD_PASSWORD": "snmpd-pass"
        }

        json_string = {
            "undercloud_db_password": "root-db-pass",
            "undercloud_ceilometer_snmpd_password": "snmpd-pass"
        }

        undercloud._create_mistral_config_environment(json.loads(
            json.dumps(env, sort_keys=True)), mock_mistral)

        mock_mistral.environments.create.assert_called_once_with(
            name='tripleo.undercloud-config',
            description='Undercloud configuration parameters',
            variables=json.dumps(json_string, sort_keys=True))

    def test_create_config_environment_existing(self):
        mock_mistral = mock.Mock()
        environment = collections.namedtuple('environment',
                                             ['name', 'variables'])

        json_string = {
            "undercloud_db_password": "root-db-pass",
            "undercloud_ceilometer_snmpd_password": "snmpd-pass"
        }

        mock_mistral.environments.get.return_value = environment(
            name='tripleo.undercloud-config',
            variables=json.loads(json.dumps(json_string, sort_keys=True))
           )

        env = {
            "UNDERCLOUD_CEILOMETER_SNMPD_PASSWORD": "snmpd-pass",
            "UNDERCLOUD_DB_PASSWORD": "root-db-pass"
        }

        undercloud._create_mistral_config_environment(json.loads(
            json.dumps(env, sort_keys=True)), mock_mistral)
        mock_mistral.executions.create.assert_not_called()

    def test_prepare_ssh_environment(self):
        mock_mistral = mock.Mock()
        undercloud._prepare_ssh_environment(mock_mistral)
        mock_mistral.executions.create.assert_called_once_with(
            'tripleo.validations.v1.copy_ssh_key')

    @mock.patch('time.sleep')
    def test_create_default_plan_timeout(self, mock_sleep):
        mock_mistral = mock.Mock()
        mock_mistral.executions.get.return_value = mock.Mock(state="RUNNING")

        self.assertRaises(
            RuntimeError,
            undercloud._create_default_plan, mock_mistral, [], timeout=0)

    @mock.patch('time.strptime')
    def test_create_default_plan_failed(self, mock_strptime):
        mock_mistral = mock.Mock()
        mock_mistral.executions.get.return_value = mock.Mock(state="ERROR")
        mock_mistral.action_executions.list.return_value = []
        mock_strptime.return_value = time.mktime(time.localtime())
        self.assertRaises(
            RuntimeError,
            undercloud._create_default_plan, mock_mistral, [])

    @mock.patch('instack_undercloud.undercloud._run_command')
    def test_copy_stackrc(self, mock_run):
        undercloud._copy_stackrc()
        calls = [mock.call(['sudo', 'cp', '/root/stackrc', mock.ANY],
                           name='Copy stackrc'),
                 mock.call(['sudo', 'chown', mock.ANY, mock.ANY],
                           name='Chown stackrc'),
                 ]
        mock_run.assert_has_calls(calls)

    def _mock_ksclient_roles(self, mock_auth_values, mock_ksdiscover, roles):
        mock_auth_values.return_value = ('user', 'password',
                                         'project', 'http://test:123')
        mock_discover = mock.Mock()
        mock_ksdiscover.return_value = mock_discover
        mock_client = mock.Mock()
        mock_roles = mock.Mock()
        mock_role_list = []
        for role in roles:
            mock_role = mock.Mock()
            mock_role.name = role
            mock_role_list.append(mock_role)
        mock_roles.list.return_value = mock_role_list
        mock_client.roles = mock_roles
        mock_discover.create_client.return_value = mock_client

        mock_client.version = 'v3'

        mock_project_list = [mock.Mock(), mock.Mock()]
        mock_project_list[0].name = 'admin'
        mock_project_list[0].id = 'admin-id'
        mock_project_list[1].name = 'service'
        mock_project_list[1].id = 'service-id'
        mock_client.projects.list.return_value = mock_project_list

        mock_user_list = [mock.Mock(), mock.Mock()]
        mock_user_list[0].name = 'admin'
        mock_user_list[1].name = 'nova'
        mock_client.users.list.return_value = mock_user_list
        return mock_client

    @mock.patch('keystoneclient.discover.Discover')
    @mock.patch('instack_undercloud.undercloud._get_auth_values')
    @mock.patch('os.path.isfile')
    def test_member_role_exists(self, mock_isfile, mock_auth_values,
                                mock_ksdiscover):
        mock_isfile.return_value = True
        mock_client = self._mock_ksclient_roles(mock_auth_values,
                                                mock_ksdiscover,
                                                ['admin'])
        undercloud._member_role_exists()
        self.assertFalse(mock_client.projects.list.called)

    @mock.patch('keystoneclient.discover.Discover')
    @mock.patch('instack_undercloud.undercloud._get_auth_values')
    @mock.patch('os.path.isfile')
    def test_member_role_exists_true(self, mock_isfile,
                                     mock_auth_values, mock_ksdiscover):
        mock_isfile.return_value = True
        mock_client = self._mock_ksclient_roles(mock_auth_values,
                                                mock_ksdiscover,
                                                ['admin', '_member_'])
        undercloud._member_role_exists()
        mock_user = mock_client.users.list.return_value[0]
        mock_role = mock_client.roles.list.return_value[1]
        mock_client.roles.grant.assert_called_once_with(
            mock_role, user=mock_user, project='admin-id')

    @mock.patch('keystoneclient.discover.Discover')
    @mock.patch('instack_undercloud.undercloud._get_auth_values')
    @mock.patch('os.path.isfile')
    def test_has_member_role(self, mock_isfile, mock_auth_values,
                             mock_ksdiscover):
        mock_isfile.return_value = True
        mock_client = self._mock_ksclient_roles(mock_auth_values,
                                                mock_ksdiscover,
                                                ['admin', '_member_'])
        fake_exception = ks_exceptions.http.Conflict('test')
        mock_client.roles.grant.side_effect = fake_exception
        undercloud._member_role_exists()
        mock_user = mock_client.users.list.return_value[0]
        mock_role = mock_client.roles.list.return_value[1]
        mock_client.roles.grant.assert_called_once_with(
            mock_role, user=mock_user, project='admin-id')

    def _create_flavor_mocks(self):
        mock_nova = mock.Mock()
        mock_nova.flavors.create = mock.Mock()
        mock_flavor = mock.Mock()
        mock_nova.flavors.create.return_value = mock_flavor
        mock_flavor.set_keys = mock.Mock()
        return mock_nova, mock_flavor

    def test_ensure_flavor_no_profile(self):
        mock_nova, mock_flavor = self._create_flavor_mocks()
        undercloud._ensure_flavor(mock_nova, None, 'test')
        mock_nova.flavors.create.assert_called_with('test', 4096, 1, 40)
        keys = {'capabilities:boot_option': 'local',
                'resources:CUSTOM_BAREMETAL': '1',
                'resources:DISK_GB': '0',
                'resources:MEMORY_MB': '0',
                'resources:VCPU': '0'}
        mock_flavor.set_keys.assert_called_with(keys)

    def test_ensure_flavor_profile(self):
        mock_nova, mock_flavor = self._create_flavor_mocks()
        undercloud._ensure_flavor(mock_nova, None, 'test', 'test')
        mock_nova.flavors.create.assert_called_with('test', 4096, 1, 40)
        keys = {'capabilities:boot_option': 'local',
                'capabilities:profile': 'test',
                'resources:CUSTOM_BAREMETAL': '1',
                'resources:DISK_GB': '0',
                'resources:MEMORY_MB': '0',
                'resources:VCPU': '0'}
        mock_flavor.set_keys.assert_called_with(keys)

    def test_ensure_flavor_exists(self):
        mock_nova, mock_flavor = self._create_flavor_mocks()
        mock_nova.flavors.create.side_effect = exceptions.Conflict(None)
        flavor = mock.Mock(spec=['name', 'get_keys', 'set_keys'])
        flavor.get_keys.return_value = {'foo': 'bar'}

        undercloud._ensure_flavor(mock_nova, flavor, 'test')

        keys = {'foo': 'bar',
                'resources:CUSTOM_BAREMETAL': '1',
                'resources:DISK_GB': '0',
                'resources:MEMORY_MB': '0',
                'resources:VCPU': '0'}
        flavor.set_keys.assert_called_with(keys)
        mock_nova.flavors.create.assert_not_called()

    @mock.patch.object(undercloud.LOG, 'warning', autospec=True)
    def test_ensure_flavor_exists_conflicting_rc(self, mock_warn):
        mock_nova, mock_flavor = self._create_flavor_mocks()
        mock_nova.flavors.create.side_effect = exceptions.Conflict(None)
        flavor = mock.Mock(spec=['name', 'get_keys', 'set_keys'])
        flavor.get_keys.return_value = {'foo': 'bar',
                                        'resources:CUSTOM_FOO': '42'}

        undercloud._ensure_flavor(mock_nova, flavor, 'test')

        flavor.set_keys.assert_not_called()
        mock_warn.assert_called_once_with(mock.ANY, flavor.name,
                                          'resources:CUSTOM_FOO')
        mock_nova.flavors.create.assert_not_called()

    def test_ensure_node_resource_classes(self):
        nodes = [mock.Mock(uuid='1', resource_class=None),
                 mock.Mock(uuid='2', resource_class='foobar')]
        ironic_mock = mock.Mock()
        ironic_mock.node.list.return_value = nodes

        undercloud._ensure_node_resource_classes(ironic_mock)

        ironic_mock.node.update.assert_called_once_with(
            '1', [{'path': '/resource_class', 'op': 'add',
                   'value': 'baremetal'}])

    @mock.patch('instack_undercloud.undercloud._run_command')
    def test_migrate_to_convergence(self, mock_run_command):
        stacks = [mock.Mock(id='1'), mock.Mock(id='2')]
        mock_heat = mock.Mock()
        mock_heat.stacks.list.return_value = stacks
        undercloud._migrate_to_convergence(mock_heat)
        self.assertEqual([mock.call(['sudo', '-E', 'heat-manage',
                                     'migrate_convergence_1', '1'],
                                    name='heat-manage'),
                          mock.call(['sudo', '-E', 'heat-manage',
                                     'migrate_convergence_1', '2'],
                                    name='heat-manage')],
                         mock_run_command.mock_calls)

    @mock.patch('instack_undercloud.undercloud._run_command')
    def test_migrate_to_convergence_no_stacks(self, mock_run_command):
        stacks = []
        mock_heat = mock.Mock()
        mock_heat.stacks.list.return_value = stacks
        undercloud._migrate_to_convergence(mock_heat)
        mock_run_command.assert_not_called()

    @mock.patch('instack_undercloud.undercloud._extract_from_stackrc')
    @mock.patch('instack_undercloud.undercloud._run_command')
    def test_get_auth_values(self, mock_run, mock_extract):
        mock_run.return_value = '3nigma'
        mock_extract.side_effect = ['aturing', 'hut8',
                                    'http://bletchley:5000/v2.0']
        values = undercloud._get_auth_values()
        expected = ('aturing', '3nigma', 'hut8', 'http://bletchley:5000/v2.0')
        self.assertEqual(expected, values)

    def test_delete_default_flavors(self):
        class FakeFlavor(object):
            def __init__(self, id_, name):
                self.id = id_
                self.name = name
        mock_instance = mock.Mock()
        mock_flavors = [FakeFlavor('f00', 'foo'),
                        FakeFlavor('8ar', 'm1.large')]
        mock_instance.flavors.list.return_value = mock_flavors
        undercloud._delete_default_flavors(mock_instance)
        mock_instance.flavors.delete.assert_called_once_with('8ar')

    @mock.patch('os.path.isfile', return_value=True)
    @mock.patch('os.listdir')
    @mock.patch('instack_undercloud.undercloud._create_mistral_config_'
                'environment')
    @mock.patch('instack_undercloud.undercloud._create_default_plan')
    @mock.patch('instack_undercloud.undercloud._upload_validations_to_swift')
    def test_post_config_mistral(self, mock_upload, mock_create, mock_cmce,
                                 mock_listdir, mock_isfile):
        instack_env = {}
        mock_mistral = mock.Mock()
        mock_swift = mock.Mock()
        mock_swift.get_account.return_value = [None, [{'name': 'hut8'}]]

        mock_workbooks = [mock.Mock() for m in range(2)]
        mock_workbooks[0].name = 'foo'
        mock_workbooks[1].name = 'tripleo.bar'
        mock_mistral.workbooks.list.return_value = mock_workbooks
        mock_triggers = [mock.Mock() for m in range(2)]
        mock_triggers[0].name = 'dont_delete_me'
        mock_triggers[0].workflow_name = 'tripleo.foo'
        mock_triggers[1].name = 'delete_me'
        mock_triggers[1].workflow_name = 'tripleo.bar'
        mock_mistral.cron_triggers.list.return_value = mock_triggers
        mock_workflows = [mock.Mock() for m in range(2)]
        mock_workflows[0].name = 'tripleo.foo'
        mock_workflows[1].name = 'tripleo.bar'
        mock_workflows[0].tags = []
        mock_workflows[1].tags = ['tripleo-common-managed', ]
        mock_mistral.workflows.list.return_value = mock_workflows

        mock_listdir.return_value = ['foo.yaml', 'bar.yaml']
        undercloud._post_config_mistral(instack_env, mock_mistral, mock_swift)
        self.assertEqual([mock.call('tripleo.bar')],
                         mock_mistral.workbooks.delete.mock_calls)
        self.assertEqual([mock.call('tripleo.bar')],
                         mock_mistral.workflows.delete.mock_calls)
        self.assertEqual([mock.call('delete_me')],
                         mock_mistral.cron_triggers.delete.mock_calls)
        self.assertEqual([mock.call(undercloud.PATHS.WORKBOOK_PATH +
                                    '/foo.yaml'),
                         mock.call(undercloud.PATHS.WORKBOOK_PATH +
                                   '/bar.yaml')],
                         mock_mistral.workbooks.create.mock_calls)
        mock_cmce.assert_called_once_with(instack_env, mock_mistral)
        mock_create.assert_called_once_with(mock_mistral, ['hut8'])
        mock_upload.assert_called_once_with(mock_mistral)

    def _neutron_mocks(self):
        mock_sdk = mock.MagicMock()
        mock_sdk.network.create_network = mock.Mock()
        mock_sdk.network.create_segment = mock.Mock()
        mock_sdk.network.update_segment = mock.Mock()
        mock_sdk.network.delete_segment = mock.Mock()
        mock_sdk.network.create_subnet = mock.Mock()
        mock_sdk.network.update_subnet = mock.Mock()
        return mock_sdk

    def test_network_create(self):
        mock_sdk = self._neutron_mocks()
        mock_sdk.network.networks.return_value = iter([])
        segment_mock = mock.Mock()
        mock_sdk.network.segments.return_value = iter([segment_mock])
        undercloud._ensure_neutron_network(mock_sdk)
        mock_sdk.network.create_network.assert_called_with(
          name='ctlplane', provider_network_type='flat',
          provider_physical_network='ctlplane', mtu=1500)

    def test_delete_default_segment(self):
        mock_sdk = self._neutron_mocks()
        mock_sdk.network.networks.return_value = iter([])
        segment_mock = mock.Mock()
        mock_sdk.network.segments.return_value = iter([segment_mock])
        undercloud._ensure_neutron_network(mock_sdk)
        mock_sdk.network.delete_segment.assert_called_with(
          segment_mock.id)

    def test_network_exists(self):
        mock_sdk = self._neutron_mocks()
        mock_sdk.network.networks.return_value = iter(['ctlplane'])
        undercloud._ensure_neutron_network(mock_sdk)
        mock_sdk.network.create_network.assert_not_called()

    def test_segment_create(self):
        mock_sdk = self._neutron_mocks()
        undercloud._neutron_segment_create(mock_sdk, 'ctlplane-subnet',
                                           'network_id', 'ctlplane')
        mock_sdk.network.create_segment.assert_called_with(
          name='ctlplane-subnet', network_id='network_id',
          physical_network='ctlplane', network_type='flat')

    def test_segment_update(self):
        mock_sdk = self._neutron_mocks()
        undercloud._neutron_segment_update(mock_sdk,
                                           'network_id', 'ctlplane-subnet')
        mock_sdk.network.update_segment.assert_called_with(
            'network_id', name='ctlplane-subnet')

    def test_subnet_create(self):
        mock_sdk = self._neutron_mocks()
        host_routes = [{'destination': '169.254.169.254/32',
                        'nexthop': '192.168.24.1'}]
        allocation_pool = [{'start': '192.168.24.5', 'end': '192.168.24.24'}]
        undercloud._neutron_subnet_create(mock_sdk, 'network_id',
                                          '192.168.24.0/24', '192.168.24.1',
                                          host_routes, allocation_pool,
                                          'ctlplane-subnet', 'segment_id')
        mock_sdk.network.create_subnet.assert_called_with(
          name='ctlplane-subnet', cidr='192.168.24.0/24',
          gateway_ip='192.168.24.1', host_routes=host_routes, enable_dhcp=True,
          ip_version='4', allocation_pools=allocation_pool,
          network_id='network_id', segment_id='segment_id')

    def test_subnet_update(self):
        mock_sdk = self._neutron_mocks()
        host_routes = [{'destination': '169.254.169.254/32',
                        'nexthop': '192.168.24.1'}]
        allocation_pool = [{'start': '192.168.24.5', 'end': '192.168.24.24'}]
        undercloud._neutron_subnet_update(mock_sdk, 'subnet_id',
                                          '192.168.24.1', host_routes,
                                          allocation_pool, 'ctlplane-subnet')
        mock_sdk.network.update_subnet.assert_called_with(
          'subnet_id', name='ctlplane-subnet', gateway_ip='192.168.24.1',
          host_routes=host_routes, allocation_pools=allocation_pool)

    @mock.patch('instack_undercloud.undercloud._neutron_subnet_update')
    @mock.patch('instack_undercloud.undercloud._get_subnet')
    def test_no_neutron_segments_if_pre_segments_undercloud(
      self, mock_get_subnet, mock_neutron_subnet_update):
        mock_sdk = self._neutron_mocks()
        mock_subnet = mock.Mock()
        mock_subnet.segment_id = None
        mock_get_subnet.return_value = mock_subnet
        undercloud._config_neutron_segments_and_subnets(mock_sdk,
                                                        'ctlplane_id')
        mock_sdk.network.create_segment.assert_not_called()
        mock_sdk.network.update_segment.assert_not_called()
        mock_neutron_subnet_update.called_once()

    @mock.patch('instack_undercloud.undercloud._neutron_segment_create')
    @mock.patch('instack_undercloud.undercloud._neutron_subnet_create')
    @mock.patch('instack_undercloud.undercloud._get_segment')
    @mock.patch('instack_undercloud.undercloud._get_subnet')
    def test_segment_and_subnet_create(self, mock_get_subnet, mock_get_segment,
                                       mock_neutron_subnet_create,
                                       mock_neutron_segment_create):
        mock_sdk = self._neutron_mocks()
        mock_get_subnet.return_value = None
        mock_get_segment.return_value = None
        undercloud._config_neutron_segments_and_subnets(mock_sdk,
                                                        'ctlplane_id')
        mock_neutron_segment_create.assert_called_with(
          mock_sdk, 'ctlplane-subnet', 'ctlplane_id', 'ctlplane')
        host_routes = [{'destination': '169.254.169.254/32',
                        'nexthop': '192.168.24.1'}]
        allocation_pool = [{'start': '192.168.24.5', 'end': '192.168.24.24'}]
        mock_neutron_subnet_create.assert_called_with(
          mock_sdk, 'ctlplane_id', '192.168.24.0/24', '192.168.24.1',
          host_routes, allocation_pool, 'ctlplane-subnet',
          mock_neutron_segment_create().id)

    @mock.patch('instack_undercloud.undercloud._neutron_segment_update')
    @mock.patch('instack_undercloud.undercloud._neutron_subnet_update')
    @mock.patch('instack_undercloud.undercloud._get_segment')
    @mock.patch('instack_undercloud.undercloud._get_subnet')
    def test_segment_and_subnet_update(self, mock_get_subnet, mock_get_segment,
                                       mock_neutron_subnet_update,
                                       mock_neutron_segment_update):
        mock_sdk = self._neutron_mocks()
        mock_subnet = mock.Mock()
        mock_subnet.id = 'subnet_id'
        mock_subnet.segment_id = 'segment_id'
        mock_get_subnet.return_value = mock_subnet
        mock_segment = mock.Mock()
        mock_get_segment.return_value = mock_segment
        mock_segment.id = 'segment_id'
        undercloud._config_neutron_segments_and_subnets(mock_sdk,
                                                        'ctlplane_id')
        mock_neutron_segment_update.assert_called_with(
          mock_sdk, mock_subnet.segment_id, 'ctlplane-subnet')
        host_routes = [{'destination': '169.254.169.254/32',
                        'nexthop': '192.168.24.1'}]
        allocation_pool = [{'start': '192.168.24.5', 'end': '192.168.24.24'}]
        mock_neutron_subnet_update.assert_called_with(
          mock_sdk, 'subnet_id', '192.168.24.1', host_routes,
          allocation_pool, 'ctlplane-subnet')

    @mock.patch('instack_undercloud.undercloud._get_segment')
    @mock.patch('instack_undercloud.undercloud._get_subnet')
    def test_local_subnet_cidr_conflict(self, mock_get_subnet,
                                        mock_get_segment):
        mock_sdk = self._neutron_mocks()
        mock_sdk = self._neutron_mocks()
        mock_subnet = mock.Mock()
        mock_subnet.id = 'subnet_id'
        mock_subnet.segment_id = 'existing_segment_id'
        mock_get_subnet.return_value = mock_subnet
        mock_segment = mock.Mock()
        mock_get_segment.return_value = mock_segment
        mock_segment.id = 'segment_id'
        self.assertRaises(
          RuntimeError,
          undercloud._config_neutron_segments_and_subnets, [mock_sdk],
          ['ctlplane_id'])


class TestUpgradeFact(base.BaseTestCase):
    @mock.patch('instack_undercloud.undercloud._run_command')
    @mock.patch('os.path.dirname')
    @mock.patch('os.path.exists')
    @mock.patch.object(tempfile, 'mkstemp', return_value=(1, '/tmp/file'))
    def test_upgrade_fact(self, mock_mkstemp, mock_exists, mock_dirname,
                          mock_run):
        fact_path = '/etc/facter/facts.d/undercloud_upgrade.txt'
        mock_dirname.return_value = '/etc/facter/facts.d'
        mock_exists.side_effect = [False, True]

        with mock.patch('instack_undercloud.undercloud.open') as mock_open:
            undercloud._handle_upgrade_fact(True)
            mock_open.assert_called_with('/tmp/file', 'w')

        run_calls = [
            mock.call(['sudo', 'mkdir', '-p', '/etc/facter/facts.d']),
            mock.call(['sudo', 'mv', '/tmp/file', fact_path]),
            mock.call(['sudo', 'chmod', '0644', fact_path])
        ]
        mock_run.assert_has_calls(run_calls)
        self.assertEqual(mock_run.call_count, 3)

    @mock.patch('instack_undercloud.undercloud._run_command')
    @mock.patch('os.path.dirname')
    @mock.patch('os.path.exists')
    @mock.patch.object(tempfile, 'mkstemp', return_value=(1, '/tmp/file'))
    def test_upgrade_fact_install(self, mock_mkstemp, mock_exists,
                                  mock_dirname, mock_run):
        mock_dirname.return_value = '/etc/facter/facts.d'
        mock_exists.return_value = False

        with mock.patch('instack_undercloud.undercloud.open') as mock_open:
            undercloud._handle_upgrade_fact(False)
            mock_open.assert_not_called()

        mock_run.assert_not_called()

    @mock.patch('instack_undercloud.undercloud._run_command')
    @mock.patch('os.path.dirname')
    @mock.patch('os.path.exists')
    @mock.patch.object(tempfile, 'mkstemp', return_value=(1, '/tmp/file'))
    def test_upgrade_fact_upgrade_after_install(self, mock_mkstemp,
                                                mock_exists, mock_dirname,
                                                mock_run):
        fact_path = '/etc/facter/facts.d/undercloud_upgrade.txt'
        mock_dirname.return_value = '/etc/facter/facts.d'
        mock_exists.return_value = True

        with mock.patch('instack_undercloud.undercloud.open') as open_m:
            undercloud._handle_upgrade_fact(True)
            open_m.assert_called_with('/tmp/file', 'w')

        run_calls = [
            mock.call(['sudo', 'mv', '/tmp/file', fact_path]),
            mock.call(['sudo', 'chmod', '0644', fact_path])
        ]
        mock_run.assert_has_calls(run_calls)
        self.assertEqual(mock_run.call_count, 2)


class TestInstackEnvironment(BaseTestCase):
    def test_set_allowed_keys(self):
        env = undercloud.InstackEnvironment()
        env['HOSTNAME'] = 'localhost1'
        env['INSPECTION_COLLECTORS'] = 'a,b,c'

    def test_set_unknown_keys(self):
        env = undercloud.InstackEnvironment()

        def _set():
            env['CATS_AND_DOGS_PATH'] = '/home'

        self.assertRaisesRegex(KeyError, 'CATS_AND_DOGS_PATH', _set)

    def test_get_always_allowed(self):
        env = undercloud.InstackEnvironment()
        env.get('HOSTNAME')
        env.get('CATS_AND_DOGS_PATH')

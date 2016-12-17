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
import os
import subprocess

import fixtures
import mock
from mistralclient.api import base as mistralclient_base
from novaclient import exceptions
from oslo_config import fixture as config_fixture
from oslotest import base
from oslotest import log
from oslotest import mockpatch
from six.moves import configparser

from instack_undercloud import undercloud


undercloud._configure_logging(undercloud.DEFAULT_LOG_LEVEL, None)


class BaseTestCase(base.BaseTestCase):
    def setUp(self):
        super(BaseTestCase, self).setUp()
        self.logger = self.useFixture(log.ConfigureLogging()).logger


class TestUndercloud(BaseTestCase):
    @mock.patch('instack_undercloud.undercloud._configure_logging')
    @mock.patch('instack_undercloud.undercloud._validate_configuration')
    @mock.patch('instack_undercloud.undercloud._run_command')
    @mock.patch('instack_undercloud.undercloud._post_config')
    @mock.patch('instack_undercloud.undercloud._run_orc')
    @mock.patch('instack_undercloud.undercloud._run_yum_update')
    @mock.patch('instack_undercloud.undercloud._run_instack')
    @mock.patch('instack_undercloud.undercloud._generate_environment')
    @mock.patch('instack_undercloud.undercloud._load_config')
    def test_install(self, mock_load_config, mock_generate_environment,
                     mock_run_yum_update, mock_run_instack, mock_run_orc,
                     mock_post_config, mock_run_command,
                     mock_validate_configuration, mock_configure_logging):
        fake_env = mock.MagicMock()
        mock_generate_environment.return_value = fake_env
        undercloud.install('.')
        self.assertTrue(mock_validate_configuration.called)
        mock_generate_environment.assert_called_with('.')
        mock_run_instack.assert_called_with(fake_env)
        mock_run_orc.assert_called_with(fake_env)
        mock_run_command.assert_called_with(
            ['sudo', 'rm', '-f', '/tmp/svc-map-services'], None, 'rm')

    def test_generate_password(self):
        first = undercloud._generate_password()
        second = undercloud._generate_password()
        self.assertNotEqual(first, second)

    def test_extract_from_stackrc(self):
        with open(os.path.expanduser('~/stackrc'), 'w') as f:
            f.write('OS_USERNAME=aturing\n')
            f.write('OS_AUTH_URL=http://bletchley:5000/v2.0\n')
        self.assertEqual('aturing',
                         undercloud._extract_from_stackrc('OS_USERNAME'))
        self.assertEqual('http://bletchley:5000/v2.0',
                         undercloud._extract_from_stackrc('OS_AUTH_URL'))

    @mock.patch('instack_undercloud.undercloud._check_hostname')
    @mock.patch('instack_undercloud.undercloud._check_memory')
    @mock.patch('instack_undercloud.undercloud._check_sysctl')
    @mock.patch('instack_undercloud.undercloud._validate_network')
    def test_validate_configuration(self, mock_validate_network,
                                    mock_check_memory, mock_check_hostname,
                                    mock_check_sysctl):
        undercloud._validate_configuration()
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
                'echo 127.0.0.1 test.hostname test >> /etc/hosts'],
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
                'echo 127.0.0.1 test.hostname test >> /etc/hosts'],
                name='hostname-to-etc-hosts')

    @mock.patch('instack_undercloud.undercloud._run_command')
    def test_set_fqdn(self, mock_run_command):
        mock_run_command.side_effect = [None,
                                        'test-hostname.domain',
                                        'test-hostname.domain',
                                        None]
        conf = config_fixture.Config()
        self.useFixture(conf)
        conf.config(undercloud_hostname='test-hostname.domain')
        fake_hosts = io.StringIO(u'127.0.0.1 other-hostname\n')
        with mock.patch('instack_undercloud.undercloud.open',
                        return_value=fake_hosts, create=True):
            undercloud._check_hostname()
        mock_run_command.assert_called_with([
            'sudo', '/bin/bash', '-c',
            'echo 127.0.0.1 test-hostname.domain test-hostname >> /etc/hosts'],
            name='hostname-to-etc-hosts')

    @mock.patch('instack_undercloud.undercloud._run_command')
    def test_set_not_fq(self, mock_run_command):
        mock_run_command.side_effect = [None,
                                        'test-hostname',
                                        'test-hostname',
                                        None]
        conf = config_fixture.Config()
        self.useFixture(conf)
        conf.config(undercloud_hostname='test-hostname')
        self.assertRaises(RuntimeError, undercloud._check_hostname)


class TestCheckMemory(BaseTestCase):
    @mock.patch('psutil.virtual_memory')
    def test_sufficient_memory(self, mock_vm):
        mock_vm.return_value = mock.Mock()
        mock_vm.return_value.total = 4143927296
        undercloud._check_memory()

    @mock.patch('psutil.virtual_memory')
    def test_insufficient_memory(self, mock_vm):
        mock_vm.return_value = mock.Mock()
        mock_vm.return_value.total = 2071963648
        self.assertRaises(RuntimeError, undercloud._check_memory)


class TestCheckSysctl(BaseTestCase):
    @mock.patch('os.path.isfile')
    def test_missing_options(self, mock_isfile):
        mock_isfile.return_value = False
        self.assertRaises(RuntimeError, undercloud._check_sysctl)

    @mock.patch('os.path.isfile')
    def test_available_option(self, mock_isfile):
        mock_isfile.return_value = True
        undercloud._check_sysctl()


class TestGenerateEnvironment(BaseTestCase):
    def setUp(self):
        super(TestGenerateEnvironment, self).setUp()
        # Things that need to always be mocked out, but that the tests
        # don't want to care about.
        self.useFixture(mockpatch.Patch(
            'instack_undercloud.undercloud._write_password_file'))
        self.useFixture(mockpatch.Patch(
            'instack_undercloud.undercloud._load_config'))
        mock_isdir = mockpatch.Patch('os.path.isdir')
        self.useFixture(mock_isdir)
        mock_isdir.mock.return_value = False
        # Some tests do care about this, but they can override the default
        # return value, and then the tests that don't care can ignore it.
        self.mock_distro = mockpatch.Patch('platform.linux_distribution')
        self.useFixture(self.mock_distro)
        self.mock_distro.mock.return_value = [
            'Red Hat Enterprise Linux Server 7.1']
        stackrc_exists_patcher = mock.patch(
            'instack_undercloud.undercloud._stackrc_exists',
            return_value=False)
        stackrc_exists_patcher.start()
        self.addCleanup(stackrc_exists_patcher.stop)

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
                         'default,extra-hardware,logs')
        self.assertEqual('192.0.2.1/24', env['PUBLIC_INTERFACE_IP'])
        self.assertEqual('192.0.2.1', env['LOCAL_IP'])

    def test_generate_endpoints(self):
        env = undercloud._generate_environment('.')
        endpoint_vars = {k: v for (k, v) in env.items()
                         if k.startswith('UNDERCLOUD_ENDPOINT')}
        self.assertEqual(39, len(endpoint_vars))
        # Spot check one service
        self.assertEqual('http://192.0.2.1:5000',
                         env['UNDERCLOUD_ENDPOINT_KEYSTONE_PUBLIC'])
        self.assertEqual('http://192.0.2.1:5000',
                         env['UNDERCLOUD_ENDPOINT_KEYSTONE_INTERNAL'])
        self.assertEqual('http://192.0.2.1:35357',
                         env['UNDERCLOUD_ENDPOINT_KEYSTONE_ADMIN'])
        # Also check that the tenant id part is preserved
        self.assertEqual('http://192.0.2.1:8080/v1/AUTH_%(tenant_id)s',
                         env['UNDERCLOUD_ENDPOINT_SWIFT_PUBLIC'])

    def test_generate_endpoints_ssl_manual(self):
        conf = config_fixture.Config()
        self.useFixture(conf)
        conf.config(undercloud_service_certificate='test.pem')
        env = undercloud._generate_environment('.')
        # Spot check one service
        self.assertEqual('https://192.0.2.2:13000',
                         env['UNDERCLOUD_ENDPOINT_KEYSTONE_PUBLIC'])
        self.assertEqual('http://192.0.2.1:5000',
                         env['UNDERCLOUD_ENDPOINT_KEYSTONE_INTERNAL'])
        self.assertEqual('http://192.0.2.1:35357',
                         env['UNDERCLOUD_ENDPOINT_KEYSTONE_ADMIN'])
        # Also check that the tenant id part is preserved
        self.assertEqual('https://192.0.2.2:13808/v1/AUTH_%(tenant_id)s',
                         env['UNDERCLOUD_ENDPOINT_SWIFT_PUBLIC'])

    def test_generate_endpoints_ssl_auto(self):
        conf = config_fixture.Config()
        self.useFixture(conf)
        conf.config(generate_service_certificate=True)
        env = undercloud._generate_environment('.')
        # Spot check one service
        self.assertEqual('https://192.0.2.2:13000',
                         env['UNDERCLOUD_ENDPOINT_KEYSTONE_PUBLIC'])
        self.assertEqual('http://192.0.2.1:5000',
                         env['UNDERCLOUD_ENDPOINT_KEYSTONE_INTERNAL'])
        self.assertEqual('http://192.0.2.1:35357',
                         env['UNDERCLOUD_ENDPOINT_KEYSTONE_ADMIN'])
        # Also check that the tenant id part is preserved
        self.assertEqual('https://192.0.2.2:13808/v1/AUTH_%(tenant_id)s',
                         env['UNDERCLOUD_ENDPOINT_SWIFT_PUBLIC'])

    def test_absolute_cert_path(self):
        conf = config_fixture.Config()
        self.useFixture(conf)
        conf.config(undercloud_service_certificate='/home/stack/test.pem')
        env = undercloud._generate_environment('.')
        self.assertEqual('/home/stack/test.pem',
                         env['UNDERCLOUD_SERVICE_CERTIFICATE'])

    def test_relative_cert_path(self):
        conf = config_fixture.Config()
        self.useFixture(conf)
        conf.config(undercloud_service_certificate='test.pem')
        env = undercloud._generate_environment('.')
        self.assertEqual(os.path.join(os.getcwd(), 'test.pem'),
                         env['UNDERCLOUD_SERVICE_CERTIFICATE'])

    def test_no_cert_path(self):
        env = undercloud._generate_environment('.')
        self.assertEqual('', env['UNDERCLOUD_SERVICE_CERTIFICATE'])

    def test_remove_dib_yum_repo_conf(self):
        self.useFixture(fixtures.EnvironmentVariable('DIB_YUM_REPO_CONF',
                                                     'rum_yepo.conf'))
        env = undercloud._generate_environment('.')
        self.assertNotIn(env, 'DIB_YUM_REPO_CONF')


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
        conf = config_fixture.Config()
        self.useFixture(conf)
        conf.config(undercloud_db_password='test', group='auth')
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


class TestPostConfig(base.BaseTestCase):
    @mock.patch('novaclient.client.Client', autospec=True)
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
                         mock_nova_client):
        instack_env = {
            'UNDERCLOUD_ENDPOINT_MISTRAL_PUBLIC': 'http://192.0.2.1:8989/v2',
        }
        mock_get_auth_values.return_value = ('aturing', '3nigma', 'hut8',
                                             'http://bletchley:5000/v2.0')
        mock_instance = mock.Mock()
        mock_nova_client.return_value = mock_instance
        mock_instance_mistral = mock.Mock()
        mock_mistral_client.return_value = mock_instance_mistral
        undercloud._post_config(instack_env)
        mock_nova_client.assert_called_with(2, 'aturing', '3nigma', 'hut8',
                                            'http://bletchley:5000/v2.0')
        self.assertTrue(mock_copy_stackrc.called)
        mock_configure_ssh_keys.assert_called_with(mock_instance)
        calls = [mock.call(mock_instance, 'baremetal'),
                 mock.call(mock_instance, 'control', 'control'),
                 mock.call(mock_instance, 'compute', 'compute'),
                 mock.call(mock_instance, 'ceph-storage', 'ceph-storage'),
                 mock.call(mock_instance, 'block-storage', 'block-storage'),
                 mock.call(mock_instance, 'swift-storage', 'swift-storage'),
                 ]
        mock_ensure_flavor.assert_has_calls(calls)
        mock_post_config_mistral.assert_called_once_with(instack_env,
                                                         mock_instance_mistral)

    def test_create_default_plan(self):
        mock_mistral = mock.Mock()
        mock_mistral.environments.list.return_value = []
        mock_mistral.executions.get.return_value = mock.Mock(state="SUCCESS")

        undercloud._create_default_plan(mock_mistral)
        mock_mistral.executions.create.assert_called_once_with(
            'tripleo.plan_management.v1.create_default_deployment_plan',
            workflow_input={
                'container': 'overcloud',
                'queue_name': mock.ANY
            }
        )

    def test_create_default_plan_existing(self):
        mock_mistral = mock.Mock()
        environment = collections.namedtuple('environment', ['name'])
        mock_mistral.environments.list.return_value = [
            environment(name='overcloud')
        ]

        undercloud._create_default_plan(mock_mistral)
        mock_mistral.executions.create.assert_not_called()

    def test_create_config_environment(self):
        mock_mistral = mock.Mock()
        mock_mistral.environments.get.side_effect = (
            mistralclient_base.APIException)

        env = {
            "UNDERCLOUD_CEILOMETER_SNMPD_PASSWORD": "snmpd-pass"
        }
        json_string = '{"undercloud_ceilometer_snmpd_password": "snmpd-pass"}'

        undercloud._create_mistral_config_environment(env, mock_mistral)

        mock_mistral.environments.create.assert_called_once_with(
            name="tripleo.undercloud-config",
            variables=json_string)

    def test_create_config_environment_existing(self):
        mock_mistral = mock.Mock()
        environment = collections.namedtuple('environment', ['name'])
        mock_mistral.environments.get.return_value = environment(
            name='overcloud')
        env = {
            "UNDERCLOUD_CEILOMETER_SNMPD_PASSWORD": "snmpd-pass"
        }

        undercloud._create_mistral_config_environment(env, mock_mistral)
        mock_mistral.executions.create.assert_not_called()

    def test_prepare_ssh_environment(self):
        mock_mistral = mock.Mock()
        undercloud._prepare_ssh_environment(mock_mistral)
        mock_mistral.executions.create.assert_called_once_with(
            'tripleo.validations.v1.copy_ssh_key')

    @mock.patch('time.sleep')
    def test_create_default_plan_timeout(self, mock_sleep):
        mock_mistral = mock.Mock()
        mock_mistral.environments.list.return_value = []
        mock_mistral.executions.get.return_value = mock.Mock(state="RUNNING")

        self.assertRaises(
            RuntimeError,
            undercloud._create_default_plan, mock_mistral, timeout=0)

    def test_create_default_plan_failed(self):
        mock_mistral = mock.Mock()
        mock_mistral.environments.list.return_value = []
        mock_mistral.executions.get.return_value = mock.Mock(state="ERROR")

        self.assertRaises(
            RuntimeError,
            undercloud._create_default_plan, mock_mistral)

    @mock.patch('instack_undercloud.undercloud._run_command')
    def test_copy_stackrc(self, mock_run):
        undercloud._copy_stackrc()
        calls = [mock.call(['sudo', 'cp', '/root/stackrc', mock.ANY],
                           name='Copy stackrc'),
                 mock.call(['sudo', 'chown', mock.ANY, mock.ANY],
                           name='Chown stackrc'),
                 ]
        mock_run.assert_has_calls(calls)

    @mock.patch('instack_undercloud.undercloud._stackrc_exists')
    def test_member_role_exists_nostackrc(self, mock_stackrc_exists):
        mock_stackrc_exists.return_value = False
        instack_env = {}
        undercloud._member_role_exists(instack_env)
        self.assertEqual({'MEMBER_ROLE_EXISTS': 'False'}, instack_env)

    def _mock_ksclient_roles(self, mock_auth_values, mock_ksdiscover, roles):
        mock_auth_values.return_value = ('user', 'password',
                                         'tenant', 'http://test:123')
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

    @mock.patch('keystoneclient.discover.Discover')
    @mock.patch('instack_undercloud.undercloud._get_auth_values')
    @mock.patch('instack_undercloud.undercloud._stackrc_exists')
    def test_member_role_exists(self, mock_stackrc_exists, mock_auth_values,
                                mock_ksdiscover):
        mock_stackrc_exists.return_value = True
        self._mock_ksclient_roles(mock_auth_values, mock_ksdiscover,
                                  ['admin'])
        instack_env = {}
        undercloud._member_role_exists(instack_env)
        self.assertEqual({'MEMBER_ROLE_EXISTS': 'False'}, instack_env)

    @mock.patch('keystoneclient.discover.Discover')
    @mock.patch('instack_undercloud.undercloud._get_auth_values')
    @mock.patch('instack_undercloud.undercloud._stackrc_exists')
    def test_member_role_exists_true(self, mock_stackrc_exists,
                                     mock_auth_values, mock_ksdiscover):
        mock_stackrc_exists.return_value = True
        self._mock_ksclient_roles(mock_auth_values, mock_ksdiscover,
                                  ['admin', '_member_'])
        instack_env = {}
        undercloud._member_role_exists(instack_env)
        self.assertEqual({'MEMBER_ROLE_EXISTS': 'True'}, instack_env)

    def _create_flavor_mocks(self):
        mock_nova = mock.Mock()
        mock_nova.flavors.create = mock.Mock()
        mock_flavor = mock.Mock()
        mock_nova.flavors.create.return_value = mock_flavor
        mock_flavor.set_keys = mock.Mock()
        return mock_nova, mock_flavor

    def test_ensure_flavor_no_profile(self):
        mock_nova, mock_flavor = self._create_flavor_mocks()
        undercloud._ensure_flavor(mock_nova, 'test')
        mock_nova.flavors.create.assert_called_with('test', 4096, 1, 40)
        keys = {'capabilities:boot_option': 'local'}
        mock_flavor.set_keys.assert_called_with(keys)

    def test_ensure_flavor_profile(self):
        mock_nova, mock_flavor = self._create_flavor_mocks()
        undercloud._ensure_flavor(mock_nova, 'test', 'test')
        mock_nova.flavors.create.assert_called_with('test', 4096, 1, 40)
        keys = {'capabilities:boot_option': 'local',
                'capabilities:profile': 'test'}
        mock_flavor.set_keys.assert_called_with(keys)

    def test_ensure_flavor_exists(self):
        mock_nova, mock_flavor = self._create_flavor_mocks()
        mock_nova.flavors.create.side_effect = exceptions.Conflict(None)
        undercloud._ensure_flavor(mock_nova, 'test')
        mock_flavor.set_keys.assert_not_called()

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

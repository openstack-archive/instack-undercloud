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

import io

import fixtures
import mock
from oslotest import base

from instack_undercloud import undercloud

# TODO(bnemec): Test all the things
# TODO(bnemec): Stop the code from logging to the real log file during tests


class TestUndercloud(base.BaseTestCase):
    @mock.patch('instack_undercloud.undercloud._check_hostname')
    @mock.patch('instack_undercloud.undercloud._run_command')
    @mock.patch('instack_undercloud.undercloud._configure_ssh_keys')
    @mock.patch('instack_undercloud.undercloud._run_orc')
    @mock.patch('instack_undercloud.undercloud._run_instack')
    @mock.patch('instack_undercloud.undercloud._generate_environment')
    @mock.patch('instack_undercloud.undercloud._load_config')
    def test_install(self, mock_load_config, mock_generate_environment,
                     mock_run_instack, mock_run_orc, mock_configure_ssh_keys,
                     mock_run_command, mock_check_hostname):
        fake_env = mock.MagicMock()
        mock_generate_environment.return_value = fake_env
        undercloud.install('.')
        mock_generate_environment.assert_called_with('.')
        mock_run_instack.assert_called_with(fake_env)
        mock_run_orc.assert_called_with(fake_env)
        mock_run_command.assert_called_with(
            ['sudo', 'rm', '-f', '/tmp/svc-map-services'], None, 'rm')


class TestCheckHostname(base.BaseTestCase):
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
    def test_missing_entry(self, mock_run_command):
        mock_run_command.side_effect = ['test-hostname', 'test-hostname']
        self.useFixture(fixtures.EnvironmentVariable('HOSTNAME',
                                                     'test-hostname'))
        fake_hosts = io.StringIO(u'127.0.0.1 other-hostname\n')
        with mock.patch('instack_undercloud.undercloud.open',
                        return_value=fake_hosts, create=True):
            self.assertRaises(RuntimeError, undercloud._check_hostname)

    @mock.patch('instack_undercloud.undercloud._run_command')
    def test_no_substring_match(self, mock_run_command):
        mock_run_command.side_effect = ['test-hostname', 'test-hostname']
        self.useFixture(fixtures.EnvironmentVariable('HOSTNAME',
                                                     'test-hostname'))
        fake_hosts = io.StringIO(u'127.0.0.1 test-hostname-bad\n')
        with mock.patch('instack_undercloud.undercloud.open',
                        return_value=fake_hosts, create=True):
            self.assertRaises(RuntimeError, undercloud._check_hostname)

    @mock.patch('instack_undercloud.undercloud._run_command')
    def test_commented(self, mock_run_command):
        mock_run_command.side_effect = ['test-hostname', 'test-hostname']
        self.useFixture(fixtures.EnvironmentVariable('HOSTNAME',
                                                     'test-hostname'))
        fake_hosts = io.StringIO(u""" #127.0.0.1 test-hostname\n
                                     127.0.0.1 other-hostname\n""")
        with mock.patch('instack_undercloud.undercloud.open',
                        return_value=fake_hosts, create=True):
            self.assertRaises(RuntimeError, undercloud._check_hostname)

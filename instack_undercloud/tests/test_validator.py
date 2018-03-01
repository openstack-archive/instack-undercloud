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

import mock

from oslo_config import fixture as config_fixture
from oslo_config import cfg
from oslotest import base

from instack_undercloud import undercloud
from instack_undercloud import validator


class TestValidator(base.BaseTestCase):
    def setUp(self):
        super(TestValidator, self).setUp()
        self.conf = self.useFixture(config_fixture.Config())
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
        self.conf.config(cidr='192.168.24.0/24',
                         dhcp_start='192.168.24.5', dhcp_end='192.168.24.24',
                         inspection_iprange='192.168.24.100,192.168.24.120',
                         gateway='192.168.24.1', masquerade=True,
                         group='ctlplane-subnet')

    @mock.patch('netifaces.interfaces')
    def test_validation_passes(self, ifaces_mock):
        ifaces_mock.return_value = ['eth1']
        undercloud._validate_network()

    def test_fail_on_local_ip(self):
        self.conf.config(local_ip='193.0.2.1/24')
        self.assertRaises(validator.FailedValidation,
                          undercloud._validate_network)

    def test_fail_on_network_gateway(self):
        self.conf.config(gateway='193.0.2.1', group='ctlplane-subnet')
        self.assertRaises(validator.FailedValidation,
                          undercloud._validate_network)

    def test_fail_on_dhcp_start(self):
        self.conf.config(dhcp_start='193.0.2.10', group='ctlplane-subnet')
        self.assertRaises(validator.FailedValidation,
                          undercloud._validate_network)

    def test_fail_on_dhcp_end(self):
        self.conf.config(dhcp_end='193.0.2.10', group='ctlplane-subnet')
        self.assertRaises(validator.FailedValidation,
                          undercloud._validate_network)

    def test_fail_on_inspection_start(self):
        self.conf.config(inspection_iprange='193.0.2.100,192.168.24.120',
                         group='ctlplane-subnet')
        self.assertRaises(validator.FailedValidation,
                          undercloud._validate_network)

    def test_fail_on_inspection_end(self):
        self.conf.config(inspection_iprange='192.168.24.100,193.0.2.120',
                         group='ctlplane-subnet')
        self.assertRaises(validator.FailedValidation,
                          undercloud._validate_network)

    def test_fail_on_dhcp_order(self):
        self.conf.config(dhcp_start='192.168.24.100', dhcp_end='192.168.24.10',
                         group='ctlplane-subnet')
        self.assertRaises(validator.FailedValidation,
                          undercloud._validate_network)

    def test_fail_on_dhcp_equal(self):
        self.conf.config(dhcp_start='192.168.24.100',
                         dhcp_end='192.168.24.100', group='ctlplane-subnet')
        self.assertRaises(validator.FailedValidation,
                          undercloud._validate_network)

    def test_fail_on_inspection_order(self):
        self.conf.config(inspection_iprange='192.168.24.120,192.168.24.100',
                         group='ctlplane-subnet')
        self.assertRaises(validator.FailedValidation,
                          undercloud._validate_network)

    def test_fail_on_inspection_equal(self):
        self.conf.config(inspection_iprange='192.168.24.120,192.168.24.120',
                         group='ctlplane-subnet')
        self.assertRaises(validator.FailedValidation,
                          undercloud._validate_network)

    def test_fail_on_range_overlap_1(self):
        self.conf.config(dhcp_start='192.168.24.10', dhcp_end='192.168.24.100',
                         inspection_iprange='192.168.24.90,192.168.24.110',
                         group='ctlplane-subnet')
        self.assertRaises(validator.FailedValidation,
                          undercloud._validate_network)

    def test_fail_on_range_overlap_2(self):
        self.conf.config(dhcp_start='192.168.24.100',
                         dhcp_end='192.168.24.120',
                         inspection_iprange='192.168.24.90,192.168.24.110',
                         group='ctlplane-subnet')
        self.assertRaises(validator.FailedValidation,
                          undercloud._validate_network)

    def test_fail_on_range_overlap_3(self):
        self.conf.config(dhcp_start='192.168.24.20', dhcp_end='192.168.24.90',
                         inspection_iprange='192.168.24.10,192.168.24.100',
                         group='ctlplane-subnet')
        self.assertRaises(validator.FailedValidation,
                          undercloud._validate_network)

    def test_fail_on_range_overlap_4(self):
        self.conf.config(dhcp_start='192.168.24.10', dhcp_end='192.168.24.100',
                         inspection_iprange='192.168.24.20,192.168.24.90',
                         group='ctlplane-subnet')
        self.assertRaises(validator.FailedValidation,
                          undercloud._validate_network)

    def test_fail_on_invalid_local_ip(self):
        self.conf.config(local_ip='192.168.24.1')
        self.assertRaises(validator.FailedValidation,
                          undercloud._validate_network)

    def test_fail_on_unqualified_hostname(self):
        self.conf.config(undercloud_hostname='undercloud')
        self.assertRaises(validator.FailedValidation,
                          undercloud._validate_network)

    def test_no_alter_params(self):
        self.conf.config(cidr='192.168.24.0/24', group='ctlplane-subnet')
        params = {opt.name: self.conf.conf[opt.name]
                  for opt in undercloud._opts}
        params.update(
            {opt.name: self.conf.conf.get('ctlplane-subnet')[opt.name]
             for opt in undercloud._subnets_opts})
        save_params = dict(params)
        validator.validate_config(params, lambda x: None)
        self.assertEqual(save_params, params)

    @mock.patch('netifaces.interfaces')
    def test_valid_undercloud_nameserver_passes(self, ifaces_mock):
        ifaces_mock.return_value = ['eth1']
        self.conf.config(undercloud_nameservers=['192.168.24.4',
                                                 '192.168.24.5'])
        undercloud._validate_network()

    def test_invalid_undercloud_nameserver_fails(self):
        self.conf.config(undercloud_nameservers=['Iamthewalrus'])
        self.assertRaises(validator.FailedValidation,
                          undercloud._validate_network)

    def test_fail_on_invalid_public_host(self):
        self.conf.config(undercloud_public_host='192.0.3.2',
                         undercloud_service_certificate='foo.pem',
                         enable_ui=False)
        self.assertRaises(validator.FailedValidation,
                          undercloud._validate_network)

    def test_fail_on_invalid_admin_host(self):
        self.conf.config(undercloud_admin_host='192.0.3.3',
                         generate_service_certificate=True,
                         enable_ui=False)
        self.assertRaises(validator.FailedValidation,
                          undercloud._validate_network)

    @mock.patch('netifaces.interfaces')
    def test_ssl_hosts_allowed(self, ifaces_mock):
        ifaces_mock.return_value = ['eth1']
        self.conf.config(undercloud_public_host='public.domain',
                         undercloud_admin_host='admin.domain',
                         undercloud_service_certificate='foo.pem',
                         enable_ui=False)
        undercloud._validate_network()

    @mock.patch('netifaces.interfaces')
    def test_allow_all_with_ui(self, ifaces_mock):
        ifaces_mock.return_value = ['eth1']
        self.conf.config(undercloud_admin_host='10.0.0.10',
                         generate_service_certificate=True,
                         enable_ui=True)
        undercloud._validate_network()

    @mock.patch('netifaces.interfaces')
    def test_fail_on_invalid_ip(self, ifaces_mock):
        ifaces_mock.return_value = ['eth1']
        self.conf.config(dhcp_start='foo.bar', group='ctlplane-subnet')
        self.assertRaises(validator.FailedValidation,
                          undercloud._validate_network)

    @mock.patch('netifaces.interfaces')
    def test_validate_interface_exists(self, ifaces_mock):
        ifaces_mock.return_value = ['eth0', 'eth1']
        self.conf.config(local_interface='eth0')
        undercloud._validate_network()

    @mock.patch('netifaces.interfaces')
    def test_fail_validate_interface_missing(self, ifaces_mock):
        ifaces_mock.return_value = ['eth0', 'eth1']
        self.conf.config(local_interface='em1')
        self.assertRaises(validator.FailedValidation,
                          undercloud._validate_network)

    @mock.patch('netifaces.interfaces')
    def test_validate_interface_with_net_config_override(self, ifaces_mock):
        ifaces_mock.return_value = ['eth0', 'eth1']
        self.conf.config(local_interface='em2', net_config_override='foo')
        undercloud._validate_network()

    def test_validate_additional_architectures_ok(self):
        self.conf.config(additional_architectures=['ppc64le'],
                         ipxe_enabled=False)
        undercloud._validate_architecure_options()

    def test_validate_additional_architectures_bad_arch(self):
        self.conf.config(additional_architectures=['ppc64le', 'INVALID'],
                         ipxe_enabled=False)
        self.assertRaises(validator.FailedValidation,
                          undercloud._validate_architecure_options)

    def test_validate_additional_architectures_ipxe_fail(self):
        self.conf.config(additional_architectures=['ppc64le'],
                         ipxe_enabled=True)
        self.assertRaises(validator.FailedValidation,
                          undercloud._validate_architecure_options)

    @mock.patch('netifaces.interfaces')
    def test_validate_routed_networks_not_enabled_pass(self, ifaces_mock):
        ifaces_mock.return_value = ['eth0', 'eth1']
        self.conf.config(enable_routed_networks=False)
        self.conf.config(subnets=['ctlplane-subnet'])
        undercloud._validate_network()

    @mock.patch('netifaces.interfaces')
    def test_validate_routed_networks_not_enabled_fail(self, ifaces_mock):
        ifaces_mock.return_value = ['eth0', 'eth1']
        self.conf.config(enable_routed_networks=False)
        self.conf.config(subnets=['ctlplane-subnet', 'subnet1'])
        self.assertRaises(validator.FailedValidation,
                          undercloud._validate_network)

    @mock.patch('netifaces.interfaces')
    def test_validate_routed_networks_enabled_pass(self, ifaces_mock):
        ifaces_mock.return_value = ['eth0', 'eth1']
        self.conf.config(enable_routed_networks=True)
        self.conf.config(subnets=['ctlplane-subnet', 'subnet1'])
        self.conf.register_opts(self.opts, group=self.grp1)
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
        undercloud._validate_network()

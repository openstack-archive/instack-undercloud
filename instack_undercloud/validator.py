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

import netaddr
import netifaces
import six


SUPPORTED_ARCHITECTURES = ['ppc64le']


class FailedValidation(Exception):
    pass


def validate_config(params, error_callback):
    """Validate an undercloud configuration described by params

    :param params: A dict containing all of the undercloud.conf option
        names mapped to their proposed values.
    :param error_callback: A callback function that should be used to handle
        errors.  The function must accept a single parameter, which will be
        a string describing the error.
    """
    local_params = dict(params)
    _validate_value_formats(local_params, error_callback)
    _validate_in_cidr(local_params, error_callback)
    _validate_dhcp_range(local_params, error_callback)
    _validate_inspection_range(local_params, error_callback)
    _validate_no_overlap(local_params, error_callback)
    _validate_ips(local_params, error_callback)
    _validate_interface_exists(local_params, error_callback)


def _validate_ppc64le_exclusive_opts(params, error_callback):
    if 'ppc64le' in params['additional_architectures']:
        if 'ipxe_enabled' in params and params['ipxe_enabled']:
            error_callback('Currently iPXE boot isn\'t supported with '
                           'ppc64le systems but is enabled')


def _validate_additional_architectures(params, error_callback):
    for arch in params['additional_architectures']:
        if arch not in SUPPORTED_ARCHITECTURES:
            error_callback('%s "%s" must be a supported architecture: %s' %
                           ('additional_architectures', arch,
                            ' '.join(SUPPORTED_ARCHITECTURES)))


def _validate_ips(params, error_callback):
    def is_ip(value, param_name):
        try:
            netaddr.IPAddress(value)
        except netaddr.core.AddrFormatError:
            error_callback(
                '%s "%s" must be a valid IP address' % (param_name, value))
    for ip in params['undercloud_nameservers']:
        is_ip(ip, 'undercloud_nameservers')


def _validate_value_formats(params, error_callback):
    """Validate format of some values

    Certain values have a specific format that must be maintained in order to
    work properly.  For example, local_ip must be in CIDR form, and the
    hostname must be a FQDN.
    """
    for param in ('local_ip', 'cidr'):
        if param in params:
            try:
                ip_net = netaddr.IPNetwork(params[param])
                if (ip_net.prefixlen == 32) or (ip_net.prefixlen == 0):
                    message = ('"%s" "%s" not valid: Invalid netmask.' %
                               (param, params[param]))
                    error_callback(message)
                # If IPv6 the ctlplane network uses the EUI-64 address format,
                # which requires the prefix to be /64
                if ip_net.version == 6 and ip_net.prefixlen != 64:
                    message = ('"%s" "%s" not valid: '
                               'Prefix must be 64 for IPv6.' %
                               (param, params[param]))
                    error_callback(message)
            except netaddr.core.AddrFormatError as e:
                message = ('"%s" "%s" not valid: "%s" '
                           'Value must be in CIDR format.' %
                           (param, params[param], str(e)))
                error_callback(message)
            except TypeError as e:
                message = ('"%s" "%s" invalid type: "%s" ' %
                           (param, params[param], str(e)))
                error_callback(message)
    if 'undercloud_hostname' in params:
        hostname = params['undercloud_hostname']
        if hostname is not None and '.' not in hostname:
            message = 'Hostname "%s" is not fully qualified.' % hostname
            error_callback(message)


def _validate_in_cidr(params, error_callback):
    cidr = netaddr.IPNetwork(params['cidr'])

    def validate_addr_in_cidr(params, name, pretty_name=None, require_ip=True):
        try:
            if netaddr.IPAddress(params[name]) not in cidr:
                message = ('%s "%s" not in defined CIDR "%s"' %
                           (pretty_name or name, params[name], cidr))
                error_callback(message)
        except netaddr.core.AddrFormatError:
            if require_ip:
                message = 'Invalid IP address: %s' % params[name]
                error_callback(message)

    # NOTE(hjensas): Only check certs etc if not validating routed subnets
    if 'local_ip' in params:
        params['just_local_ip'] = params['local_ip'].split('/')[0]
        validate_addr_in_cidr(params, 'just_local_ip', 'local_ip')
        # NOTE(bnemec): The ui needs to be externally accessible, which means
        # in many cases we can't have the public vip on the provisioning
        # network. In that case users are on their own to ensure they've picked
        # valid values for the VIP hosts.
        if ((params['undercloud_service_certificate'] or
             params['generate_service_certificate']) and
                not params['enable_ui']):
            validate_addr_in_cidr(params, 'undercloud_public_host',
                                  require_ip=False)
            validate_addr_in_cidr(params, 'undercloud_admin_host',
                                  require_ip=False)
    # undercloud.conf uses inspection_iprange, the configuration wizard
    # tool passes the values separately.
    if 'inspection_iprange' in params:
        inspection_iprange = params['inspection_iprange'].split(',')
        params['inspection_start'] = inspection_iprange[0]
        params['inspection_end'] = inspection_iprange[1]
    validate_addr_in_cidr(params, 'gateway')
    validate_addr_in_cidr(params, 'dhcp_start')
    validate_addr_in_cidr(params, 'dhcp_end')
    validate_addr_in_cidr(params, 'inspection_start', 'Inspection range start')
    validate_addr_in_cidr(params, 'inspection_end', 'Inspection range end')


def _validate_dhcp_range(params, error_callback):
    dhcp_start = netaddr.IPAddress(params['dhcp_start'])
    dhcp_end = netaddr.IPAddress(params['dhcp_end'])
    if dhcp_start >= dhcp_end:
        message = ('Invalid dhcp range specified, dhcp_start "%s" does '
                   'not come before dhcp_end "%s"' %
                   (dhcp_start, dhcp_end))
        error_callback(message)


def _validate_inspection_range(params, error_callback):
    inspection_start = netaddr.IPAddress(params['inspection_start'])
    inspection_end = netaddr.IPAddress(params['inspection_end'])
    if inspection_start >= inspection_end:
        message = ('Invalid inspection range specified, inspection_start '
                   '"%s" does not come before inspection_end "%s"' %
                   (inspection_start, inspection_end))
        error_callback(message)


def _validate_no_overlap(params, error_callback):
    """Validate the provisioning and inspection ip ranges do not overlap"""
    dhcp_set = netaddr.IPSet(netaddr.IPRange(params['dhcp_start'],
                                             params['dhcp_end']))
    inspection_set = netaddr.IPSet(netaddr.IPRange(params['inspection_start'],
                                                   params['inspection_end']))
    # If there is any intersection of the two sets then we have a problem
    if dhcp_set & inspection_set:
        message = ('Inspection DHCP range "%s-%s" overlaps provisioning '
                   'DHCP range "%s-%s".' %
                   (params['inspection_start'], params['inspection_end'],
                    params['dhcp_start'], params['dhcp_end']))
        error_callback(message)


def _validate_interface_exists(params, error_callback):
    """Validate the provided local interface exists"""
    local_interface = params['local_interface']
    net_override = params['net_config_override']
    if not net_override and local_interface not in netifaces.interfaces():
        message = ('Invalid local_interface specified. %s is not available.' %
                   local_interface)
        error_callback(message)


def _validate_no_missing_subnet_param(name, params, error_callback):
    if None in six.viewvalues(params):
        missing = list((k) for k, v in params.iteritems() if not v)
        message = 'subnet %s. Missing option(s): %s' % (name, missing)
        error_callback(message)


def validate_subnet(name, params, error_callback):
    local_params = dict(params)
    _validate_no_missing_subnet_param(name, params, error_callback)
    _validate_value_formats(local_params, error_callback)
    _validate_in_cidr(local_params, error_callback)
    _validate_dhcp_range(local_params, error_callback)
    _validate_inspection_range(local_params, error_callback)
    _validate_no_overlap(local_params, error_callback)

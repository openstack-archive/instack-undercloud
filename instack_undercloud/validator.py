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


def _validate_value_formats(params, error_callback):
    """Validate format of some values

    Certain values have a specific format that must be maintained in order to
    work properly.  For example, local_ip must be in CIDR form, and the
    hostname must be a FQDN.
    """
    try:
        local_ip = netaddr.IPNetwork(params['local_ip'])
        if local_ip.prefixlen == 32:
            raise netaddr.AddrFormatError('Invalid netmask')
    except netaddr.core.AddrFormatError as e:
        message = ('local_ip "%s" not valid: "%s" '
                   'Value must be in CIDR format.' %
                   (params['local_ip'], str(e)))
        error_callback(message)
    hostname = params['undercloud_hostname']
    if hostname is not None and '.' not in hostname:
        message = 'Hostname "%s" is not fully qualified.' % hostname
        error_callback(message)


def _validate_in_cidr(params, error_callback):
    cidr = netaddr.IPNetwork(params['network_cidr'])

    def validate_addr_in_cidr(params, name, pretty_name=None):
        if netaddr.IPAddress(params[name]) not in cidr:
            message = ('%s "%s" not in defined CIDR "%s"' %
                       (pretty_name or name, params[name], cidr))
            error_callback(message)

    params['just_local_ip'] = params['local_ip'].split('/')[0]
    # undercloud.conf uses inspection_iprange, the configuration wizard
    # tool passes the values separately.
    if 'inspection_iprange' in params:
        inspection_iprange = params['inspection_iprange'].split(',')
        params['inspection_start'] = inspection_iprange[0]
        params['inspection_end'] = inspection_iprange[1]
    validate_addr_in_cidr(params, 'just_local_ip', 'local_ip')
    validate_addr_in_cidr(params, 'network_gateway')
    if params['undercloud_service_certificate']:
        validate_addr_in_cidr(params, 'undercloud_public_vip')
        validate_addr_in_cidr(params, 'undercloud_admin_vip')
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

#!/usr/bin/env python
"""Usage: "<virsh|libvirt> [<MAC-TO-SEARCH> ... ]" """

import sys
import xml.etree.ElementTree as ET

import libvirt
from oslo_concurrency import processutils
import paramiko


SSH_PARAMS = {
    'host': 'pshchelokovskyy-pc',
    'user': 'pshchelo',
    'key_file': '/home/pshchelo/.ssh/id_rsa'
}

VIRSH_CMDS = {
    "base_cmd": "LC_ALL=C /usr/bin/virsh",
    "list_all": "list --all | tail -n +2 | awk -F\" \" '{print $2}'",
    "get_node_macs": (
        "dumpxml {_NodeName_} | "
        "awk -F \"'\" '/mac address/{print $2}'| tr -d ':'")
}

LIBVIRT_URI = "qemu+ssh://%(user)s@%(host)s/system" % SSH_PARAMS


def _normalize_mac(mac):
    return mac.replace('-', '').replace(':', '').lower()


def _ssh_connect():
    """Method to connect to a remote system using ssh protocol.
    :param connection: a dict of connection parameters.
    :returns: paramiko.SSHClient -- an active ssh connection.
    :raises: SSHConnectFailed
    """
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    pkey = None
    ssh.connect(SSH_PARAMS.get('host'),
                username=SSH_PARAMS.get('user'),
                port=22,
                key_filename=SSH_PARAMS.get('key_file'),
                timeout=10)

    # send TCP keepalive packets every 20 seconds
    ssh.get_transport().set_keepalive(20)

    return ssh

def _ssh_execute(ssh_obj, cmd_to_exec):
    return processutils.ssh_execute(ssh_obj, cmd_to_exec)[0].split('\n')

def test_virsh(macs):
    matched_name = None
    ssh_obj = _ssh_connect()
    cmd = "%s %s" % (VIRSH_CMDS['base_cmd'], VIRSH_CMDS['list_all'])
    all_nodes = _ssh_execute(ssh_obj, cmd)
    if not macs:
        return [n for n in all_nodes if n]
    for node in all_nodes:
        if not node:
            continue
        cmd = "%s %s" % (VIRSH_CMDS['base_cmd'], VIRSH_CMDS['get_node_macs'])
        cmd = cmd.replace('{_NodeName_}', node)
        hosts_node_mac_list = _ssh_execute(ssh_obj, cmd)

        for host_mac in hosts_node_mac_list:
            if not host_mac:
                continue
            for node_mac in macs:
                if _normalize_mac(host_mac) in _normalize_mac(node_mac):
                    matched_name = node
                    break

            if matched_name:
                break
        if matched_name:
            break

    return matched_name


def test_libvirt(macs):
    conn = libvirt.open(LIBVIRT_URI)
    all_domains = conn.listAllDomains()
    if not macs:
        return [d.name() for d in all_domains]
    node_macs = {_normalize_mac(m) for m in macs}
    for domain in all_domains:
        parsed = ET.fromstring(domain.XMLDesc())
        domain_macs = {_normalize_mac(el.attrib['address'])
                       for el in parsed.iter('mac')}
        found_macs = domain_macs & node_macs
        if found_macs:
            return domain.name()


def test(name, *macs):
    if name == 'virsh':
        # print("Testing SSH...")
        # print(test_virsh(macs))
        test_virsh(macs)
    elif name == 'libvirt':
        # print("Testing LibVirt...")
        # print(test_libvirt(macs))
        test_libvirt(macs)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    test(args[0], *args[1:])

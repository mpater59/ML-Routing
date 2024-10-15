import yaml
import argparse
import requests


# Constants
IPV4_ADDRESS = '127.0.0.1'  # SDN controller IPv4 address
PORT = 8080


def apply_init_config(topo_info):
    def get_dpid(dpid):
        dpid = hex(dpid)[2:]
        dpid = '0' * (16 - len(dpid)) + dpid
        return dpid

    def get_switch(switch_name):
        dpid = None
        for node in topo_info['nodes']:
            if node['name'] == switch_name:
                return node
        if dpid is None:
            print(f"Couldn't find DPID for switch {switch_name}")
            exit()

    # setting up switches
    for node in topo_info['nodes']:
        dpid_r = get_dpid(node['id'])
        dpid_s = get_dpid(node['id'] + len(topo_info['nodes']))

        data = {"type": "router", "ip address": f"192.168.{node['id'] * 10}.1",
                "mac address": f"00:aa:bb:00:00:0{node['id']}"}
        requests.post(f'http://{IPV4_ADDRESS}:{PORT}/switch/{dpid_r}', json=data)

        data = {"type": "switch"}
        requests.post(f'http://{IPV4_ADDRESS}:{PORT}/switch/{dpid_s}', json=data)

    # setting up links
    for link in topo_info['links']:
        dpid_a = get_dpid(get_switch(link['node a'])['id'])
        dpid_b = get_dpid(get_switch(link['node b'])['id'])

        data = {"sw1": {"dpid": f"{dpid_a}", "port": link['port a']},
                "sw2": {"dpid": f"{dpid_b}", "port": link['port b']},
                "metric": link['metric']}
        requests.post(f'http://{IPV4_ADDRESS}:{PORT}/ospf/link', json=data)

    # setting up ospf networks
    for node in topo_info['nodes']:
        dpid = get_dpid(node['id'])
        data = {"network": f"192.168.{node['id'] * 10}.0/24"}
        requests.post(f'http://{IPV4_ADDRESS}:{PORT}/ospf/network/switch/{dpid}', json=data)

    # enable ospf
    requests.post(f'http://{IPV4_ADDRESS}:{PORT}/ospf', json={"enable": True})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--file', dest='file', default='topo.yaml',
                        help='Topology file in .yaml format')
    args = parser.parse_args()

    topo_info = {}
    with open(args.file) as f:
        try:
            topo_info = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(e)
    apply_init_config(topo_info)

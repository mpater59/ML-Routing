import argparse
import yaml
import topo_init_config
import time


from traffic_emulation.traffic_emulation_starter import start_traffic_emulation
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.node import RemoteController, OVSSwitch
from mininet.link import TCLink
from mininet.topolib import Topo
from mininet.log import info
from os import listdir
from re import match
from urllib.request import build_opener, HTTPHandler, Request
from mininet.util import quietRun
from json import dumps

# Constants
NUMBER_OF_ROUTERS = 5
NUMBER_OF_HOSTS = 3
COLLECTOR = '127.0.0.1'
AGENT = 'lo'
SAMPLING_N = 64
POLLING_SECS = 10


def get_dpid(dpid):
    dpid = hex(dpid)[2:]
    dpid = '0' * (16 - len(dpid)) + dpid
    return dpid


def get_switch(switch_name, switch_list):
    dpid = None
    for node in topo_info['nodes']:
        if node['name'] == switch_name:
            dpid = node['id']
            break
    if dpid is None:
        print(f"Couldn't find DPID for switch {switch_name}")
        exit()

    return switch_list[dpid]


# from sflow-rt/extras/sflow.py
def config_sflow(net, collector, ifname, sampling, polling):
    info("*** Enabling sFlow:\n")
    sflow = 'ovs-vsctl -- --id=@sflow create sflow agent=%s target=%s sampling=%s polling=%s --' % (ifname, collector,
                                                                                                    sampling, polling)
    for s in net.switches:
        sflow += ' -- set bridge %s sflow=@sflow' % s
    info(' '.join([s.name for s in net.switches]) + "\n")
    quietRun(sflow)


# from sflow-rt/extras/sflow.py
def send_topology(net, agent, collector):
    info("*** Sending topology\n")
    topo = {'nodes': {}, 'links': {}}
    for s in net.switches:
        topo['nodes'][s.name] = {'agent': agent, 'ports': {}}
    path = '/sys/devices/virtual/net/'
    for child in listdir(path):
        parts = match('(^.+)-(.+)', child)
        if parts is None: continue
        if parts.group(1) in topo['nodes']:
            ifindex = open(path + child + '/ifindex').read().split('\n', 1)[0]
            topo['nodes'][parts.group(1)]['ports'][child] = {'ifindex': ifindex}
    i = 0
    for s1 in net.switches:
        j = 0
        for s2 in net.switches:
            if j > i:
                intfs = s1.connectionsTo(s2)
                for intf in intfs:
                    s1ifIdx = topo['nodes'][s1.name]['ports'][intf[0].name]['ifindex']
                    s2ifIdx = topo['nodes'][s2.name]['ports'][intf[1].name]['ifindex']
                    linkName = '%s-%s' % (s1.name, s2.name)
                    topo['links'][linkName] = {'node1': s1.name, 'port1': intf[0].name, 'node2': s2.name,
                                               'port2': intf[1].name}
            j += 1
        i += 1

    opener = build_opener(HTTPHandler)
    request = Request('http://%s:8008/topology/json' % collector, data=dumps(topo).encode('utf-8'))
    request.add_header('Content-Type', 'application/json')
    request.get_method = lambda: 'PUT'
    url = opener.open(request)


class Topology(Topo):
    def build(self):

        routers = {}
        r_switches = {}
        for node in topo_info['nodes']:
            switch_id = node['id']
            routers[switch_id] = self.addSwitch(f"{node['name']}", dpid=get_dpid(switch_id))

        for node in topo_info['nodes']:
            dpid = node['id'] + len(topo_info['nodes'])
            switch_id = node['id']
            r_switches[switch_id] = self.addSwitch(f's{switch_id}', dpid=get_dpid(dpid))
            self.addLink(routers[switch_id], r_switches[switch_id])

        hosts = {}
        for node in topo_info['nodes']:
            switch_id = node['id']
            hosts[switch_id] = []
            for host_id in range(1, topo_info['hosts number'] + 1):
                hosts[switch_id].append(self.addHost(f's{switch_id}h{host_id}',
                                                     ip=f'192.168.{10 * switch_id}.{10 * host_id}/24'))
                self.addLink(r_switches[switch_id], hosts[switch_id][-1])

        for link in topo_info['links']:
            a_node = get_switch(link['node a'], routers)
            b_node = get_switch(link['node b'], routers)
            bw = link['bw']
            delay = link['delay']
            self.addLink(a_node, b_node, bw=bw, delay=f"{delay}ms")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--file', dest='file', default='topo.yaml',
                        help='Topology file in .yaml format')
    parser.add_argument('-e', '--emulation', dest='emulation', default=None,
                        help='Name of traffic emulation for saving results (default: None)')
    parser.add_argument('-t', '--time', dest='time', type=int, default=None,
                        help='Time of traffic emulation in minutes (default: infinite time)')
    parser.add_argument('-s', '--seed', dest='seed', type=int, default=None,
                        help='Seed for random function in traffic emulation (default: current timestamp)')
    args = parser.parse_args()

    ryu_controller = RemoteController('ryu', ip='127.0.0.1', port=6633)
    topo = Topology()
    net = Mininet(switch=OVSSwitch, link=TCLink, topo=topo, controller=ryu_controller, autoSetMacs=True)

    net.start()

    for node in topo_info['nodes']:
        switch_id = node['id']
        for host_id in range(1, topo_info['hosts number'] + 1):
            host = net.get(f's{switch_id}h{host_id}')
            host.setARP(f'192.168.{10 * switch_id}.1', f'00:aa:bb:00:00:0{switch_id}')
            host.setDefaultRoute(f'dev s{switch_id}h{host_id}-eth0 via 192.168.{10 * switch_id}.1')

    config_sflow(net, COLLECTOR, AGENT, SAMPLING_N, POLLING_SECS)
    send_topology(net, COLLECTOR, COLLECTOR)

    topo_init_config.apply_init_config(topo_info)
    time.sleep(1)
    net.pingAll()
    # start_traffic_emulation(net, topo_info, args.emulation, args.time, args.seed)
    CLI(net)
    net.stop()

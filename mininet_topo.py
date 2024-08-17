import argparse

from mininet.net import Mininet
from mininet.cli import CLI
from mininet.node import RemoteController, OVSSwitch
from mininet.link import TCLink
from mininet.topolib import Topo
from mininet.log import info
from os import listdir, environ
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


        dpid_id = 1
        routers = []
        r_switches = []
        for x in range(1, NUMBER_OF_ROUTERS + 1):
            routers.append(self.addSwitch(f'r{x}', dpid=get_dpid(dpid_id)))
            dpid_id += 1

        for x in range(1, NUMBER_OF_ROUTERS + 1):
            r_switches.append(self.addSwitch(f's{x}', dpid=get_dpid(dpid_id)))
            dpid_id += 1
            self.addLink(routers[x-1], r_switches[-1])

        hosts = {}
        for switch_id in range(1, NUMBER_OF_ROUTERS + 1):
            hosts[switch_id] = []
            for host_id in range(1, NUMBER_OF_HOSTS + 1):
                hosts[switch_id].append(self.addHost(f's{switch_id}h{host_id}',
                                                     ip=f'192.168.{10 * switch_id}.{10 * host_id}/24'))
                self.addLink(r_switches[switch_id - 1], hosts[switch_id][-1])

        r1 = routers[0]
        r2 = routers[1]
        r3 = routers[2]
        r4 = routers[3]
        r5 = routers[4]

        self.addLink(r1, r2, bw=10, delay='10ms')
        self.addLink(r1, r3, bw=10, delay='5ms')
        self.addLink(r1, r4, bw=15, delay='15ms')
        self.addLink(r3, r4, bw=15, delay='15ms')
        self.addLink(r4, r2, bw=5, delay='5ms')
        self.addLink(r3, r5, bw=5, delay='5ms')
        self.addLink(r5, r4, bw=5, delay='5ms')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--file', dest='file', default='topo.yaml',
                        help='Topology file in .yaml format')
    args = parser.parse_args()

    ryu_controller = RemoteController('ryu', ip='127.0.0.1', port=6633)
    topo = Topology()
    net = Mininet(switch=OVSSwitch, link=TCLink, topo=topo, controller=ryu_controller, autoSetMacs=True)

    net.start()

    for switch_id in range(1, NUMBER_OF_ROUTERS + 1):
        for host_id in range(1, NUMBER_OF_HOSTS + 1):
            host = net.get(f's{switch_id}h{host_id}')
            host.setARP(f'192.168.{10 * switch_id}.1', f'00:aa:bb:00:00:0{switch_id}')
            host.setDefaultRoute(f'dev s{switch_id}h{host_id}-eth0 via 192.168.{10 * switch_id}.1')

    config_sflow(net, COLLECTOR, AGENT, SAMPLING_N, POLLING_SECS)
    send_topology(net, COLLECTOR, COLLECTOR)

    CLI(net)
    net.stop()

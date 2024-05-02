import argparse

from mininet.net import Mininet
from mininet.cli import CLI
from mininet.node import RemoteController, OVSSwitch
from mininet.link import TCLink
from mininet.topolib import Topo


# Constants
NUMBER_OF_ROUTERS = 5


def get_dpid(dpid):
    dpid = hex(dpid)[2:]
    dpid = '0' * (16 - len(dpid)) + dpid
    return dpid


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
            for host_id in range(1, args.hosts + 1):
                hosts[switch_id].append(self.addHost(f's{switch_id}-h{host_id}',
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
    parser.add_argument('-hs', '--hosts', dest='hosts', default=3, type=int,
                        help='Number of hosts for every router switch (default 3)')
    args = parser.parse_args()

    ryu_controller = RemoteController('ryu', ip='127.0.0.1', port=6633)
    topo = Topology()
    net = Mininet(switch=OVSSwitch, link=TCLink, topo=topo, controller=ryu_controller, autoSetMacs=True)

    net.start()

    for switch_id in range(1, NUMBER_OF_ROUTERS + 1):
        for host_id in range(1, args.hosts + 1):
            host = net.get(f's{switch_id}-h{host_id}')
            host.setARP(f'192.168.{10 * switch_id}.1', '00:aa:bb:00:00:01')
            host.setDefaultRoute(f'dev eth0 via 192.168.{10 * switch_id}.1')

    CLI(net)
    net.stop()

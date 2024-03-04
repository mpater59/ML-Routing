import argparse

from mininet.net import Mininet
from mininet.cli import CLI
from mininet.node import RemoteController, OVSSwitch
from mininet.link import TCLink
from mininet.topolib import Topo


class Topology(Topo):
    def build(self):
        spine_switches = []
        leaf_switches = []
        servers = []
        server_links = []

        for x in range(args.spine):
            spine_switches.append(self.addSwitch(f's{x + 1}'))

        for x in range(args.leaf):
            leaf_switches.append(self.addSwitch(f's{x + 1 + args.spine}'))
            # servers.append(net.addHost(f'h{x + 1 + args.host}', ip=f'10.0.{x + 1}.11/24'))
            servers.append(self.addHost(f'h{x + 1}', ip=f'10.0.0.{x + 1}/24'))
            server_links.append(self.addLink(servers[x], leaf_switches[x]))
            for spine in spine_switches:
                self.addLink(spine, leaf_switches[x], bw=10, delay='10ms')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--spine', dest='spine', default=2, type=int,
                        help='Number of spine switches (default 2)')
    parser.add_argument('-l', '--leaf', dest='leaf', default=2, type=int,
                        help='Number of leaf switches (default 2)')
    args = parser.parse_args()

    ryu_controller = RemoteController('ryu', ip='127.0.0.1', port=6633)
    topo = Topology()
    net = Mininet(switch=OVSSwitch, link=TCLink, topo=topo, controller=ryu_controller, autoSetMacs=True)

    for host in net.hosts:
        host.cmd("sysctl -w net.ipv6.conf.all.disable_ipv6=1")
        host.cmd("sysctl -w net.ipv6.conf.default.disable_ipv6=1")
        host.cmd("sysctl -w net.ipv6.conf.lo.disable_ipv6=1")

    for switch in net.switches:
        switch.cmd("sysctl -w net.ipv6.conf.all.disable_ipv6=1")
        switch.cmd("sysctl -w net.ipv6.conf.default.disable_ipv6=1")
        switch.cmd("sysctl -w net.ipv6.conf.lo.disable_ipv6=1")

    net.start()
    CLI(net)
    net.stop()

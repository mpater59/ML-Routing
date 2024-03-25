import argparse

from mininet.net import Mininet
from mininet.cli import CLI
from mininet.node import RemoteController, OVSSwitch
from mininet.link import TCLink
from mininet.topolib import Topo


class Topology(Topo):
    def build(self):
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')
        s3 = self.addSwitch('s3')
        s4 = self.addSwitch('s4')
        s5 = self.addSwitch('s5')

        self.addLink(s1, s2, bw=10, delay='10ms')
        self.addLink(s1, s3, bw=10, delay='5ms')
        self.addLink(s1, s4, bw=15, delay='15ms')
        self.addLink(s3, s4, bw=15, delay='15ms')
        self.addLink(s4, s2, bw=5, delay='5ms')
        self.addLink(s3, s5, bw=5, delay='5ms')
        self.addLink(s5, s4, bw=5, delay='5ms')


if __name__ == '__main__':
    ryu_controller = RemoteController('ryu', ip='127.0.0.1', port=6633)
    topo = Topology()
    net = Mininet(switch=OVSSwitch, link=TCLink, topo=topo, controller=ryu_controller, autoSetMacs=True)

    net.start()
    CLI(net)
    net.stop()

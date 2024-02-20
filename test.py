from mininet.cli import CLI
from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController
from mininet.log import setLogLevel


def create_topology():
    net = Mininet(controller=RemoteController, switch=OVSSwitch)

    c0 = net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)

    h1 = net.addHost('h1', ip='10.0.0.1/24')
    h2 = net.addHost('h2', ip='10.0.0.2/24')
    h3 = net.addHost('h3', ip='10.0.0.3/24')
    h4 = net.addHost('h4', ip='10.0.0.4/24')

    s1 = net.addSwitch('s1')
    s2 = net.addSwitch('s2')

    net.addLink(h1, s1)
    net.addLink(h2, s1)
    net.addLink(h3, s2)
    net.addLink(h4, s2)
    net.addLink(s1, s2)

    net.start()
    s1.cmd('ovs-vsctl add-port s1 s1-vxlan1 -- set interface s1-vxlan1 type=vxlan options:remote_ip=10.0.0.3 options:key=100')
    s1.cmd('ovs-vsctl add-port s1 s1-vxlan2 -- set interface s1-vxlan2 type=vxlan options:remote_ip=10.0.0.3 options:key=200')

    s2.cmd('ovs-vsctl add-port s2 s2-vxlan1 -- set interface s2-vxlan1 type=vxlan options:remote_ip=10.0.0.1 options:key=100')
    s2.cmd('ovs-vsctl add-port s2 s2-vxlan2 -- set interface s2-vxlan2 type=vxlan options:remote_ip=10.0.0.1 options:key=200')
    CLI(net)
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    create_topology()

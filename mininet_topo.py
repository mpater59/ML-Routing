import argparse

from mininet.net import Mininet
from mininet.cli import CLI
from mininet.node import RemoteController, OVSSwitch
from mininet.link import TCLink


# parser = argparse.ArgumentParser()
# parser.add_argument('-s', '--spine', dest='spine', default=2, type=int,
#                     help='Number of spine switches (default 2)')
# parser.add_argument('-l', '--leaf', dest='leaf', default=4, type=int,
#                     help='Number of leaf switches (default 4)')
# parser.add_argument('-ht', '--host', dest='host', default=3, type=int,
#                     help='Number of hosts (default 3)')
# args = parser.parse_args()
#
# ryu_controller = RemoteController('ryu', ip='127.0.0.1', port=6633)
# net = Mininet(switch=OVSSwitch, link=TCLink, autoSetMacs=True, autoStaticArp=True)
#
# s1 = net.addSwitch('s1')
#
# spine_switches = []
# leaf_switches = []
# servers = []
# hosts = []
# host_links = []
# server_links = []
#
# index = 1
#
# for x in range(args.host):
#     # hosts.append(net.addHost(f'h{x + 1}', ip=f'192.168.{x + 1}.11/24'))
#     hosts.append(net.addHost(f'h{x + 1}', ip=f'10.0.0.{index}/24'))
#     index += 1
#     host_links.append(net.addLink(hosts[x], s1))
#
# for x in range(args.spine):
#     spine_switches.append(net.addSwitch(f's{x + 2}'))
#     net.addLink(s1, spine_switches[x], bw=10, delay='10ms', loss=0, max_queue_size=10000)
#
# for x in range(args.leaf):
#     leaf_switches.append(net.addSwitch(f's{x + 2 + args.spine}'))
#     # servers.append(net.addHost(f'h{x + 1 + args.host}', ip=f'10.0.{x + 1}.11/24'))
#     servers.append(net.addHost(f'h{x + 1 + args.host}', ip=f'10.0.0.{index}/24'))
#     index += 1
#     server_links.append(net.addLink(servers[x], leaf_switches[x]))
#     for spine in spine_switches:
#         net.addLink(spine, leaf_switches[x], bw=10, delay='10ms', loss=0, max_queue_size=10000)
#
# net.addController(ryu_controller)
#
# net.start()
#
# for host, link in zip(hosts, host_links):
#     host.setDefaultRoute(intf=link.intf1)
# for server, link in zip(servers, server_links):
#     server.setDefaultRoute(intf=link.intf1)

ryu_controller = RemoteController('ryu', ip='127.0.0.1', port=6633)
net = Mininet(switch=OVSSwitch, link=TCLink)

net.addSwitch('s1', protocols='OpenFlow13')
net.addSwitch('s2', protocols='OpenFlow13')

net.addHost('h1', ip='10.0.0.1/24')
net.addHost('h2', ip='10.0.0.2/24')

net.addLink('h1', 's1', bw=10, delay='10ms')
net.addLink('s1', 's2', bw=10, delay='10ms')
net.addLink('s2', 'h2', bw=10, delay='10ms')

CLI(net)

net.stop()

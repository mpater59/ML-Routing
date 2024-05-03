import json
import math
import ipaddress

from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.lib import dpid as dpid_lib
from ryu.controller import ofp_event, dpset
from ryu.controller.handler import set_ev_cls, CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.lib.packet import packet, ethernet, ether_types, arp, ipv4
from ryu.app.wsgi import WSGIApplication, ControllerBase, route


# GLOBAL VARIABLES
ospf = {'links': [], 'networks': [], 'paths': {}, 'routing tables': {}}
sw_info_type = []
sw_mac_to_port = {}
routers = {}


def _get_network(dpid):
    for network in ospf['networks']:
        if network['dpid'] == dpid:
            return network['network']


class RestController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(RestController, self).__init__(req, link, data, **config)
        self.rest_controller = data['rest_controller']
        self.dpset = self.rest_controller.dpset
        self.waiters = self.rest_controller.waiters

    @route('set_switch_type', '/switch/{dpid}', methods=['POST'],
           requirements={'dpid': dpid_lib.DPID_PATTERN})
    def set_switch_type(self, req, **kwargs):
        data = json.loads(req.body)
        dpid = dpid_lib.str_to_dpid(kwargs['dpid'])
        if 'type' in data:
            if data['type'] == 'router' and 'ip address' in data and 'mac address' in data:
                sw_info_type.append({'dpid': dpid, 'type': 'router'})
                routers[dpid] = {'ip address': data['ip address'], 'mac address': data['mac address'], 'arp': {},
                                 'queue': []}
            elif data['type'] == 'switch':
                sw_info_type.append({'dpid': dpid, 'type': 'switch'})
                sw_mac_to_port[dpid] = {}
            else:
                return "Wrong JSON body\n"
        else:
            return "Wrong JSON body\n"

    @route('get_switch_type', '/switch/{dpid}', methods=['GET'],
           requirements={'dpid': dpid_lib.DPID_PATTERN})
    def get_switch_type(self, req, **kwargs):
        dpid = dpid_lib.str_to_dpid(kwargs['dpid'])
        for switch in sw_info_type:
            if dpid == switch['dpid']:
                if switch['type'] == 'router':
                    return f"Switch {dpid} is router\n"
                else:
                    return f"Switch {dpid} is host network switch\n"
        return "Unknown DPID\n"

    @route('set_ospf_link', '/ospf/link', methods=['POST'])
    def set_ospf_link(self, req, **kwargs):
        data = json.loads(req.body)
        if data is not list and 'sw1' in data and 'sw2' in data and 'metric' in data:
            self._set_ospf_link(data['sw1'], data['sw2'], data['metric'])
        elif data is list:
            for element in data:
                if 'sw1' in element and 'sw2' in element and 'metric' in element:
                    self._set_ospf_link(element['sw1'], element['sw2'], element['metric'])
                else:
                    return "Wrong JSON body\n"
        else:
            return "Wrong JSON body\n"

    @route('set_ospf_network', '/ospf/network/switch/{dpid}', methods=['POST'],
           requirements={'dpid': dpid_lib.DPID_PATTERN})
    def set_ospf_network(self, req, **kwargs):
        data = json.loads(req.body)
        dpid = dpid_lib.str_to_dpid(kwargs['dpid'])
        if 'network' in data:
            self._set_ospf_network(dpid, data['network'])
        else:
            return f"Wrong JSON body\n"

    @route('set_ospf', '/ospf', methods=['POST'])
    def set_ospf(self, req, **kwargs):
        data = json.loads(req.body)
        if 'enable' in data:
            if data['enable'] is True:
                self._set_ospf()
        else:
            return f"Wrong JSON body\n"

    @route('get_ospf', '/ospf', methods=['GET'])
    def get_ospf(self, req, **kwargs):
        output = "OSPF info\n"
        for key, value in ospf.items():
            if key == 'links':
                output += "Links:\n"
                for link in value:
                    output += f"{link}\n"
            else:
                output += f"{key}: {value}\n"
        return output

    @route('get_mac_to_port', '/mac', methods=['GET'])
    def get_mac_to_port(self, req, **kwargs):
        output = "MAC to port info\n"
        for key, value in sw_mac_to_port.items():
            output += f"{key}: {value}\n"
        return output

    @route('get_sw_info', '/switch/info', methods=['GET'])
    def get_sw_info(self, req, **kwargs):
        output = "Switch info\n"
        for info in sw_info_type:
            output += f"{info}\n"
        return output

    @route('get_routers_info', '/routers', methods=['GET'])
    def get_routers_info(self, req, **kwargs):
        output = "Routers info\n"
        for key, value in routers.items():
            output += f"{key}: {value}\n"
        return output

    @staticmethod
    def _set_ospf_link(sw1, sw2, metric):
        link_exists = False

        sw1_dpid = dpid_lib.str_to_dpid(sw1['dpid'])
        sw2_dpid = dpid_lib.str_to_dpid(sw2['dpid'])

        if sw1_dpid not in routers or sw2_dpid not in routers:
            return "Entered DPID does not belong to routers!\n"

        for link in ospf['links']:
            if (((link['sw1']['dpid'] == sw1_dpid) and (link['sw2']['dpid'] == sw2_dpid)) or
                    ((link['sw1']['dpid'] == sw2_dpid) and (link['sw2']['dpid'] == sw1_dpid))):
                link['sw1']['dpid'] = sw1_dpid
                link['sw2']['dpid'] = sw2_dpid

                link['sw1']['port'] = sw1['port']
                link['sw2']['port'] = sw2['port']

                link['metric'] = metric
                link_exists = True
                break
        if link_exists is False:
            ospf['links'].append({'sw1': {'dpid': sw1_dpid, 'port': sw1['port']},
                                  'sw2': {'dpid': sw2_dpid, 'port': sw2['port']},
                                  'metric': metric})

    @staticmethod
    def _set_ospf_network(dpid, network):
        network_exists = False
        for element in ospf['networks']:
            if element['dpid'] == dpid:
                element['network'] = network
                network_exists = True
                break
        if network_exists is False:
            ospf['networks'].append({'dpid': dpid, 'network': network})

    def _set_ospf(self):
        for switch in sw_info_type:
            if switch['type'] == 'router':
                s_dpid = switch['dpid']
                ospf['paths'][s_dpid] = self._dijkstra_algorithm(s_dpid)
                ospf['routing tables'][s_dpid] = self._set_routing_table(s_dpid)
                for network in ospf['networks']:
                    d_dpid = network['dpid']
                    if d_dpid != s_dpid:
                        port = self._get_route_port(s_dpid, ospf['routing tables'][s_dpid][d_dpid])
                        self._add_flow_network(s_dpid, port, _get_network(d_dpid))

    def _dijkstra_algorithm(self, s_dpid):
        unvisited_nodes = []
        path_cost = {}
        prev_node = {}
        for switch in sw_info_type:
            if switch['type'] == 'router' and switch['dpid'] != s_dpid:
                unvisited_nodes.append(switch['dpid'])
                link_cost = self._link_cost(s_dpid, switch['dpid'])
                path_cost[switch['dpid']] = link_cost
                if link_cost != math.inf:
                    prev_node[switch['dpid']] = s_dpid
                else:
                    prev_node[switch['dpid']] = None

        while len(unvisited_nodes) != 0:
            current_min_path = math.inf
            visiting_node = None
            for node in unvisited_nodes:
                if path_cost[node] < current_min_path:
                    current_min_path = path_cost[node]
                    visiting_node = node
            unvisited_nodes.remove(visiting_node)

            adj_nodes = []
            for node in unvisited_nodes:
                if self._link_cost(visiting_node, node) != math.inf:
                    adj_nodes.append(node)
            for adj_node in adj_nodes:
                new_cost = path_cost[visiting_node] + self._link_cost(visiting_node, adj_node)
                if path_cost[adj_node] > new_cost:
                    path_cost[adj_node] = new_cost
                    prev_node[adj_node] = visiting_node
        return prev_node

    @staticmethod
    def _link_cost(dpid1, dpid2):
        for link in ospf['links']:
            if (link['sw1']['dpid'] == dpid1 and link['sw2']['dpid'] == dpid2) or (link['sw1']['dpid'] == dpid2 and
                                                                                   link['sw2']['dpid'] == dpid1):
                return link['metric']
        return math.inf

    @staticmethod
    def _set_routing_table(dpid):
        paths = ospf['paths'][dpid]
        routing_table = {}
        for d_dpid, prev_node in paths.items():
            via_node = d_dpid
            while prev_node != dpid:
                for d_dpid_temp, prev_node_temp in paths.items():
                    if d_dpid_temp == prev_node:
                        prev_node = prev_node_temp
                        via_node = d_dpid_temp
                        break
            routing_table[d_dpid] = via_node
        return routing_table

    @staticmethod
    def _get_route_port(s_dpid, d_dpid):
        for link in ospf['links']:
            if (link['sw1']['dpid'] == s_dpid and link['sw2']['dpid'] == d_dpid) or (link['sw1']['dpid'] == d_dpid and
                                                                                     link['sw2']['dpid'] == s_dpid):
                if link['sw1']['dpid'] == s_dpid:
                    return link['sw1']['port']
                else:
                    return link['sw2']['port']

    def _add_flow_network(self, dpid, output_port, network_route):
        dp = self.dpset.get(dpid)
        ofproto = dp.ofproto
        parser = dp.ofproto_parser

        match = parser.OFPMatch(eth_type=0x0800, ipv4_dst=network_route)
        priority = 100
        actions = [parser.OFPActionOutput(port=output_port)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=dp, priority=priority, match=match, command=ofproto.OFPFC_ADD,
                                instructions=inst)
        dp.send_msg(mod)


class RestControllerAPI(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    _CONTEXTS = {'dpset': dpset.DPSet,
                 'wsgi': WSGIApplication}

    def __init__(self, *args, **kwargs):
        super(RestControllerAPI, self).__init__(*args, **kwargs)
        self.dpset = kwargs['dpset']
        self.waiters = {}
        self.data = {}
        self.data['dpset'] = self.dpset
        self.data['waiters'] = self.waiters

        wsgi = kwargs['wsgi']
        wsgi.register(RestController, {'rest_controller': self})

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        dp = ev.msg.datapath
        ofproto = dp.ofproto
        parser = dp.ofproto_parser

        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=dp, priority=0, match=match, instructions=inst)
        dp.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        in_port = msg.match['in_port']
        pkt = packet.Packet(msg.data)
        eth_pkt = pkt.get_protocols(ethernet.ethernet)[0]

        if (eth_pkt.ethertype == ether_types.ETH_TYPE_LLDP) or (eth_pkt.ethertype == ether_types.ETH_TYPE_IPV6):
            return

        print('Correct!')
        print(f'dp.id: {dp.id}')
        print(f'pkt: {pkt}')
        print(f'in_port: {in_port}')
        print()
        if dp.id in routers:
            if eth_pkt.ethertype == ether_types.ETH_TYPE_ARP and in_port == 1:
                arp_pkt = pkt.get_protocol(arp.arp)
                routers[dp.id]['arp'][arp_pkt.src_ip] = arp_pkt.src_mac
                if arp_pkt.opcode == arp.ARP_REQUEST and arp_pkt.dst_ip == routers[dp.id]['ip address']:
                    self._arp_request_handler_router(dp.id, arp_pkt)
            elif eth_pkt.ethertype == ether_types.ETH_TYPE_IP:
                ip_pkt = pkt.get_protocol(ipv4.ipv4)
                if in_port == 1:
                    routers[dp.id]['arp'][ip_pkt.src] = eth_pkt.src
                self._ip_handler_router(dp.id, pkt)
            self._send_packet_in_queue(dp.id)
        elif self._check_if_switch(dp.id) is True:
            sw_mac_to_port[dp.id][eth_pkt.src] = in_port
            if eth_pkt.ethertype == ether_types.ETH_TYPE_IP:
                self._ip_handler_switch(dp.id, pkt, in_port)
            elif eth_pkt.ethertype == ether_types.ETH_TYPE_ARP:
                self._other_handler_switch(dp.id, pkt, in_port)

    @staticmethod
    def _check_if_switch(dpid):
        for switch in sw_info_type:
            if switch['dpid'] == dpid:
                if switch['type'] == 'switch':
                    return True
                else:
                    return False
        return False

    def _arp_request_handler_router(self, dpid, arp_packet):
        dp = self.dpset.get(dpid)
        ofproto = dp.ofproto
        parser = dp.ofproto_parser

        src_mac = routers[dpid]['mac address']
        src_ip = routers[dpid]['ip address']
        dst_mac = arp_packet.src_mac
        dst_ip = arp_packet.src_ip

        eth_replay = ethernet.ethernet(dst=dst_mac, src=src_mac, ethertype=ether_types.ETH_TYPE_ARP)
        arp_replay = arp.arp(opcode=arp.ARP_REPLY, src_mac=src_mac, src_ip=src_ip, dst_mac=dst_mac, dst_ip=dst_ip)
        replay_pkt = packet.Packet()
        replay_pkt.add_protocol(eth_replay)
        replay_pkt.add_protocol(arp_replay)
        print('_arp_request_handler_router')
        print(replay_pkt)
        replay_pkt.serialize()
        print(replay_pkt)
        print()

        actions = [parser.OFPActionOutput(port=1)]
        req = parser.OFPPacketOut(datapath=dp, in_port=ofproto.OFPP_CONTROLLER, actions=actions, data=replay_pkt,
                                  buffer_id=ofproto.OFP_NO_BUFFER)
        dp.send_msg(req)

    def _ip_handler_router(self, dpid, pkt):
        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        if ip_pkt.dst in routers[dpid]['arp']:
            eth_pkt = pkt.get_protocol(ethernet.ethernet)
            eth_pkt.src = routers[dpid]['mac address']
            eth_pkt.dst = routers[dpid]['arp'][ip_pkt.dst]
            print('_ip_handler_router')
            print(pkt)
            pkt.serialize()
            print(pkt)
            print()
            self._send_packet(dpid, 1, pkt)
            self._add_flow_router(dpid, ip_pkt.dst)
        else:
            if ipaddress.ip_address(ip_pkt.dst) in ipaddress.ip_network(_get_network(dpid)):
                self._send_arp_request(dpid, ip_pkt.dst)
                routers[dpid]['queue'].append({'ip address': ip_pkt.dst, 'packet': pkt})

    def _ip_handler_switch(self, dpid, pkt, in_port):
        eth_pkt = pkt.get_protocol(ethernet.ethernet)
        if eth_pkt.dst in sw_mac_to_port[dpid]:
            ip_pkt = pkt.get_protocol(ipv4.ipv4)
            self._send_packet(dpid, sw_mac_to_port[dpid][eth_pkt.dst], pkt)
            self._add_flow_switch(dpid, eth_pkt.src, eth_pkt.dst, ip_pkt.src, ip_pkt.dst,
                                  sw_mac_to_port[dpid][eth_pkt.dst])
        else:
            dp = self.dpset.get(dpid)
            ofproto = dp.ofproto
            self._send_packet(dpid, ofproto.OFPP_FLOOD, pkt, in_port)

    def _other_handler_switch(self, dpid, pkt, in_port):
        eth_pkt = pkt.get_protocol(ethernet.ethernet)
        if eth_pkt.dst in sw_mac_to_port[dpid]:
            self._send_packet(dpid, sw_mac_to_port[dpid][eth_pkt.dst], pkt)
        else:
            dp = self.dpset.get(dpid)
            ofproto = dp.ofproto
            self._send_packet(dpid, ofproto.OFPP_FLOOD, pkt, in_port)

    def _send_arp_request(self, dpid, ip_dst):
        dp = self.dpset.get(dpid)
        ofproto = dp.ofproto
        parser = dp.ofproto_parser

        src_mac = routers[dpid]['mac address']
        src_ip = routers[dpid]['ip address']
        dst_mac = 'ff:ff:ff:ff:ff:ff'
        dst_ip = ip_dst

        eth_replay = ethernet.ethernet(dst=dst_mac, src=src_mac, ethertype=ether_types.ETH_TYPE_ARP)
        arp_replay = arp.arp(opcode=arp.ARP_REQUEST, src_mac=src_mac, src_ip=src_ip, dst_mac=dst_mac, dst_ip=dst_ip)
        replay_pkt = packet.Packet()
        replay_pkt.add_protocol(eth_replay)
        replay_pkt.add_protocol(arp_replay)
        print('_send_arp_request')
        print(replay_pkt)
        replay_pkt.serialize()
        print(replay_pkt)
        print()

        actions = [parser.OFPActionOutput(port=1)]
        req = parser.OFPPacketOut(datapath=dp, in_port=ofproto.OFPP_CONTROLLER, actions=actions, data=replay_pkt,
                                  buffer_id=ofproto.OFP_NO_BUFFER)
        dp.send_msg(req)

    def _send_packet_in_queue(self, dpid):
        print()
        print('_send_packet_in_queue\n')
        del_packets = []
        for q_packet in routers[dpid]['queue']:
            print(f'q_packet: {q_packet}')
            print(f"routers[dpid]['arp']: {routers[dpid]['arp']}\n")
            if q_packet['ip address'] in routers[dpid]['arp']:
                pkt = q_packet['packet']
                eth_pkt = pkt.get_protocol(ethernet.ethernet)
                ip_pkt = pkt.get_protocol(ipv4.ipv4)
                eth_pkt.src = routers[dpid]['mac address']
                eth_pkt.dst = routers[dpid]['arp'][ip_pkt.dst]
                print('_send_packet_in_queue')
                print(pkt)
                pkt.serialize()
                print(pkt)
                print()
                self._send_packet(dpid, 1, pkt)
                self._add_flow_router(dpid, q_packet['ip address'])
                del_packets.append(q_packet)
        for del_packet in del_packets:
            routers[dpid]['queue'].remove(del_packet)

    def _send_packet(self, dpid, out_port, pkt, in_port=None):
        dp = self.dpset.get(dpid)
        ofproto = dp.ofproto
        parser = dp.ofproto_parser

        if in_port is None:
            in_port = ofproto.OFPP_CONTROLLER

        data = pkt
        actions = [parser.OFPActionOutput(out_port)]
        req = parser.OFPPacketOut(datapath=dp, in_port=in_port, actions=actions, data=data,
                                  buffer_id=ofproto.OFP_NO_BUFFER)
        dp.send_msg(req)

    def _add_flow_router(self, dpid, dst_ip):
        dp = self.dpset.get(dpid)
        ofproto = dp.ofproto
        parser = dp.ofproto_parser

        src_mac = routers[dpid]['mac address']
        dst_mac = routers[dpid]['arp'][dst_ip]

        match = parser.OFPMatch(eth_type=0x0800, ipv4_dst=dst_ip)
        actions = [parser.OFPActionSetField(eth_src=src_mac), parser.OFPActionSetField(eth_dst=dst_mac),
                   parser.OFPActionOutput(port=1)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=dp, priority=100, match=match, instructions=inst,
                                command=ofproto.OFPFC_ADD)
        dp.send_msg(mod)

    def _add_flow_switch(self, dpid, src_mac, dst_mac, src_ip, dst_ip, out_port):
        dp = self.dpset.get(dpid)
        ofproto = dp.ofproto
        parser = dp.ofproto_parser

        match = parser.OFPMatch(eth_src=src_mac, eth_dst=dst_mac, eth_type=0x0800, ipv4_src=src_ip, ipv4_dst=dst_ip)
        actions = [parser.OFPActionOutput(port=out_port)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=dp, priority=100, match=match, instructions=inst,
                                command=ofproto.OFPFC_ADD)
        dp.send_msg(mod)

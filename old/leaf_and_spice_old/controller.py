import json

from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.lib import ofctl_v1_3
from ryu.app.wsgi import ControllerBase
from ryu.lib import dpid as dpid_lib
from ryu.controller.handler import set_ev_cls
from ryu.controller import ofp_event, dpset
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.lib.packet import packet, ethernet, ether_types, arp, ipv4
from ryu.app.wsgi import WSGIApplication, ControllerBase, route
from ryu.app.wsgi import Response
from ryu.exception import OFPUnknownVersion
from ryu.lib import hub
from ryu.exception import RyuException


leaf_switches = {}
spine_switches = []
vxlan = {}
ofctl = ofctl_v1_3


class RestController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(RestController, self).__init__(req, link, data, **config)
        self.rest_controller = data['rest_controller']
        self.dpset = self.rest_controller.dpset
        self.waiters = self.rest_controller.waiters

    @route('set_switch', '/switch/{dpid}', methods=['POST'],
           requirements={'dpid': dpid_lib.DPID_PATTERN})
    def set_switch(self, req, **kwargs):
        data = json.loads(req.body)
        dpid = dpid_lib.str_to_dpid(kwargs['dpid'])
        if 'type' in data:
            if 'leaf' == data['type']:
                self._add_leaf(dpid)
                return f'Leaf switches: {leaf_switches}\n'
            elif 'spine' == data['type']:
                self._add_spine(dpid)
                return f'Spine switches ID: {spine_switches}\n'
            else:
                return f'Wrong JSON body\n'
        else:
            return f'Wrong JSON body\n'

    @route('get_switch', '/switch/{dpid}', methods=['GET'],
           requirements={'dpid': dpid_lib.DPID_PATTERN})
    def get_switch(self, req, **kwargs):
        dpid = dpid_lib.str_to_dpid(kwargs['dpid'])
        if dpid in leaf_switches:
            return f"Switch {dpid} is leaf switch, ID: {leaf_switches[dpid]['id']}\n"
        elif dpid in spine_switches:
            return f"Switch {dpid} is spine switch\n"

    @route('set_vxlan', '/switch/{dpid}/vxlan', methods=['POST'],
           requirements={'dpid': dpid_lib.DPID_PATTERN})
    def set_vxlan(self, req, **kwargs):
        data = json.loads(req.body)
        dpid = dpid_lib.str_to_dpid(kwargs['dpid'])
        if 'vni' in data and 'port' in data:
            vni = data['vni']
            if vni not in vxlan:
                vxlan[vni] = {'switches': []}
            for switch in vxlan[vni]['switches']:
                if dpid == switch['id']:
                    switch['port'] = data['port']
                    return f"Configured VxLAN: {vxlan}\n"
            vxlan[vni]['switches'].append({'id': dpid, 'port': data['port'], 'mac_addr': []})
            return f"Configured VxLAN: {vxlan}\n"
        else:
            return f'Wrong JSON body\n'

    def _add_leaf(self, dpid):
        if dpid not in leaf_switches:
            leaf_id = len(leaf_switches) + 1
            leaf_switches[dpid] = {'id': leaf_id}
            for spine_switch in spine_switches:
                self._add_flow_spine(spine_switch, leaf_id, f'{leaf_id}.{leaf_id}.0.0/16')

    def _add_spine(self, dpid):
        if dpid not in spine_switches:
            spine_switches.append(dpid)
        for switch_id in leaf_switches:
            leaf_id = leaf_switches[switch_id]['id']
            self._add_flow_spine(dpid, leaf_id, f'{leaf_id}.{leaf_id}.0.0/16')

    def _add_flow_spine(self, dpid, output_port, network_route):
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

        # update mac tables
        if dp.id in leaf_switches:
            for vni in vxlan:
                for switch in vxlan[vni]['switches']:
                    if switch['id'] == dp.id and switch['port'] == in_port:
                        if eth_pkt.src not in switch['mac_addr']:
                            RestControllerAPI._update_mac_table(dp.id, vni, eth_pkt.src)

                        if eth_pkt and eth_pkt.ethertype == ether_types.ETH_TYPE_ARP:
                            arp_pkt = pkt.get_protocol(arp.arp)
                            # arp request handler
                            if arp_pkt.opcode == arp.ARP_REQUEST:
                                self._arp_request_handler(dp, pkt, vni)
                            # arp reply handler
                            elif arp_pkt.opcode == arp.ARP_REPLY:
                                self._arp_reply_handler(pkt, vni)
                        # handle IP traffic
                        elif eth_pkt and eth_pkt.ethertype == ether_types.ETH_TYPE_IP:
                            self._ip_traffic_handler(dp, pkt, vni, in_port)

    @staticmethod
    def _update_mac_table(dpid, vni, mac_addr):
        for switch in vxlan[vni]['switches']:
            if dpid != switch['id']:
                if mac_addr in switch['mac_addr']:
                    switch['mac_addr'].remove(mac_addr)
            else:
                if mac_addr not in switch['mac_addr']:
                    switch['mac_addr'].append(mac_addr)
        print(f"Updated mac addresses for VNI {vni}: {vxlan[vni]}")

    def _arp_request_handler(self, datapath, pkt, vni):
        for switch in vxlan[vni]['switches']:
            if switch['id'] != datapath.id:
                dp = self.dpset.get(switch['id'])
                ofproto = dp.ofproto
                parser = dp.ofproto_parser

                pkt.serialize()
                port = switch['port']

                actions = [parser.OFPActionOutput(port=port)]
                req = parser.OFPPacketOut(datapath=dp, in_port=ofproto.OFPP_CONTROLLER, actions=actions, data=pkt,
                                          buffer_id=ofproto.OFP_NO_BUFFER)
                dp.send_msg(req)

    def _arp_reply_handler(self, pkt, vni):
        eth_pkt = pkt.get_protocols(ethernet.ethernet)[0]
        eth_dst = eth_pkt.dst

        for switch in vxlan[vni]['switches']:
            if eth_dst in switch['mac_addr']:
                dp = self.dpset.get(switch['id'])
                ofproto = dp.ofproto
                parser = dp.ofproto_parser

                pkt.serialize()
                port = switch['port']

                actions = [parser.OFPActionOutput(port=port)]
                req = parser.OFPPacketOut(datapath=dp, in_port=ofproto.OFPP_CONTROLLER, actions=actions, data=pkt,
                                          buffer_id=ofproto.OFP_NO_BUFFER)
                dp.send_msg(req)

    def _ip_traffic_handler(self, datapath, pkt, vni, in_port):
        eth_pkt = pkt.get_protocols(ethernet.ethernet)[0]
        eth_dst = eth_pkt.dst
        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        ip_dst = ip_pkt.dst

        for switch in vxlan[vni]['switches']:
            if eth_dst in switch['mac_addr']:
                # add flow rule for source leaf switch
                dp = self.dpset.get(datapath.id)
                ofproto = dp.ofproto
                parser = dp.ofproto_parser
                leaf_id = leaf_switches[switch['id']]['id']

                match = parser.OFPMatch(eth_type=0x0800, in_port=in_port, eth_dst=eth_dst)
                actions = [parser.OFPActionSetField(ipv4_dst=f'{leaf_id}.{leaf_id}.0.{vni}'),
                           parser.OFPActionOutput(port=1)]
                inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
                mod = parser.OFPFlowMod(datapath=dp, priority=100, match=match, instructions=inst,
                                        command=ofproto.OFPFC_ADD)
                dp.send_msg(mod)

                # add flow rule for destination leaf switch
                dp = self.dpset.get(switch['id'])
                ofproto = dp.ofproto
                parser = dp.ofproto_parser

                port = switch['port']
                match = parser.OFPMatch(eth_type=0x0800, ipv4_dst=f'{leaf_id}.{leaf_id}.0.{vni}')
                actions = [parser.OFPActionSetField(ipv4_dst=ip_dst),
                           parser.OFPActionOutput(port=port)]
                inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
                mod = parser.OFPFlowMod(datapath=dp, priority=100, match=match, instructions=inst,
                                        command=ofproto.OFPFC_ADD)
                dp.send_msg(mod)

                # output IP packet
                dp = self.dpset.get(datapath.id)
                ofproto = dp.ofproto
                parser = dp.ofproto_parser
                leaf_id = leaf_switches[switch['id']]['id']

                pkt.serialize()
                actions = [parser.OFPActionSetField(ipv4_dst=f'{leaf_id}.{leaf_id}.0.{vni}'),
                           parser.OFPActionOutput(port=1)]
                req = parser.OFPPacketOut(datapath=dp, in_port=ofproto.OFPP_CONTROLLER, actions=actions, data=pkt,
                                          buffer_id=ofproto.OFP_NO_BUFFER)
                dp.send_msg(req)
                break

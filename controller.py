import json
import logging

from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.lib import ofctl_v1_3
from ryu.app.wsgi import ControllerBase
from ryu.lib import dpid as dpid_lib
from ryu.controller.handler import set_ev_cls
from ryu.controller import ofp_event, dpset
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
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
                print(f'Leaf switches: {leaf_switches}')
            elif 'spine' == data['type']:
                self._add_spine(dpid)
                print(f'Spine switches ID: {spine_switches}')

    @route('get_switch', '/switch/{dpid}', methods=['GET'],
           requirements={'dpid': dpid_lib.DPID_PATTERN})
    def get_switch(self, req, **kwargs):
        dpid = dpid_lib.str_to_dpid(kwargs['dpid'])
        if dpid in leaf_switches:
            return f"Switch {dpid} is leaf switch, ID: {leaf_switches[dpid]['id']}"
        elif dpid in spine_switches:
            return f"Switch {dpid} is spine switch"

    def _add_leaf(self, dpid):
        if dpid not in leaf_switches:
            leaf_id = len(leaf_switches) + 1
            leaf_switches[dpid] = {'id': leaf_id}
            for spine_switch in spine_switches:
                self._add_flow_spine(spine_switch, leaf_id, f'{leaf_id}.{leaf_id}.{leaf_id}.0/24')

    def _add_spine(self, dpid):
        if dpid not in spine_switches:
            spine_switches.append(dpid)
        for switch_id in leaf_switches:
            leaf_id = leaf_switches[switch_id]['id']
            self._add_flow_spine(dpid, leaf_id, f'{leaf_id}.{leaf_id}.{leaf_id}.0/24')

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





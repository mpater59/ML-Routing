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


class NotFoundError(RyuException):
    message = 'Switch is not connected: switch_id=%(switch_id)s'


def rest_command(func):
    def _wrapper(*args, **kwargs):
        try:
            print(*args)
            print(**kwargs)
            msg = func(*args, **kwargs)
            return Response(content_type='application/json',
                            body=json.dumps(msg))

        except SyntaxError as e:
            status = 400
            details = e.msg
        except (ValueError, NameError) as e:
            status = 400
            details = e.message

        except NotFoundError as msg:
            status = 404
            details = str(msg)

        msg = {'result': 'failure',
               'details': details}
        return Response(status=status, body=json.dumps(msg))

    return _wrapper


class RestController(ControllerBase):

    # _LOGGER = None
    _SWITCHES = []

    def __init__(self, req, link, data, **config):
        super(RestController, self).__init__(req, link, data, **config)
        self.rest_controller = data['rest_controller']
        print(data)
        # self.dpset = data['dpset']
        # self.waiters = data['waiters']

    # @classmethod
    # def register_switch(cls, dp):
    #     if dp not in cls._SWITCHES:
    #         cls._SWITCHES.append(dp)

    # @classmethod
    # def set_logger(cls, logger):
    #     cls._LOGGER = logger
    #     cls._LOGGER.propagate = False
    #     hdlr = logging.StreamHandler()
    #     FORMAT = '[%(levelname)s] switch_id=%(sw_id)s: %(message)s'
    #     hdlr.setFormatter(logging.Formatter(FORMAT))
    #     cls._LOGGER.addHandler(hdlr)

    # @classmethod
    # def packet_in_handler(cls, msg):
    #     dp_id = msg.datapath.id
    #     if dp_id in cls._SWITCH_LIST:
    #         switch = cls._SWITCH_LIST[dp_id]
    #         switch.packet_in_handler(msg)

    # @rest_command
    # def set_switch(self, switch_id, req, **kwargs):
    #     data = json.loads(req.body)
    #     if 'type' in data and 'id' in data:
    #         if 'leaf' == data['type']:
    #             self._add_leaf(switch_id)
    #         elif 'spine' == data['type']:
    #             Controller._add_spine(switch_id)

    # @rest_command
    # def del_switch(self, switch_id, req, **kwargs):
    #     if switch_id in leaf_switches:
    #         Controller._del_leaf(switch_id)
    #     elif switch_id in spine_switches:
    #         Controller._del_spine(switch_id)

    @route('set_switch', '/switch/{dpid}', methods=['POST'],
           requirements={'dpid': dpid_lib.DPID_PATTERN})
    def set_switch(self, req, **kwargs):
        data = json.loads(req.body)
        dpid = dpid_lib.str_to_dpid(kwargs['dpid'])
        if 'type' in data:
            if 'leaf' == data['type']:
                self._add_leaf(dpid)
                print(leaf_switches)
            elif 'spine' == data['type']:
                RestController._add_spine(dpid)
                print(spine_switches)

    def _add_leaf(self, dpid):
        if dpid not in leaf_switches:
            leaf_id = len(leaf_switches) + 1
            leaf_switches[dpid] = {'id': leaf_id}
            for spine_switch in spine_switches:
                self._add_flow_spine(spine_switch, leaf_id, f'{leaf_id}.{leaf_id}.{leaf_id}.0/24')

    @staticmethod
    def _add_spine(switch_id):
        if switch_id not in spine_switches:
            spine_switches.append(switch_id)

    def _add_flow_spine(self, dpid, output_port, network_route):
        print(self.rest_controller)
        exit()
        dp = self.dpset.get(dpid)
        print(dp)
        print(dp.id)
        ofproto = dp.ofproto
        parser = dp.ofproto_parser

        match = parser.OFPMatch(ipv4_dst=network_route)
        actions = [parser.OFPActionOutput(output_port)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=dp, match=match, command=ofproto.OFPFC_ADD, instructions=inst)
        dp.send_msg(mod)

    # @staticmethod
    # def _del_leaf(switch_id):
    #     pass



    # @staticmethod
    # def _del_spine(switch_id):
    #     pass


class RestControllerAPI(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    _CONTEXTS = {'dpset': dpset.DPSet,
                 'wsgi': WSGIApplication}

    def __init__(self, *args, **kwargs):
        super(RestControllerAPI, self).__init__(*args, **kwargs)

        # Controller.set_logger(self.logger)

        self.dpset = kwargs['dpset']
        wsgi = kwargs['wsgi']
        self.waiters = {}
        self.data = {}
        self.data['dpset'] = self.dpset
        self.data['waiters'] = self.waiters

        # mapper = wsgi.mapper
        # wsgi.registory['Controller'] = self.data
        wsgi.register(RestController, {'rest_controller': self})

        # # REST functions
        # path = '/switch/{switch_id}'
        # # uri = path + '/data'
        # # mapper.connect('switch', uri, controller=Controller,
        # #                action='get_data',
        # #                conditions=dict(method=['GET']))
        # # uri = path + '/flows'
        # # mapper.connect('switch', uri, controller=Controller,
        # #                action='get_flows',
        # #                conditions=dict(method=['GET']))
        # # uri = path + '/stats'
        # # mapper.connect('switch', uri, controller=Controller,
        # #                action='get_stats',
        # #                conditions=dict(method=['GET']))
        # uri = path
        # mapper.connect('switch', uri, controller=Controller,
        #                action='get_switch',
        #                conditions=dict(method=['GET']))
        # uri = path + '/vxlan'
        # mapper.connect('switch', uri, controller=Controller,
        #                action='get_vxlan',
        #                conditions=dict(method=['GET']))
        # uri = path
        # mapper.connect('switch', uri, controller=Controller,
        #                action='set_switch',
        #                conditions=dict(method=['POST']))
        # uri = path + '/vxlan'
        # mapper.connect('switch', uri, controller=Controller,
        #                action='set_vxlan',
        #                conditions=dict(method=['POST']))
        # # uri = path
        # # mapper.connect('switch', uri, controller=Controller,
        # #                action='del_switch',
        # #                conditions=dict(method=['DELETE']))
        # # uri = path + '/vxlan'
        # # mapper.connect('switch', uri, controller=Controller,
        # #                action='del_vxlan',
        # #                conditions=dict(method=['DELETE']))

    # @set_ev_cls(dpset.EventDP, dpset.DPSET_EV_DISPATCHER)
    # def datapath_handler(self, ev):
    #     if ev.enter:
    #         Controller.register_switch(ev.dp)




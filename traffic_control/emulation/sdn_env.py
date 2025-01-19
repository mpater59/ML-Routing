import time
from typing import Any, SupportsFloat

import gymnasium as gym
import numpy as np
import requests

from gymnasium import spaces
from gymnasium.core import ActType, ObsType

from traffic_control.emulation.topo_paths import get_all_paths
from traffic_control.emulation.topo_paths import get_ospf_paths
from traffic_control.emulation.rt_flow_stats import get_if_index_datasource
from traffic_control.emulation.rt_flow_stats import get_rt_flow_topo
from traffic_control.emulation.rt_flow_stats import get_stats
from traffic_control.emulation.rt_flow_stats import get_current_flows


class SDN_env(gym.Env):
    def __init__(self, topo_info, env_info):
        super(SDN_env, self).__init__()
        self.topo_info = topo_info
        self.env_info = env_info
        self.stop = False

        self.topo_paths = get_all_paths(topo_info)
        self.max_con_value = topo_info['max topo bandwidth'] * 10**3
        self.max_connections = len(topo_info['nodes']) * (len(topo_info['nodes']) - 1) * topo_info['hosts number']
        self.current_connections = [None] * self.max_connections
        self.flow_paths = []
        self.flow_paths_id = {}
        self.ospf_paths = get_ospf_paths(topo_info, env_info)
        for node_a in topo_info['nodes']:
            for node_b in topo_info['nodes']:
                if node_a['name'] == node_b['name']:
                    continue
                topo_paths_info = self.topo_paths[node_a['name']]
                for path_info in topo_paths_info:
                    if path_info['destination node'] == node_b['name']:
                        ospf_path_id = None
                        for i, path in enumerate(path_info['all paths']):
                            if path == self.ospf_paths[f"{node_a['name']}-{node_b['name']}"]:
                                ospf_path_id = i
                                break
                        for i in range(1, topo_info['hosts number'] + 1):
                            self.flow_paths.append(len(path_info['all paths']))
                            flow_name = f"{node_a['name']}h{i}-{node_b['name']}h{i}"
                            self.flow_paths_id[flow_name] = {'id': len(self.flow_paths) - 1,
                                                             'ip src': f"192.168.{node_a['id'] * 10}.{i * 10}",
                                                             'ip dst': f"192.168.{node_b['id'] * 10}.{i * 10}"}
                            if ospf_path_id is not None:
                                self.flow_paths_id[flow_name]['ospf path id'] = ospf_path_id
        self.num_switches = len(topo_info['nodes'])
        self.num_links = len(topo_info['links'])
        self.if_index_datasource = get_if_index_datasource(topo_info, env_info)
        self.rt_flow_topo = get_rt_flow_topo(env_info['rt-flow address'])

        self.action_tuple = ([spaces.Discrete(num_paths) for num_paths in self.flow_paths])
        self.action_space = spaces.MultiDiscrete([num_paths for num_paths in self.flow_paths])
        self.observation_space = spaces.Dict({
            # "switch loads": spaces.Box(low=0, high=1, shape=(self.num_switches,), dtype=np.float32),
            # "link loads": spaces.Box(low=0, high=2, shape=(self.num_links,), dtype=np.float32),
            "connection throughputs": spaces.Box(low=0, high=1, shape=(self.max_connections,), dtype=np.float32),
            "connection paths": spaces.MultiDiscrete(self.flow_paths)
        })
        self.state = self.get_topology_state()

    def reset(self, *, seed: int | None = None, options: dict[str, Any] | None = None) -> tuple[ObsType, dict[str, Any]]:
        self.state = self.get_topology_state()
        return self.state, {}

    def step(self, action: ActType) -> tuple[ObsType, SupportsFloat, bool, bool, dict[str, Any]]:
        from traffic_control.emulation.traffic_control_learning import LOGGER
        # apply new actions
        self.apply_new_action(action)

        # get new topology state
        time.sleep(0.2)  # 0.2
        next_state = self.get_topology_state()

        # calculate rewards
        reward = self.compute_reward(self.state, next_state)

        time.sleep(1)
        next_state = self.get_topology_state()

        # end step
        self.state = next_state
        if self.stop is False:
            done = False
        else:
            done = True
        LOGGER.info(f"Step info - action: {action}")
        LOGGER.info(f"Step info - state: {self.state}")
        LOGGER.info(f"Step info - reward: {reward}")

        returned_state = {"connection throughputs": self.state["connection throughputs"],
                          "connection paths": self.state["connection paths"]}
        return returned_state, reward, done, False, {}

    def get_topology_state(self):
        topo_stats = get_stats(self.topo_info, self.env_info, self.if_index_datasource, self.rt_flow_topo)
        self.get_current_connections()

        con_throughputs = [0] * self.max_connections
        con_paths = [0] * self.max_connections
        for i, current_con in enumerate(self.current_connections):
            if current_con is None:
                con_paths[i] = self.get_ospf_path(i)
                continue
            con_throughputs[i] = current_con['value']
            con_paths[i] = current_con['path']

        state = {
            # "switch loads": topo_stats['switch loads'],
            "link loads": topo_stats['link loads'],
            "connection throughputs": con_throughputs,
            "connection paths": con_paths
        }
        return state

    def get_current_connections(self):
        mn_flows = get_current_flows(self.env_info['rt-flow address'])
        visible_flows = []
        for mn_flow in mn_flows:
            key = mn_flow['key'].split(',')
            ip_src = key[0]
            ip_dst = key[1]
            port_src = key[3]
            port_dst = key[4]
            src_switch_id = int(int(ip_src.split('.')[2]) / 10)
            src_host_id = int(int(ip_src.split('.')[3]) / 10)
            dst_switch_id = int(int(ip_dst.split('.')[2]) / 10)
            dst_host_id = int(int(ip_dst.split('.')[3]) / 10)
            con_name = f'r{src_switch_id}h{src_host_id}-r{dst_switch_id}h{dst_host_id}'
            visible_flows.append(con_name)
            normalized_value = int(mn_flow['value']) * 8 / self.max_con_value

            con_table_id = self.get_con_table_id(src_switch_id, src_host_id, dst_switch_id)
            current_con = self.current_connections[con_table_id]
            if current_con is None:

                con_info = {
                    'name': con_name,
                    'ip src': ip_src,
                    'ip dst': ip_dst,
                    'port src': port_src,
                    'port dst': port_dst,
                    'value': min(1.0, normalized_value),
                    'path': self.flow_paths_id[con_name]['ospf path id']
                }
                self.current_connections[con_table_id] = con_info
            else:
                if current_con['port src'] != port_src or current_con['port dst'] != port_dst:
                    if current_con['value'] < mn_flow['value']:
                        current_con['port src'] = port_src
                        current_con['port dst'] = port_dst
                        current_con['path'] = self.flow_paths_id[con_name]['ospf path id']
                current_con['value'] = min(1.0, normalized_value)

        for con in self.current_connections:
            if con is None:
                continue
            if con['name'] not in visible_flows:
                con['value'] = 0

    def get_con_table_id(self, src_switch_id, src_host_id, dst_switch_id):
        if src_switch_id < dst_switch_id:
            dst_switch_id -= 1
        return ((src_switch_id - 1) * self.topo_info['hosts number'] * (self.num_switches - 1) + (dst_switch_id - 1)
                * self.topo_info['hosts number'] + src_host_id - 1)

    def get_ospf_path(self, connection_id):
        for _, con_info in self.flow_paths_id.items():
            if con_info['id'] == connection_id:
                return con_info['ospf path id']

    def apply_new_action(self, action):
        for connection_id, path_id in enumerate(action):
            self.apply_of_routes(connection_id, path_id)
            if self.current_connections[connection_id] is not None:
                self.current_connections[connection_id]['path'] = path_id

    def apply_of_routes(self, connection_id, path_id):
        connection = self.current_connections[connection_id]
        ryu_ip_address = self.env_info['ryu controller address']
        if connection is not None:
            src_node = connection['name'].split('-')[0].split('h')[0]
            dst_node = connection['name'].split('-')[1].split('h')[0]
            all_paths = self.topo_paths[src_node]
            path = None
            for node_path in all_paths:
                if node_path['destination node'] == dst_node:
                    path = node_path['all paths'][path_id]

            if path is not None:
                for i in range(len(path) - 2, -1, -1):
                    dpid = self.get_dpid(int(path[i].split('r')[1]))
                    data = {
                        "IP src": connection['ip src'],
                        "Port src": connection['port src'],
                        "IP dst": connection['ip dst'],
                        "Port dst": connection['port dst'],
                        "L4 proto": "udp",
                        "Output port": self.get_of_port(path[i], path[i + 1])
                    }
                    requests.post(f'http://{ryu_ip_address}/route/{dpid}', json=data)

    def get_of_port(self, src_node, dst_node):
        for link in self.topo_info['links']:
            if (link['node a'] == src_node and link['node b'] == dst_node) or \
                    (link['node b'] == src_node and link['node a'] == dst_node):
                if link['node a'] == src_node:
                    return link['port a']
                else:
                    return link['port b']

    @staticmethod
    def get_dpid(dpid):
        dpid = hex(dpid)[2:]
        dpid = '0' * (16 - len(dpid)) + dpid
        return dpid

    @staticmethod
    def compute_reward(old_state, new_state):
        # switch_penalty = 0
        link_penalty = 0
        route_change_penalty = 0

        # for switch_load in new_state['switch loads']:
        #     if switch_load < 0.7:
        #         switch_penalty += switch_load * 10 + (switch_load ** 2) * 10
        #     else:
        #         switch_penalty += switch_load * 10 + (switch_load ** 2) * 10 + (20 * (switch_load - 0.7)) ** 2

        for link_load in new_state['link loads']:
            if link_load < 0.7:
                link_penalty += link_load * 10 + (link_load ** 2) * 10
            else:
                link_penalty += link_load * 10 + (link_load ** 2) * 10 + (20 * (link_load - 0.7)) ** 2

        for old_path, new_path in zip(old_state['connection paths'], new_state['connection paths']):
            if np.int64(old_path) != np.int64(new_path):
                route_change_penalty += 1

        route_change_penalty *= 0.1

        # reward calculation factors for specific penalty
        # alfa = 1  # switch penalty
        beta = 1  # link penalty
        gamma = 1  # path change penalty

        total_reward = - (beta * link_penalty + gamma * route_change_penalty)
        return total_reward

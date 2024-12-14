import random
from datetime import datetime
from typing import Any, SupportsFloat

import gymnasium as gym
import numpy as np

from gymnasium import spaces
from gymnasium.core import ActType, ObsType

from traffic_control.simulation.topo_paths import get_all_paths
from traffic_control.simulation.topo_paths import get_ospf_paths


class SDN_env(gym.Env):
    def __init__(self, topo_info, env_info, disable_action_reward, seed, result_path, save_results):
        super(SDN_env, self).__init__()
        self.topo_info = topo_info
        self.env_info = env_info
        self.disable_action_reward = disable_action_reward
        self.stop = False
        self.random = random.Random()
        if seed is None:
            self.random.seed(datetime.now().timestamp())
        else:
            self.random.seed(seed)
        self.save_results = save_results
        self.result_path = result_path
        self.timestamp = 0

        self.topo_paths = get_all_paths(topo_info)
        self.max_con_value = topo_info['max topo bandwidth'] * 10**3
        self.max_connections = len(topo_info['nodes']) * (len(topo_info['nodes']) - 1) * topo_info['hosts number']
        self.current_connections = [None] * self.max_connections
        self.connection_time_left = [0] * self.max_connections
        self.flow_paths = []
        self.flow_paths_id = {}
        self.flow_paths_id_list = []
        self.ospf_paths = get_ospf_paths(topo_info)
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
                            flow_path_details = {'id': len(self.flow_paths) - 1,
                                                 'src node': node_a['name'],
                                                 'dst node': node_b['name'],
                                                 'ip src': f"192.168.{node_a['id'] * 10}.{i * 10}",
                                                 'ip dst': f"192.168.{node_b['id'] * 10}.{i * 10}",
                                                 'ospf path id': ospf_path_id}
                            self.flow_paths_id[flow_name] = flow_path_details
                            self.flow_paths_id_list.append(flow_path_details)
        self.num_switches = len(topo_info['nodes'])
        self.num_links = len(topo_info['links'])

        self.action_tuple = ([spaces.Discrete(num_paths) for num_paths in self.flow_paths])
        self.action_space = spaces.MultiDiscrete([num_paths for num_paths in self.flow_paths])
        self.observation_space = spaces.Dict({
            # "switch loads": spaces.Box(low=0, high=1, shape=(self.num_switches,), dtype=np.float32),
            "link loads": spaces.Box(low=0, high=2, shape=(self.num_links,), dtype=np.float32),
            "connection throughputs": spaces.Box(low=0, high=1, shape=(self.max_connections,), dtype=np.float32),
            "connection paths": spaces.MultiDiscrete(self.flow_paths)
        })

        self.switch_loads = {}
        for node in topo_info['nodes']:
            self.switch_loads[node['name']] = {'load': 0,
                                               'max load': 0}
        self.link_loads = {}
        for link in topo_info['links']:
            self.link_loads[f"{link['node a']}-{link['node b']}"] = {'load': 0,
                                                                     'max load': link['bw'] * 10**6 * 2}

        self.state = self.reset()[0]

    def reset(self, *, seed: int | None = None, options: dict[str, Any] | None = None) -> tuple[ObsType, dict[str, Any]]:
        return self.init_topology_state(), {}

    def init_topology_state(self):

        for connection_id in range(self.max_connections):
            flow_throughput, path, flow_time = self.new_flow(connection_id)
            self.current_connections[connection_id] = {
                'src node': self.flow_paths_id_list[connection_id]['src node'],
                'dst node': self.flow_paths_id_list[connection_id]['dst node'],
                'value': flow_throughput,
                'path': path
            }
            self.connection_time_left[connection_id] = flow_time

        return self.get_topology_state()

    def get_topology_state(self):
        for _, link in self.link_loads.items():
            link['load'] = 0

        for i, connection in enumerate(self.current_connections):
            for paths in self.topo_paths[connection['src node']]:
                if paths['destination node'] == connection['dst node']:
                    path = paths['all paths'][connection['path']]
                    for node_id in range(1, len(path)):
                        node_a = path[node_id]
                        node_b = path[node_id - 1]
                        link_name_a = f'{node_a}-{node_b}'
                        link_name_b = f'{node_b}-{node_a}'
                        if link_name_a in self.link_loads:
                            self.link_loads[link_name_a]['load'] += connection['value']
                        else:
                            self.link_loads[link_name_b]['load'] += connection['value']

        link_loads = []
        connection_throughputs = []
        connection_paths = []
        for _, link in self.link_loads.items():
            link_loads.append(min(2, link['load'] / link['max load']))
        for connection in self.current_connections:
            connection_throughputs.append(connection['value'] / self.max_con_value)
            connection_paths.append(connection['path'])
        state = {
            'link loads': link_loads,
            'connection throughputs': connection_throughputs,
            'connection paths': connection_paths
        }
        return state

    def new_flow(self, flow_id):
        bandwidth_interval = self.topo_info['bandwidth interval']
        time_interval = self.topo_info['time interval']
        flow_throughput = self.random.randint(bandwidth_interval[0], bandwidth_interval[1]) * 10**3
        flow_time = self.random.randint(time_interval[0], time_interval[1])
        path = self.flow_paths_id_list[flow_id]['ospf path id']
        return flow_throughput, path, flow_time

    def step(self, action: ActType) -> tuple[ObsType, SupportsFloat, bool, bool, dict[str, Any]]:
        if self.save_results is True:
            self.save_results_to_file()

        from traffic_control.emulation.traffic_control_learning import LOGGER
        # apply new actions
        if self.disable_action_reward is False:
            self.apply_new_action(action)

        # get new topology state
        next_state = self.get_topology_state()

        # calculate rewards
        if self.disable_action_reward is False:
            reward = self.compute_reward(self.state, next_state)
        else:
            reward = 0

        changed_flag = self.update_flows()
        if changed_flag is True:
            self.state = self.get_topology_state()
        else:
            self.state = next_state

        if self.stop is False:
            done = False
        else:
            done = True
        LOGGER.info(f"Step info - action: {action}")
        LOGGER.info(f"Step info - state: {self.state}")
        LOGGER.info(f"Step info - reward: {reward}")
        return self.state, reward, done, False, {}

    def apply_new_action(self, action):
        for connection_id, path_id in enumerate(action):
            self.current_connections[connection_id]['path'] = path_id

    def update_flows(self):
        changed_flag = False
        for connection_id in range(len(self.connection_time_left)):
            self.connection_time_left[connection_id] -= 1
            if self.connection_time_left[connection_id] == 0:
                changed_flag = True
                flow_throughput, path, flow_time = self.new_flow(connection_id)
                self.current_connections[connection_id] = {
                    'src node': self.flow_paths_id_list[connection_id]['src node'],
                    'dst node': self.flow_paths_id_list[connection_id]['dst node'],
                    'value': flow_throughput,
                    'path': path
                }
                self.connection_time_left[connection_id] = flow_time
        return changed_flag

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
            # link_load *= 2
            if link_load <= 0.7:
                link_penalty += link_load * 10 + (link_load ** 2) * 10
            else:
                link_penalty += link_load * 10 + (link_load ** 2) * 10 + (20 * (link_load - 0.7)) ** 2
            # if link_load >= 1:
            #     link_penalty += 100

        for old_path, new_path in zip(old_state['connection paths'], new_state['connection paths']):
            if np.int64(old_path) != np.int64(new_path):
                route_change_penalty += 1

        route_change_penalty *= 2

        # reward calculation factors for specific penalty
        # alfa = 1  # switch penalty
        beta = 1  # link penalty
        gamma = 1  # path change penalty

        total_reward = - (beta * link_penalty + gamma * route_change_penalty)
        return total_reward

    def save_results_to_file(self):
        switch_loads = {}
        link_loads = {}
        for node in self.topo_info['nodes']:
            switch_loads[node['name']] = 0
        for link in self.topo_info['links']:
            link_loads[f"{link['node a']}-{link['node b']}"] = 0

        for name, link in self.link_loads.items():
            split_name = name.split('-')
            node_a = split_name[0]
            node_b = split_name[1]
            name_b = f'{node_b}-{node_a}'
            switch_loads[node_a] += link['load']
            switch_loads[node_b] += link['load']
            if name in link_loads:
                link_loads[name] = link['load']
            else:
                link_loads[name_b] = link['load']

        with open(f'{self.result_path}/switch_loads.csv', 'a') as file:
            for name, stats in switch_loads.items():
                csv_line = f"{self.timestamp},{name},{stats}\n"
                file.write(csv_line)

        with open(f'{self.result_path}/link_loads.csv', 'a') as file:
            for name, stats in link_loads.items():
                csv_line = f"{self.timestamp},{name},{stats}\n"
                file.write(csv_line)

        self.timestamp += 1

import requests


def get_stats(topo_file, env_file, if_index_datasource, rt_flow_topo):
    # switch_loads = []
    port_loads = {}
    link_loads = []

    rt_flow_address = env_file['rt-flow address']
    if_in_bytes = get_if_in_bytes(rt_flow_address)
    if_out_bytes = get_if_out_bytes(rt_flow_address)

    # get switch loads
    for node in topo_file['nodes']:
        # switch_load = 0
        # switch_max_load = get_switch_max_load(topo_file, node['name'])
        for port in rt_flow_topo['nodes'][node['name']]['ports']:
            port_loads[port] = 0

            for metric_info in if_in_bytes:
                if metric_info['dataSource'] == if_index_datasource[port]:
                    metric_value = int(metric_info['metricValue']) * 8
                    # switch_load += (metric_value * 8)
                    port_loads[port] += metric_value
                    break
            for metric_info in if_out_bytes:
                if metric_info['dataSource'] == if_index_datasource[port]:
                    metric_value = int(metric_info['metricValue']) * 8
                    # switch_load += (metric_value * 8)
                    port_loads[port] += metric_value
                    break
        # switch_loads.append(min(1.0, switch_load / switch_max_load))

    # get link loads
    for link in topo_file['links']:
        port_a_load = port_loads[f"{link['node a']}-eth{link['port a']}"]
        port_b_load = port_loads[f"{link['node b']}-eth{link['port b']}"]
        link_load_value = max(port_a_load, port_b_load)
        link_max_load = link['bw'] * 10**6 * 2
        link_loads.append(min(2.0, link_load_value / link_max_load))

    # stats = {'switch loads': switch_loads, 'link loads': link_loads}
    stats = {'link loads': link_loads}
    return stats


def get_if_index_datasource(topo_file, env_file):
    rt_flow_topo = get_rt_flow_topo(env_file['rt-flow address'])
    if_index_datasource_tmp = {}
    for node in topo_file['nodes']:
        for node_port in rt_flow_topo['nodes'][node['name']]['ports']:
            if_index_datasource_tmp[rt_flow_topo['nodes'][node['name']]['ports'][node_port]['ifindex']] = node_port

    if_index_datasource = if_index_datasource_tmp.copy()
    for datasource, interface in if_index_datasource_tmp.items():
        if_index_datasource[interface] = datasource
    return if_index_datasource


def get_rt_flow_topo(rt_flow_address):
    request_path = '/topology/json'
    return requests.get(f'http://{rt_flow_address}{request_path}').json()


def get_if_in_bytes(rt_flow_address):
    request_path = '/dump/ALL/ifinoctets/json'
    return requests.get(f'http://{rt_flow_address}{request_path}').json()


def get_if_out_bytes(rt_flow_address):
    request_path = '/dump/ALL/ifoutoctets/json'
    return requests.get(f'http://{rt_flow_address}{request_path}').json()


def get_current_flows(rt_flow_address):
    request_path = '/activeflows/ALL/mn_flow/json?minValue=1000&aggMode=avg'
    return requests.get(f'http://{rt_flow_address}{request_path}').json()


def get_switch_max_load(topo_info, switch_name):
    switch_max_value = 0
    for link in topo_info['links']:
        if switch_name == link['node a'] or switch_name == link['node b']:
            switch_max_value += link['bw'] * 10**6 * 2
    return switch_max_value

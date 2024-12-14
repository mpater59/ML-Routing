import requests
import ast


def get_all_paths(topo_info):
    paths = {}
    topo_neighbors = {}
    for link in topo_info['links']:
        if link['node a'] not in topo_neighbors:
            topo_neighbors[link['node a']] = []
        if link['node b'] not in topo_neighbors:
            topo_neighbors[link['node b']] = []
        topo_neighbors[link['node a']].append(link['node b'])
        topo_neighbors[link['node b']].append(link['node a'])

    for node in topo_info['nodes']:
        paths[node['name']] = []
        for dest_node in topo_info['nodes']:
            if dest_node == node:
                continue
            dest_paths = find_all_paths(topo_neighbors, node['name'], dest_node['name'])
            paths[node['name']].append({'destination node': dest_node['name'], 'all paths': dest_paths})

    return paths


def find_all_paths(topo, src, dst, path=None):
    if path is None:
        path = []

    path = path + [src]
    if src == dst:
        return [path]
    if src not in topo:
        print('Wrong source node!')
        exit()

    paths = []
    for neighbor in topo[src]:
        if neighbor not in path:
            new_paths = find_all_paths(topo, neighbor, dst, path)
            paths.extend(new_paths)
    return paths


def get_ospf_paths(topo, env):
    ospf_paths = {}
    ipv4_address = env['ryu controller address']
    ospf_info = requests.get(f'http://{ipv4_address}/ospf/json')
    routing_table = ast.literal_eval(ospf_info.text)['routing tables']

    for node_src in topo['nodes']:
        for node_dst in topo['nodes']:
            if node_src == node_dst:
                continue
            path = find_ospf_path(routing_table, node_src['id'], node_dst['id'])
            ospf_paths[f"{node_src['name']}-{node_dst['name']}"] = path

    return ospf_paths


def find_ospf_path(routing_table, src_id, dst_id):
    path = [f'r{src_id}']
    local_routing_table = routing_table[src_id]
    while True:
        path.append(f'r{local_routing_table[dst_id]}')
        if local_routing_table[dst_id] == dst_id:
            break
        local_routing_table = routing_table[local_routing_table[dst_id]]

    return path

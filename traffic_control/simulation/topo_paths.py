import networkx as nx


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


def get_ospf_paths(topo):
    graph = nx.Graph()
    for link in topo['links']:
        graph.add_edge(link['node a'], link['node b'], weight=link['metric'])

    ospf_paths = {}
    for node_a in topo['nodes']:
        for node_b in topo['nodes']:
            if node_a == node_b:
                continue
            ospf_paths[f"{node_a['name']}-{node_b['name']}"] = nx.shortest_path(graph, node_a['name'], node_b['name'],
                                                                                weight='weight')
    return ospf_paths

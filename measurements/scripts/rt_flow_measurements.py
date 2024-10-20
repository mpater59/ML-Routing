import argparse
import time
import yaml
import requests
import threading
import os


def start_measurements(topo_file, emulation_name=None, max_time=300):
    from traffic_emulation.traffic_emulation_starter import LOGGER

    if emulation_name is None:
        LOGGER.critical('Enter emulation name for saving measurements!')
        exit()

    with open('env.yaml') as f:
        try:
            env_file = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(e)

    rt_flow_topo = get_rt_flow_topo(env_file['rt-flow address'])
    if_index_datasource = {}
    for node in topo_file['nodes']:
        for node_port in rt_flow_topo['nodes'][node['name']]['ports']:
            if node_port.split('-')[1] == 'eth1':
                continue
            if_index_datasource[rt_flow_topo['nodes'][node['name']]['ports'][node_port]['ifindex']] = node_port

    timestamp = 0
    LOGGER.info('Starting measurements!')
    while True:
        from traffic_emulation.traffic_emulation_starter import KILL_THREAD
        if KILL_THREAD is True:
            break
        if timestamp >= max_time:
            break
        thread = threading.Thread(target=get_stats, args=(timestamp, emulation_name, if_index_datasource,
                                                          env_file['rt-flow address'], env_file['repository path'],))
        thread.start()
        time.sleep(5)
        timestamp += 5
    LOGGER.info('Ending measurements!')


def get_current_flows(rt_flow_address):
    request_path = '/activeflows/ALL/mn_flow/json?minValue=100'
    return requests.get(f'http://{rt_flow_address}{request_path}').json()


def get_rt_flow_topo(rt_flow_address):
    request_path = '/topology/json'
    return requests.get(f'http://{rt_flow_address}{request_path}').json()


def get_if_in_bytes(rt_flow_address):
    request_path = '/dump/ALL/ifinoctets/json'
    return requests.get(f'http://{rt_flow_address}{request_path}').json()


def get_if_out_bytes(rt_flow_address):
    request_path = '/dump/ALL/ifoutoctets/json'
    return requests.get(f'http://{rt_flow_address}{request_path}').json()


def get_stats(timestamp, emulation_name, if_index_datasource, rt_flow_address, repository_path):
    if_in_bytes = get_if_in_bytes(rt_flow_address)
    if_out_bytes = get_if_out_bytes(rt_flow_address)
    mn_flow_bytes = get_current_flows(rt_flow_address)

    os.system(f'sudo touch {repository_path}/measurements/results/{emulation_name}/switches/if_in_bytes.csv')
    with open(f'{repository_path}/measurements/results/{emulation_name}/switches/if_in_bytes.csv', 'a') as file:
        for stats in if_in_bytes:
            if stats['dataSource'] in if_index_datasource:
                csv_line = f"{timestamp},{if_index_datasource[stats['dataSource']]},{int(stats['metricValue'])}\n"
                file.write(csv_line)

    os.system(f'sudo touch {repository_path}/measurements/results/{emulation_name}/switches/if_out_bytes.csv')
    with open(f'{repository_path}/measurements/results/{emulation_name}/switches/if_out_bytes.csv', 'a') as file:
        for stats in if_out_bytes:
            if stats['dataSource'] in if_index_datasource:
                csv_line = f"{timestamp},{if_index_datasource[stats['dataSource']]},{int(stats['metricValue'])}\n"
                file.write(csv_line)

    os.system(f'sudo touch {repository_path}/measurements/results/{emulation_name}/switches/mn_flow_bytes.csv')
    with open(f'{repository_path}/measurements/results/{emulation_name}/switches/mn_flow_bytes.csv', 'a') as file:
        for stats in mn_flow_bytes:
            csv_line = f"{timestamp},{stats['key']},{int(stats['value'])}\n"
            file.write(csv_line)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--file', dest='file', default='topo.yaml',
                        help='Topology file in .yaml format')
    parser.add_argument('-e', '--emulation', dest='emulation', default=None,
                        help='Name of traffic emulation for saving results (default: None)')
    parser.add_argument('-t', '--time', dest='time', type=int, default=300,
                        help='Max time for measurements (default: 300)')
    args = parser.parse_args()

    with open(args.file) as f:
        try:
            topo_file = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(e)
    start_measurements(topo_file, args.emulation, args.time)

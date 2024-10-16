import threading
import time
import random
import os
import psutil
import logging
import yaml


from datetime import datetime


with open('env.yaml') as f:
    try:
        env_file = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(e)

# CONSTANTS
LOGFILE = f"{env_file['repository path']}/traffic_emulation.log"


# GLOBALS
KILL_THREAD = False
LOGGER = logging
logging.basicConfig(filename=LOGFILE,
                    filemode='w',
                    format='%(asctime)s %(name)s %(levelname)s %(message)s',
                    level=logging.INFO)


def start_traffic_emulation(net, topo_info, emulation_name=None, emulation_time=None, seed=None):
    from traffic_emulation.iperf import run_server_thread
    from traffic_emulation.iperf import run_client_thread

    if seed is None:
        random.seed(datetime.now().timestamp())
    else:
        random.seed(seed)

    host_pairs, host_id = initial_hosts_information(net, topo_info)
    output = None
    if emulation_name is not None:
        prepare_result_dir(emulation_name)
        output = f"{env_file['repository path']}/measurements/results/{emulation_name}/hosts"

    bandwidth_interval = topo_info['bandwidth interval']
    time_interval = topo_info['time interval']

    thread_server_list = []
    thread_client_list = []
    for source_host, destination_host_list in host_pairs.items():
        for destination_host in destination_host_list:
            server_id = host_id[source_host]
            client_id = host_id[destination_host]
            # tcp_thread_server = threading.Thread(target=run_server_thread, args=(source_host,
            #                                                                      destination_host,
            #                                                                      server_id,
            #                                                                      client_id,
            #                                                                      'tcp',
            #                                                                      output,))
            udp_thread_server = threading.Thread(target=run_server_thread, args=(source_host,
                                                                                 destination_host,
                                                                                 server_id,
                                                                                 client_id,
                                                                                 'udp',
                                                                                 output,))
            # new_seed = random.randint(0, 999999999999)
            # tcp_thread_client = threading.Thread(target=run_client_thread, args=(source_host,
            #                                                                      destination_host,
            #                                                                      server_id,
            #                                                                      client_id,
            #                                                                      'tcp',
            #                                                                      bandwidth_interval,
            #                                                                      time_interval,
            #                                                                      new_seed,))
            new_seed = random.randint(0, 999999999999)
            udp_thread_client = threading.Thread(target=run_client_thread, args=(source_host,
                                                                                 destination_host,
                                                                                 server_id,
                                                                                 client_id,
                                                                                 'udp',
                                                                                 bandwidth_interval,
                                                                                 time_interval,
                                                                                 new_seed,))
            # thread_server_list.append(tcp_thread_server)
            thread_server_list.append(udp_thread_server)
            # thread_client_list.append(tcp_thread_client)
            thread_client_list.append(udp_thread_client)

    start_time = time.time()
    LOGGER.info('Starting emulation!')
    for thread in thread_server_list:
        thread.start()
    time.sleep(1)
    for thread in thread_client_list:
        thread.start()

    if emulation_time is not None:
        emulation_time = emulation_time * 60
    try:
        while True:
            time.sleep(10)
            if emulation_time is not None:
                current_time = time.time()
                if current_time - start_time >= emulation_time:
                    LOGGER.info('Ending emulation!')
                    kill_threads()
                    if output is not None:
                        os.system(
                            f"sudo cp {LOGFILE} {env_file['repository path']}/measurements/results/{emulation_name}")
                    break
            # reset iperf connection
            if psutil.virtual_memory().percent >= 90:
                LOGGER.warning('Restarting iperf connection!')
                os.system('sudo kill -9 $(pgrep iperf)')
    except KeyboardInterrupt:
        LOGGER.warning('Interrupted!')
        kill_threads()
        if output is not None:
            os.system(f"sudo cp {LOGFILE} {env_file['repository path']}/measurements/results/{emulation_name}")


def kill_threads():
    global KILL_THREAD
    KILL_THREAD = True
    os.system('sudo kill -9 $(pgrep iperf)')


def initial_hosts_information(net, topo_info):
    host_pairs = {}
    host_id_dict = {}
    current_index = 0
    for node in topo_info['nodes']:
        switch_id = node['id']
        for host_id in range(1, topo_info['hosts number'] + 1):
            host = net.get(f's{switch_id}h{host_id}')
            host_pairs[host] = []
            host_id_dict[host] = current_index
            current_index += 1
            for node_ in topo_info['nodes']:
                switch_id_ = node_['id']
                if switch_id != switch_id_:
                    for host_id_ in range(1, topo_info['hosts number'] + 1):
                        host_ = net.get(f's{switch_id_}h{host_id_}')
                        host_pairs[host].append(host_)
    return host_pairs, host_id_dict


def prepare_result_dir(emulation_name):
    os.system(f"sudo rm -rf {env_file['repository path']}/measurements/results/{emulation_name}")
    os.system(f"sudo mkdir -p {env_file['repository path']}/measurements/results/{emulation_name}")
    os.system(f"sudo mkdir -p {env_file['repository path']}/measurements/results/{emulation_name}/hosts")
    os.system(f"sudo mkdir -p {env_file['repository path']}/measurements/results/{emulation_name}/switches")
    os.system(f"sudo mkdir -p {env_file['repository path']}/measurements/results/{emulation_name}/final")

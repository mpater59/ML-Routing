import threading
import time
import random


from traffic_emulation.iperf import run_server_thread
from traffic_emulation.iperf import run_client_thread
from datetime import datetime


def random_traffic_emulation(net, topo_info):
    random.seed(datetime.now().timestamp())

    host_pairs, host_id = initial_hosts_information(net, topo_info)
    output = None

    bandwidth_interval = topo_info['bandwidth interval']
    time_interval = topo_info['time interval']

    thread_server_list = []
    thread_client_list = []
    print(host_pairs)
    for source_host, destination_host_list in host_pairs:
        for destination_host in destination_host_list:
            server_id = host_id[source_host]
            client_id = host_id[destination_host]
            tcp_thread_server = threading.Thread(target=run_server_thread, args=(source_host,
                                                                                 destination_host,
                                                                                 server_id,
                                                                                 client_id,
                                                                                 'tcp',
                                                                                 output,))
            udp_thread_server = threading.Thread(target=run_server_thread, args=(source_host,
                                                                                 destination_host,
                                                                                 server_id,
                                                                                 client_id,
                                                                                 'udp',
                                                                                 output,))
            new_seed = random.randint(0, 999999999999)
            tcp_thread_client = threading.Thread(target=run_client_thread, args=(source_host,
                                                                                 destination_host,
                                                                                 server_id,
                                                                                 client_id,
                                                                                 'tcp',
                                                                                 bandwidth_interval,
                                                                                 time_interval,
                                                                                 new_seed,))
            new_seed = random.randint(0, 999999999999)
            udp_thread_client = threading.Thread(target=run_client_thread, args=(source_host,
                                                                                 destination_host,
                                                                                 server_id,
                                                                                 client_id,
                                                                                 'udp',
                                                                                 bandwidth_interval,
                                                                                 time_interval,
                                                                                 new_seed,))
            thread_server_list.append(tcp_thread_server)
            thread_server_list.append(udp_thread_server)
            thread_client_list.append(tcp_thread_client)
            thread_client_list.append(udp_thread_client)

    for thread in thread_server_list:
        thread.start()
    time.sleep(1)
    for thread in thread_client_list:
        thread.start()

    while True:
        time.sleep(1)


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

import threading
import time
import random
import os


from datetime import datetime


# GLOBALS
KILL_THREAD = False


def random_traffic_emulation(net, topo_info):
    from traffic_emulation.iperf import run_server_thread
    from traffic_emulation.iperf import run_client_thread
    from traffic_emulation.iperf import run_iperf_server_tcp

    random.seed(datetime.now().timestamp())

    host_pairs, host_id = initial_hosts_information(net, topo_info)
    output = None

    os.system("/home/user/mininet/util/m s1h1 ip a")
    exit()


    # host = net.get('s1h1')
    # host.pexec('iperf -s -p 10000')
    # print('test1')
    # host.pexec('iperf -s -p 20000')
    # print('test2')
    # t1 = threading.Thread(target=run_iperf_server_tcp, args=(host, host, 10000,))
    # t2 = threading.Thread(target=run_iperf_server_tcp, args=(host, host, 20000,))
    # t1.start()
    # time.sleep(1)
    # t2.start()

    bandwidth_interval = topo_info['bandwidth interval']
    time_interval = topo_info['time interval']

    thread_server_list = []
    thread_client_list = []
    for source_host, destination_host_list in host_pairs.items():
        for destination_host in destination_host_list:
            server_id = host_id[source_host]
            client_id = host_id[destination_host]
            tcp_thread_server = threading.Thread(target=run_server_thread, args=(source_host,
                                                                                 destination_host,
                                                                                 server_id,
                                                                                 client_id,
                                                                                 'tcp',
                                                                                 '/home/user/log1.log',))
            udp_thread_server = threading.Thread(target=run_server_thread, args=(source_host,
                                                                                 destination_host,
                                                                                 server_id,
                                                                                 client_id,
                                                                                 'udp',
                                                                                 '/home/user/log2.log',))
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
            break
        break

    for thread in thread_server_list:
        thread.start()
        time.sleep(1)
    time.sleep(1)
    for thread in thread_client_list:
        thread.start()

    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        global KILL_THREAD
        KILL_THREAD = True
        print('Interrupted!')


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




import sys
import threading
import time
import random


from traffic_emulation.iperf import run_server_thread
from datetime import datetime


def random_traffic_emulation(net, topo_info):
    random.seed(datetime.now().timestamp())

    host_pairs = generate_host_pairs(net, topo_info)
    print(host_pairs)

    # s1h1 = net.get('s1h1')
    #
    # t1 = threading.Thread(target=run_server_thread, args=(s1h1, 1, 2, 'tcp',))
    # t1.start()
    # while True:
    #     time.sleep(1)
    # run_server_thread(1, 1, 1, 1, 1)

    server_threads = []
    tcp_clients_threads = []
    udp_clients_threads = []

    # s1h1 = net.get('s1h1')
    # s2h1 = net.get('s2h1')
    # s3h1 = net.get('s3h1')
    # s4h1 = net.get('s4h1')
    # print('Printing')
    # s1h1.cmdPrint('echo test')
    # s1h1.cmd('echo test > test.txt')
    # print(s1h1.cmd('cat test.txt'))
    # t1 = threading.Thread(target=run_iperf_server, args=(s1h1,))
    # # t1.start()
    # time.sleep(2)
    # t2 = threading.Thread(target=run_iperf_client, args=(s2h1, '192.168.10.10',))
    # # t2.start()
    #
    # # result = net.iperf([s1h1, s2h1])
    # # print(result)
    # # t1 = threading.Thread(target=run_iperf_test, args=(net, s1h1, s2h1,))
    # # t2 = threading.Thread(target=run_iperf_test, args=(net, s3h1, s4h1,))
    # t1.start()
    # t2.start()
    # t1.join()
    # t2.join()


def generate_host_pairs(net, topo_info):
    host_pairs = {}
    for node in topo_info['nodes']:
        switch_id = node['id']
        for host_id in range(1, topo_info['hosts number'] + 1):
            host = net.get(f's{switch_id}h{host_id}')
            host_pairs[host] = []
            for node_ in topo_info['nodes']:
                switch_id_ = node_['id']
                if switch_id != switch_id_:
                    for host_id_ in range(1, topo_info['hosts number'] + 1):
                        host_ = net.get(f's{switch_id_}h{host_id_}')
                        host_pairs[host].append(host_)
    return host_pairs

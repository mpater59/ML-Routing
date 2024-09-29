import threading
import time
import random

from traffic_emulation.iperf import run_iperf_client_tcp
from traffic_emulation.iperf import run_iperf_client_udp
from traffic_emulation.iperf import run_iperf_server_tcp
from traffic_emulation.iperf import run_iperf_server_udp
from datetime import datetime


def random_traffic_emulation(net, topo_info):
    random.seed(datetime.now().timestamp())

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


def iperf_server_tcp_thread():
    pass

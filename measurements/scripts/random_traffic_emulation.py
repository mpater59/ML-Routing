import threading
import time


def random_traffic_emulation(net, topo_info):
    s1h1 = net.get('s1h1')
    s2h1 = net.get('s2h1')
    s3h1 = net.get('s3h1')
    s4h1 = net.get('s4h1')
    print('Printing')
    s1h1.cmdPrint('echo test')
    s1h1.cmd('echo test > test.txt')
    print(s1h1.cmd('cat test.txt'))
    # t1 = threading.Thread(target=run_iperf_server, args=(s1h1,))
    # t1.start()
    # time.sleep(2)
    # t2 = threading.Thread(target=run_iperf_client, args=(s2h1, '192.168.10.10',))
    # t2.start()

    # result = net.iperf([s1h1, s2h1])
    # print(result)
    threading.Thread(target=run_iperf_test, args=(net, s1h1, s2h1,)).start()
    threading.Thread(target=run_iperf_test, args=(net, s3h1, s4h1,)).start()



def run_iperf_server(host):
    print('Starting iperf server')
    host.cmd('iperf -s')
    print('Ending iperf server')


def run_iperf_client(host, dest_ip_addr):
    print('Starting iperf client')
    host.cmd(f'iperf -c {dest_ip_addr}')
    print('Ending iperf client')


def run_iperf_test(net, host1, host2):
    net.iperf([host1, host2])

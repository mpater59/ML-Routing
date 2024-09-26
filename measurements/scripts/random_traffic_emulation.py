import threading
import time


def random_traffic_emulation(net, topo_info):
    s1h1 = net.get('s1h1')
    s2h1 = net.get('s2h1')
    print('Printing')
    s1h1.cmdPrint('echo test')
    s1h1.cmd('echo test > test.txt')
    print(s1h1.cmd('cat test.txt'))
    threading.Thread(target=run_iperf_server, args=(s1h1,)).start()
    time.sleep(2)
    threading.Thread(target=run_iperf_client, args=(s2h1, '192.168.10.10',)).start()
    print('Ended')


def run_iperf_server(host):
    print('Starting iperf server')
    host.cmd('iperf -s -y C > test.txt')
    print('Ending iperf server')


def run_iperf_client(host, dest_ip_addr):
    print('Starting iperf client')
    print(host.cmd(f'iperf -c {dest_ip_addr}'))
    print('Ended iperf client')

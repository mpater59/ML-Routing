import random
import time


from datetime import datetime


# Constants
DEFAULT_BANDWIDTH_INTERVAL = [1000, 10000]
DEFAULT_TIME_INTERVAL = [60, 300]


def run_iperf_server_tcp(host, port, output=None):
    print(f'Starting iperf TCP server - host: {host.name}; port: {port}')
    if output is None:
        host.cmd(f'iperf -s -p {port}')
    else:
        host.cmd(f'iperf -s -p {port} -y C > {output}')
    print(f'Ending iperf TCP server - host: {host.name}; port: {port}')


def run_iperf_server_udp(host, port, output=None):
    print(f'Starting iperf UDP server - host: {host.name}; port: {port}')
    if output is None:
        host.cmd(f'iperf -s -p {port} -u')
    else:
        host.cmd(f'iperf -s -p {port} -y C -u > {output}')
    print(f'Ending iperf UDP server - host: {host.name}; port: {port}')


def run_iperf_client_tcp(host, port, dest_ip_addr, bandwidth, flow_time):
    host.cmd(f'iperf -c {dest_ip_addr} -p {port} -b {bandwidth}K -t {flow_time}')


def run_iperf_client_udp(host, port, dest_ip_addr, bandwidth, flow_time):
    host.cmd(f'iperf -c {dest_ip_addr} -p {port} -u -b {bandwidth} -t {flow_time}')


def run_server_thread(server, server_id, client_id, l4_proto, output=None):
    if len(str(server_id)) == 1:
        server_id = f'0{server_id}'
    if len(str(client_id)) == 1:
        client_id = f'0{client_id}'

    port = None
    if l4_proto == 'tcp':
        if output is not None:
            pass
        port = f'1{server_id}{client_id}'
    elif l4_proto == 'udp':
        if output is not None:
            pass
        port = f'2{server_id}{client_id}'

    while True:
        if l4_proto == 'tcp':
            run_iperf_server_tcp(server, port, output)
        elif l4_proto == 'udp':
            run_iperf_server_udp(server, port, output)
        else:
            print('Unknown L4 protocol!')
            exit()


def run_client_thread(server, client, server_id, client_id, l4_proto, bandwidth_interval=None,
                      time_interval=None, seed=None):
    if bandwidth_interval is None:
        bandwidth_interval = DEFAULT_BANDWIDTH_INTERVAL
    if time_interval is None:
        time_interval = DEFAULT_TIME_INTERVAL
    if seed is None:
        random.seed(datetime.now().timestamp())
    else:
        random.seed(seed)

    if len(str(server_id)) == 1:
        server_id = f'0{server_id}'
    if len(str(client_id)) == 1:
        client_id = f'0{client_id}'

    port = None
    if l4_proto == 'tcp':
        port = f'1{server_id}{client_id}'
    elif l4_proto == 'udp':
        port = f'2{server_id}{client_id}'

    server_ip_addr = server.IP()
    while True:
        bandwidth = random.randint(bandwidth_interval[0], bandwidth_interval[1])
        flow_time = random.randint(time_interval[0], time_interval[1])
        if l4_proto == 'tcp':
            run_iperf_client_tcp(client, port, server_ip_addr, bandwidth, flow_time)
        elif l4_proto == 'udp':
            run_iperf_client_udp(client, port, server_ip_addr, bandwidth, flow_time)
        else:
            print('Unknown L4 protocol!')
            exit()
        time.sleep(1)

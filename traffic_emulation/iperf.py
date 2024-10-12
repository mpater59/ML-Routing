import random
import threading
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


def run_server_thread(host, server_id, client_id, l4_proto, output=None):
    if len(str(server_id)) == 1:
        server_id = f'0{server_id}'
    if len(str(client_id)) == 1:
        client_id = f'0{client_id}'

    if l4_proto == 'tcp':
        if output is not None:
            pass
        tcp_port = f'1{server_id}{client_id}'
        while True:
            run_iperf_server_tcp(host, tcp_port, output)

    elif l4_proto == 'udp':
        if output is not None:
            pass
        udp_port = f'2{server_id}{client_id}'
        while True:
            run_iperf_server_udp(host, udp_port, output)



def run_iperf_test(server, client, server_id, client_id, bandwidth_interval=None, time_interval=None,
                   seed=None, output=None):
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
    tcp_port = f'1{server_id}{client_id}'
    udp_port = f'2{server_id}{client_id}'

    output_tcp = None
    output_udp = None
    if output is not None:
        pass

    server_tcp_thread = threading.Thread(target=run_iperf_server_tcp, args=(server, tcp_port, output_tcp,))
    server_udp_thread = threading.Thread(target=run_iperf_server_udp, args=(server, udp_port, output_udp,))

import random
import time
import os


from datetime import datetime


# Constants
DEFAULT_BANDWIDTH_INTERVAL = [1000, 10000]
DEFAULT_TIME_INTERVAL = [60, 300]
MNEXEC = '/home/user/mininet/util/m'


def run_iperf_server_tcp(server, client, port, output=None):
    print(f' {client.name} -> {server.name} flow (TCP) - Starting iperf TCP server; host: {server.name}; port: {port}; '
          f'output: {output}')
    if output is None:
        os.system(f'{MNEXEC} {server.name} iperf -s -p {port} > /dev/null 2> /dev/null')
        # server.cmd(f'iperf -s -p {port} &')
    else:
        os.system(f'{MNEXEC} {server.name} iperf -s -p {port} -y C > {output} 2> /dev/null')
        # server.cmd(f'iperf -s -p {port} -y C > {output} &')


def run_iperf_server_udp(server, client, port, output=None):
    print(f'{client.name} -> {server.name} flow (UDP) - Starting iperf UDP server; host: {server.name}; port: {port}; '
          f'output: {output}')
    if output is None:
        os.system(f'{MNEXEC} {server.name} iperf -s -p {port} -u > /dev/null 2> /dev/null')
        # server.cmd(f'iperf -s -p {port} -u &')
    else:
        os.system(f'{MNEXEC} {server.name} iperf -s -p {port} -y C -u > {output} 2> /dev/null')
        # server.cmd(f'iperf -s -p {port} -y C -u > {output} &')


def run_iperf_client_tcp(server, client, port, dest_ip_addr, bandwidth, flow_time):
    print(f'{client.name} -> {server.name} flow (TCP) - Starting iperf TCP client; host: {client.name}; port: {port}; '
          f'destination IP address: {dest_ip_addr}; bandwidth: {bandwidth} Kbps; flow time: {flow_time} s')
    # client.pexec(f'iperf -c {dest_ip_addr} -p {port} -b {bandwidth}K -t {flow_time}')
    os.system(f'{MNEXEC} {client.name} iperf -c {dest_ip_addr} -p {port} -b {bandwidth}K -t {flow_time} '
              f'> /dev/null 2> /dev/null')


def run_iperf_client_udp(server, client, port, dest_ip_addr, bandwidth, flow_time):
    print(f'{client.name} -> {server.name} flow (UDP) - Starting iperf UDP client; host: {client.name}; port: {port}; '
          f'destination IP address: {dest_ip_addr}; bandwidth: {bandwidth} Kbps; flow time: {flow_time} s')
    # client.pexec(f'iperf -c {dest_ip_addr} -p {port} -u -b {bandwidth} -t {flow_time}')
    os.system(f'{MNEXEC} {client.name} iperf -c {dest_ip_addr} -p {port} -u -b {bandwidth}K -t {flow_time} '
              f'> /dev/null 2> /dev/null')


def run_server_thread(server, client, server_id, client_id, l4_proto, output=None):
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
        from traffic_emulation.random_traffic_emulation import KILL_THREAD
        if KILL_THREAD is True:
            break
        if server.waiting is False:
            if l4_proto == 'tcp':
                run_iperf_server_tcp(server, client, port, output)
                break
            elif l4_proto == 'udp':
                run_iperf_server_udp(server, client, port, output)
                break
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
        print(f'{client.name} -> {server.name} flow ({l4_proto.upper()}) - thread seed: {seed}')

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
        from traffic_emulation.random_traffic_emulation import KILL_THREAD
        if KILL_THREAD is True:
            break
        bandwidth = random.randint(bandwidth_interval[0], bandwidth_interval[1])
        flow_time = random.randint(time_interval[0], time_interval[1])
        if l4_proto == 'tcp':
            run_iperf_client_tcp(server, client, port, server_ip_addr, bandwidth, flow_time)
        elif l4_proto == 'udp':
            run_iperf_client_udp(server, client, port, server_ip_addr, bandwidth, flow_time)
        else:
            print('Unknown L4 protocol!')
            exit()
        time.sleep(1)

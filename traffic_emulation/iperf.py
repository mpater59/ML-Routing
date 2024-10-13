import random
import time
import os
import gc

from datetime import datetime

# Constants
DEFAULT_BANDWIDTH_INTERVAL = [1000, 10000]
DEFAULT_TIME_INTERVAL = [60, 300]
MNEXEC = '/home/user/mininet/util/m'


def run_iperf_server_tcp(server, port, logger, output=None):
    logger.info(f'{server.name} (TCP) - Starting iperf TCP server; '
                f'host: {server.name}; port: {port}; output: {output}')
    if output is None:
        os.system(f'{MNEXEC} {server.name} iperf -s -p {port} > /dev/null 2> /dev/null')
    else:
        os.system(f'{MNEXEC} {server.name} iperf -s -p {port} -y C > {output} 2> /dev/null')


def run_iperf_server_udp(server, port, logger, output=None):
    logger.info(f'{server.name} (UDP) - Starting iperf UDP server; '
                f'host: {server.name}; port: {port}; output: {output}')
    if output is None:
        os.system(f'{MNEXEC} {server.name} iperf -s -p {port} -u > /dev/null 2> /dev/null')
    else:
        os.system(f'{MNEXEC} {server.name} iperf -s -p {port} -y C -u > {output} 2> /dev/null')


def run_iperf_client_tcp(server, client, port, dest_ip_addr, bandwidth, flow_time, logger):
    logger.info(f'{client.name} -> {server.name} flow (TCP) - Starting iperf TCP client; '
                f'host: {client.name}; port: {port}; destination IP address: {dest_ip_addr}; '
                f'bandwidth: {bandwidth} Kbps; flow time: {flow_time} s')
    os.system(f'{MNEXEC} {client.name} iperf -c {dest_ip_addr} -p {port} -b {bandwidth}K -t {flow_time} '
              f'> /dev/null 2> /dev/null')


def run_iperf_client_udp(server, client, port, dest_ip_addr, bandwidth, flow_time, logger):
    logger.info(f'{client.name} -> {server.name} flow (UDP) - Starting iperf UDP client; '
                f'host: {client.name}; port: {port}; destination IP address: {dest_ip_addr}; '
                f'bandwidth: {bandwidth} Kbps; flow time: {flow_time} s')
    os.system(f'{MNEXEC} {client.name} iperf -c {dest_ip_addr} -p {port} -u -b {bandwidth}K -t {flow_time} '
              f'> /dev/null 2> /dev/null')


def run_server_thread(server, server_id, l4_proto, output=None):
    from traffic_emulation.random_traffic_emulation import LOGGER

    server_id = '0' * (4 - len(str(server_id))) + str(server_id)

    port = None
    if l4_proto == 'tcp':
        if output is not None:
            pass
        port = f'1{server_id}'
    elif l4_proto == 'udp':
        if output is not None:
            pass
        port = f'2{server_id}'

    while True:
        from traffic_emulation.random_traffic_emulation import KILL_THREAD

        if KILL_THREAD is True:
            break
        if l4_proto == 'tcp':
            run_iperf_server_tcp(server, port, LOGGER, output)
        elif l4_proto == 'udp':
            run_iperf_server_udp(server, port, LOGGER, output)
        else:
            print('Unknown L4 protocol!')
            exit()
        time.sleep(1)
        gc.collect()


def run_client_thread(server, client, server_id, l4_proto, bandwidth_interval=None,
                      time_interval=None, seed=None):
    from traffic_emulation.random_traffic_emulation import LOGGER

    if bandwidth_interval is None:
        bandwidth_interval = DEFAULT_BANDWIDTH_INTERVAL
    if time_interval is None:
        time_interval = DEFAULT_TIME_INTERVAL
    if seed is None:
        random.seed(datetime.now().timestamp())
    else:
        random.seed(seed)
        LOGGER.info(f'{client.name} -> {server.name} flow ({l4_proto.upper()}) - thread seed: {seed}')

    server_id = '0' * (4 - len(str(server_id))) + str(server_id)

    port = None
    if l4_proto == 'tcp':
        port = f'1{server_id}'
    elif l4_proto == 'udp':
        port = f'2{server_id}'

    server_ip_addr = server.IP()
    while True:
        from traffic_emulation.random_traffic_emulation import KILL_THREAD
        if KILL_THREAD is True:
            break
        bandwidth = random.randint(bandwidth_interval[0], bandwidth_interval[1])
        flow_time = random.randint(time_interval[0], time_interval[1])
        if l4_proto == 'tcp':
            run_iperf_client_tcp(server, client, port, server_ip_addr, bandwidth, flow_time, LOGGER)
        elif l4_proto == 'udp':
            run_iperf_client_udp(server, client, port, server_ip_addr, bandwidth, flow_time, LOGGER)
        else:
            print('Unknown L4 protocol!')
            exit()
        time.sleep(5)
        gc.collect()

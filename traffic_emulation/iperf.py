def run_iperf_server_tcp(host, output=None):
    if output is None:
        host.cmd('iperf -s -p 5000')
    else:
        host.cmd(f'iperf -s -p 5000 -y C > {output}')


def run_iperf_server_udp(host, output=None):
    if output is None:
        host.cmd('iperf -s -p 6000')
    else:
        host.cmd(f'iperf -s -p 6000 -y C > {output}')


def run_iperf_client_tcp(host, dest_ip_addr):
    host.cmd(f'iperf -c {dest_ip_addr} -p 5000')


def run_iperf_client_udp(host, dest_ip_addr):
    host.cmd(f'iperf -c {dest_ip_addr} -p 6000')
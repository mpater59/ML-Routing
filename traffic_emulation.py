def run_traffic_emulation(net, test_version=None):
    print('test print :)')
    host = net.get('s1h1')
    print(host.cmd('ls -al'))

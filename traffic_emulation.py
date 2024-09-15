def run_traffic_emulation(net, test_version=None):
    print('test print :)')
    host = net.get('s1h1')
    host.cmd('ls -al')
    print(host.cmd('ls -al'))

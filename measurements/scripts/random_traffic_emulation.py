def random_traffic_emulation(net, topo_info):
    s1h1 = net.get('s1h1')
    print('Printing')
    s1h1.cmdPrint('echo test')
    s1h1.cmd('echo test > test.txt')
    print(s1h1.cmd('cat test.txt'))
    print(s1h1.cmd('iperf -s'))
    print('Ended')

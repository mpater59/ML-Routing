from measurements.scripts.random_traffic_emulation import random_traffic_emulation


def traffic_emulation(net, topo_info, test_version=None):
    if test_version is None:
        random_traffic_emulation(net, topo_info)

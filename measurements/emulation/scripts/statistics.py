import csv
import argparse
import matplotlib.pyplot as plt
import numpy as np
import yaml


parser = argparse.ArgumentParser()
# test_5_42_v1
# ppo_off_test_10_42
# ppo_on_test_10_42
# ppo_on_test_10_42_v2
parser.add_argument('-e', '--emulation', dest='emulation', default='ppo_off_test_10_42',
                    help='Traffic emulation name')
parser.add_argument('-f', '--file', dest='file', default='topo.yaml',
                    help='Topology file in .yaml format')
args = parser.parse_args()

topo_info = {}
with open(args.file) as f:
    try:
        topo_info = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(e)

if_in_bytes_csv = []
with open(f'measurements/emulation/results/{args.emulation}/switches/if_in_bytes.csv') as file:
    csv_result = csv.reader(file)
    for row in csv_result:
        if_in_bytes_csv.append(row)

if_out_bytes_csv = []
with open(f'measurements/emulation/results/{args.emulation}/switches/if_out_bytes.csv') as file:
    csv_result = csv.reader(file)
    for row in csv_result:
        if_out_bytes_csv.append(row)

timestamps = []
for row in if_in_bytes_csv:
    if int(row[0]) not in timestamps:
        timestamps.append(int(row[0]))

link_max_loads = {}
for link in topo_info['links']:
    link_max_loads[f"{link['node a']}-{link['node b']}"] = link['bw'] * 10**6 * 2

# ingress interface statistics
if_in_results = {}
for row in if_in_bytes_csv:
    if row[1] not in if_in_results:
        if_in_results[row[1]] = {}
        if_in_results[row[1]]['mean'] = 0
        if_in_results[row[1]]['timestamp values'] = []
    if_in_results[row[1]]['mean'] += int(row[2]) * 8
    if_in_results[row[1]]['timestamp values'].append(int(row[2]) * 8)

for _, if_in_result in if_in_results.items():
    if_in_result['mean'] = if_in_result['mean'] / len(timestamps)
if_in_results = dict(sorted(if_in_results.items()))

# egress interface statistics
if_out_results = {}
for row in if_out_bytes_csv:
    if row[1] not in if_out_results:
        if_out_results[row[1]] = {}
        if_out_results[row[1]]['mean'] = 0
        if_out_results[row[1]]['timestamp values'] = []
    if_out_results[row[1]]['mean'] += int(row[2]) * 8
    if_out_results[row[1]]['timestamp values'].append(int(row[2]) * 8)

for _, if_in_result in if_out_results.items():
    if_in_result['mean'] = if_in_result['mean'] / len(timestamps)
if_out_results = dict(sorted(if_out_results.items()))

# combine interface statistics
if_combine_results = {}
for interface in if_in_results:
    if interface not in if_combine_results:
        if_combine_results[interface] = {}
        if_combine_results[interface]['mean'] = 0
        if_combine_results[interface]['timestamp values'] = []
    if_combine_results[interface]['mean'] = if_in_results[interface]['mean'] + if_out_results[interface]['mean']
    for ingress_value, egress_value in zip(if_in_results[interface]['timestamp values'],
                                           if_out_results[interface]['timestamp values']):
        if_combine_results[interface]['timestamp values'].append(ingress_value + egress_value)
if_combine_results = dict(sorted(if_combine_results.items()))

# switches statistics
switches_results = {}
for interface, values in if_combine_results.items():
    switch_name = interface.split('-')[0]
    if switch_name not in switches_results:
        switches_results[switch_name] = {}
        switches_results[switch_name]['mean'] = 0
        switches_results[switch_name]['timestamp values'] = [0] * len(timestamps)
        switches_results[switch_name]['interfaces'] = []
    switches_results[switch_name]['mean'] += values['mean']
    for index, value in enumerate(values['timestamp values']):
        switches_results[switch_name]['timestamp values'][index] += value
    switches_results[switch_name]['interfaces'].append(interface)
switches_results = dict(sorted(switches_results.items()))

# links statistics
links_results = {}
for link in topo_info['links']:
    port_a = f"{link['node a']}-eth{link['port a']}"
    port_b = f"{link['node b']}-eth{link['port b']}"
    links_results[f'{link["node a"]}-{link["node b"]}'] = {}
    links_results[f'{link["node a"]}-{link["node b"]}']['mean'] = max(if_combine_results[port_a]['mean'],
                                                                      if_combine_results[port_b]['mean'])
    links_results[f'{link["node a"]}-{link["node b"]}']['timestamp values'] = []
    links_results[f'{link["node a"]}-{link["node b"]}']['normalized values'] = []
    for value_a, value_b in zip(if_combine_results[port_a]['timestamp values'],
                                if_combine_results[port_b]['timestamp values']):
        if value_a >= value_b:
            links_results[f'{link["node a"]}-{link["node b"]}']['timestamp values'].append(value_a)
            links_results[f'{link["node a"]}-{link["node b"]}']['normalized values'].append(
                value_a / link_max_loads[f'{link["node a"]}-{link["node b"]}'])
        else:
            links_results[f'{link["node a"]}-{link["node b"]}']['timestamp values'].append(value_b)
            links_results[f'{link["node a"]}-{link["node b"]}']['normalized values'].append(
                value_b / link_max_loads[f'{link["node a"]}-{link["node b"]}'])


print('Printing switch average throughput:\n')
for switch_name, values in switches_results.items():
    print(f"Switch {switch_name}:")
    print(f"Total average throughput: {round(values['mean'] / 1000, 3)} Kbps")
    for interface in values['interfaces']:
        print(f"Interface {interface} average throughput: "
              f"{round(if_combine_results[interface]['mean'] / 1000, 3)} Kbps")
    print()

print()
print('Printing link average throughput:')
for link_name, values in links_results.items():
    print(f"Link {link_name} - average throughput: {round(values['mean'] / 1000, 3)} Kbps")

print()
print('Printing normalized link average load:')
for link_name, values in links_results.items():
    print(f"Link {link_name} - average load: {round(values['mean'] / link_max_loads[link_name], 3)}")

# plotting average throughput of switches
plt.figure(1)
for switch_name, values in switches_results.items():
    format_values = []
    for value in values['timestamp values']:
        format_values.append(round(value / 1000, 3))
    plt.plot(timestamps, format_values, label=f'{switch_name}')
plt.legend()
plt.grid()
plt.gca().ticklabel_format(axis='y', style='plain')
plt.xlabel("Time [s]")
plt.ylabel("Switch load [Kbps]")
plt.title("Switch load over time")

num_ticks = 20
tick_positions = np.linspace(timestamps[0], timestamps[-1], num_ticks)
plt.xticks(tick_positions)


# plotting average throughput of links
plt.figure(2)
for link_name, values in links_results.items():
    format_values = []
    for value in values['timestamp values']:
        format_values.append(round(value / 1000, 3))
    plt.plot(timestamps, format_values, label=f'{link_name}')
plt.legend()
plt.grid()
plt.gca().ticklabel_format(axis='y', style='plain')
plt.xlabel("Time [s]")
plt.ylabel("Link load [Kbps]")
plt.title("Link load over time")

num_ticks = 20
tick_positions = np.linspace(timestamps[0], timestamps[-1], num_ticks)
plt.xticks(tick_positions)

plt.figure(3)
for link_name, values in links_results.items():
    format_values = []
    for value in values['normalized values']:
        format_values.append(round(value, 3))
    plt.plot(timestamps, format_values, label=f'{link_name}')
plt.legend()
plt.grid()
plt.gca().ticklabel_format(axis='y', style='plain')
plt.xlabel("Time [s]")
plt.ylabel("Link load")
plt.title("Link load over time")

num_ticks = 20
tick_positions = np.linspace(timestamps[0], timestamps[-1], num_ticks)
plt.xticks(tick_positions)

# # plotting selected interfaces
# selected_interfaces = ['r1-eth2', 'r1-eth3', 'r1-eth4']
# plt.figure(2)
# for interface in selected_interfaces:
#     format_values = []
#     for value in if_combine_results[interface]['timestamp values']:
#         format_values.append(round(value / 1000, 3))
#     plt.plot(timestamps, format_values, label=f'{interface}')
# plt.legend()
# plt.grid()
# plt.gca().ticklabel_format(axis='y', style='plain')
# plt.xlabel("Time [s]")
# plt.ylabel("Interface load [Kbps]")
# plt.title("Interfaces load over time")
#
# num_ticks = 20
# tick_positions = np.linspace(timestamps[0], timestamps[-1], num_ticks)
# plt.xticks(tick_positions)

plt.show()
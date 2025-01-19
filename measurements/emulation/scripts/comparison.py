import csv
import argparse
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import yaml


parser = argparse.ArgumentParser()
# final tests
# Emu_topo_5_test_ppo_off_v1
# Emu_topo_5_test_ppo_on_v1
# Emu_topo_5_test_ppo_off_v2
# Emu_topo_5_test_ppo_on_v2
# Emu_topo_5_test_ppo_off_v3
# Emu_topo_5_test_ppo_on_v3

# Emu_topo_5_test_ppo_off_v1.2
# Emu_topo_5_test_ppo_on_v1.2
# Emu_topo_5_test_ppo_off_v2.2
# Emu_topo_5_test_ppo_on_v2.2
# Emu_topo_5_test_ppo_off_v3.2
# Emu_topo_5_test_ppo_on_v3.2

# Emu_topo_10_test_ppo_off_v1
# Emu_topo_10_test_ppo_on_v1
# Emu_topo_10_test_ppo_off_v2
# Emu_topo_10_test_ppo_on_v2
parser.add_argument('-e1', '--emulation-1', dest='emulation_1', default='Emu_topo_10_test_ppo_off_v2',
                    help='Name of the first traffic emulation to comparison')
parser.add_argument('-e2', '--emulation-2', dest='emulation_2', default='Emu_topo_10_test_ppo_on_v2',
                    help='Name of the second traffic emulation to comparison')
parser.add_argument('-ln', '--link-name', dest='link_name', default='r9-r10',
                    help='Name of the link to comparison')
parser.add_argument('-f', '--file', dest='file', default='topo_10_v2.yaml',
                    help='Topology file in .yaml format')
args = parser.parse_args()

font = {'family': 'monospace',
        'weight': 'bold',
        'size': 20}
matplotlib.rc('font', **font)
label_font_size = 15

topo_info = {}
with open(args.file) as f:
    try:
        topo_info = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(e)

if_in_bytes_csv_1 = []
with open(f'measurements/emulation/results/{args.emulation_1}/switches/if_in_bytes.csv') as file:
    csv_result = csv.reader(file)
    for row in csv_result:
        if_in_bytes_csv_1.append(row)

if_in_bytes_csv_2 = []
with open(f'measurements/emulation/results/{args.emulation_2}/switches/if_in_bytes.csv') as file:
    csv_result = csv.reader(file)
    for row in csv_result:
        if_in_bytes_csv_2.append(row)

if_out_bytes_csv_1 = []
with open(f'measurements/emulation/results/{args.emulation_1}/switches/if_out_bytes.csv') as file:
    csv_result = csv.reader(file)
    for row in csv_result:
        if_out_bytes_csv_1.append(row)

if_out_bytes_csv_2 = []
with open(f'measurements/emulation/results/{args.emulation_2}/switches/if_out_bytes.csv') as file:
    csv_result = csv.reader(file)
    for row in csv_result:
        if_out_bytes_csv_2.append(row)

rows_limit = 120

timestamps_1 = []
for row in if_out_bytes_csv_1:
    if len(timestamps_1) > rows_limit:
        break
    if int(row[0]) not in timestamps_1:
        timestamps_1.append(int(row[0]))

timestamps_2 = []
for row in if_out_bytes_csv_1:
    if len(timestamps_2) > rows_limit:
        break
    if int(row[0]) not in timestamps_2:
        timestamps_2.append(int(row[0]))

max_timestamp_1 = []
for row in if_in_bytes_csv_1:
    if int(row[0]) not in max_timestamp_1:
        max_timestamp_1.append(int(row[0]))

max_timestamp_2 = []
for row in if_in_bytes_csv_1:
    if int(row[0]) not in max_timestamp_2:
        max_timestamp_2.append(int(row[0]))

link_max_loads = {}
for link in topo_info['links']:
    link_max_loads[f"{link['node a']}-{link['node b']}"] = link['bw'] * 10**6 * 2

# ingress interface statistics
if_in_results_1 = {}
for row in if_in_bytes_csv_1:
    if row[1] not in if_in_results_1:
        if_in_results_1[row[1]] = {}
        if_in_results_1[row[1]]['mean'] = 0
        if_in_results_1[row[1]]['timestamp values'] = []
    if_in_results_1[row[1]]['mean'] += int(row[2]) * 8
    if_in_results_1[row[1]]['timestamp values'].append(int(row[2]) * 8)

for _, if_in_result in if_in_results_1.items():
    if_in_result['mean'] = if_in_result['mean'] / len(max_timestamp_1)
if_in_results_1 = dict(sorted(if_in_results_1.items()))

if_in_results_2 = {}
for row in if_in_bytes_csv_2:
    if row[1] not in if_in_results_2:
        if_in_results_2[row[1]] = {}
        if_in_results_2[row[1]]['mean'] = 0
        if_in_results_2[row[1]]['timestamp values'] = []
    if_in_results_2[row[1]]['mean'] += int(row[2]) * 8
    if_in_results_2[row[1]]['timestamp values'].append(int(row[2]) * 8)

for _, if_in_result in if_in_results_2.items():
    if_in_result['mean'] = if_in_result['mean'] / len(max_timestamp_2)
if_in_results_2 = dict(sorted(if_in_results_2.items()))

# egress interface statistics
if_out_results_1 = {}
for row in if_out_bytes_csv_1:
    if row[1] not in if_out_results_1:
        if_out_results_1[row[1]] = {}
        if_out_results_1[row[1]]['mean'] = 0
        if_out_results_1[row[1]]['timestamp values'] = []
    if_out_results_1[row[1]]['mean'] += int(row[2]) * 8
    if_out_results_1[row[1]]['timestamp values'].append(int(row[2]) * 8)

for _, if_in_result in if_out_results_1.items():
    if_in_result['mean'] = if_in_result['mean'] / len(max_timestamp_1)
if_out_results_1 = dict(sorted(if_out_results_1.items()))

if_out_results_2 = {}
for row in if_out_bytes_csv_2:
    if row[1] not in if_out_results_2:
        if_out_results_2[row[1]] = {}
        if_out_results_2[row[1]]['mean'] = 0
        if_out_results_2[row[1]]['timestamp values'] = []
    if_out_results_2[row[1]]['mean'] += int(row[2]) * 8
    if_out_results_2[row[1]]['timestamp values'].append(int(row[2]) * 8)

for _, if_in_result in if_out_results_2.items():
    if_in_result['mean'] = if_in_result['mean'] / len(max_timestamp_2)
if_out_results_2 = dict(sorted(if_out_results_2.items()))

# combine interface statistics
if_combine_results_1 = {}
for interface in if_in_results_1:
    if interface not in if_combine_results_1:
        if_combine_results_1[interface] = {}
        if_combine_results_1[interface]['mean'] = 0
        if_combine_results_1[interface]['timestamp values'] = []
    if_combine_results_1[interface]['mean'] = if_in_results_1[interface]['mean'] + if_out_results_1[interface]['mean']
    for ingress_value, egress_value in zip(if_in_results_1[interface]['timestamp values'],
                                           if_out_results_1[interface]['timestamp values']):
        if_combine_results_1[interface]['timestamp values'].append(ingress_value + egress_value)
if_combine_results_1 = dict(sorted(if_combine_results_1.items()))

if_combine_results_2 = {}
for interface in if_in_results_2:
    if interface not in if_combine_results_2:
        if_combine_results_2[interface] = {}
        if_combine_results_2[interface]['mean'] = 0
        if_combine_results_2[interface]['timestamp values'] = []
    if_combine_results_2[interface]['mean'] = if_in_results_2[interface]['mean'] + if_out_results_2[interface]['mean']
    for ingress_value, egress_value in zip(if_in_results_2[interface]['timestamp values'],
                                           if_out_results_2[interface]['timestamp values']):
        if_combine_results_2[interface]['timestamp values'].append(ingress_value + egress_value)
if_combine_results_2 = dict(sorted(if_combine_results_2.items()))

# switches statistics
switches_results_1 = {}
for interface, values in if_combine_results_1.items():
    switch_name = interface.split('-')[0]
    if switch_name not in switches_results_1:
        switches_results_1[switch_name] = {}
        switches_results_1[switch_name]['mean'] = 0
        switches_results_1[switch_name]['timestamp values'] = [0] * len(max_timestamp_1)
        switches_results_1[switch_name]['interfaces'] = []
    switches_results_1[switch_name]['mean'] += values['mean']
    for index, value in enumerate(values['timestamp values']):
        switches_results_1[switch_name]['timestamp values'][index] += value
    switches_results_1[switch_name]['interfaces'].append(interface)
switches_results_1 = dict(sorted(switches_results_1.items()))

switches_results_2 = {}
for interface, values in if_combine_results_2.items():
    switch_name = interface.split('-')[0]
    if switch_name not in switches_results_2:
        switches_results_2[switch_name] = {}
        switches_results_2[switch_name]['mean'] = 0
        switches_results_2[switch_name]['timestamp values'] = [0] * len(max_timestamp_2)
        switches_results_2[switch_name]['interfaces'] = []
    switches_results_2[switch_name]['mean'] += values['mean']
    for index, value in enumerate(values['timestamp values']):
        switches_results_2[switch_name]['timestamp values'][index] += value
    switches_results_2[switch_name]['interfaces'].append(interface)
switches_results_2 = dict(sorted(switches_results_2.items()))

# links statistics
links_results_1 = {}
for link in topo_info['links']:
    port_a = f"{link['node a']}-eth{link['port a']}"
    port_b = f"{link['node b']}-eth{link['port b']}"
    links_results_1[f'{link["node a"]}-{link["node b"]}'] = {}
    links_results_1[f'{link["node a"]}-{link["node b"]}']['mean'] = max(if_combine_results_1[port_a]['mean'],
                                                                        if_combine_results_1[port_b]['mean'])
    links_results_1[f'{link["node a"]}-{link["node b"]}']['timestamp values'] = []
    links_results_1[f'{link["node a"]}-{link["node b"]}']['normalized values'] = []
    for value_a, value_b in zip(if_combine_results_1[port_a]['timestamp values'],
                                if_combine_results_1[port_b]['timestamp values']):
        if value_a >= value_b:
            links_results_1[f'{link["node a"]}-{link["node b"]}']['timestamp values'].append(value_a)
            links_results_1[f'{link["node a"]}-{link["node b"]}']['normalized values'].append(
                value_a / link_max_loads[f'{link["node a"]}-{link["node b"]}'])
        else:
            links_results_1[f'{link["node a"]}-{link["node b"]}']['timestamp values'].append(value_b)
            links_results_1[f'{link["node a"]}-{link["node b"]}']['normalized values'].append(
                value_b / link_max_loads[f'{link["node a"]}-{link["node b"]}'])

links_results_2 = {}
for link in topo_info['links']:
    port_a = f"{link['node a']}-eth{link['port a']}"
    port_b = f"{link['node b']}-eth{link['port b']}"
    links_results_2[f'{link["node a"]}-{link["node b"]}'] = {}
    links_results_2[f'{link["node a"]}-{link["node b"]}']['mean'] = max(if_combine_results_2[port_a]['mean'],
                                                                        if_combine_results_2[port_b]['mean'])
    links_results_2[f'{link["node a"]}-{link["node b"]}']['timestamp values'] = []
    links_results_2[f'{link["node a"]}-{link["node b"]}']['normalized values'] = []
    for value_a, value_b in zip(if_combine_results_2[port_a]['timestamp values'],
                                if_combine_results_2[port_b]['timestamp values']):
        if value_a >= value_b:
            links_results_2[f'{link["node a"]}-{link["node b"]}']['timestamp values'].append(value_a)
            links_results_2[f'{link["node a"]}-{link["node b"]}']['normalized values'].append(
                value_a / link_max_loads[f'{link["node a"]}-{link["node b"]}'])
        else:
            links_results_2[f'{link["node a"]}-{link["node b"]}']['timestamp values'].append(value_b)
            links_results_2[f'{link["node a"]}-{link["node b"]}']['normalized values'].append(
                value_b / link_max_loads[f'{link["node a"]}-{link["node b"]}'])

link_name = args.link_name
link_info_1 = links_results_1[link_name]['normalized values']
link_info_2 = links_results_2[link_name]['normalized values']

plt.figure(1)
format_values = []
for value in link_info_1:
    if len(format_values) > rows_limit:
        break
    format_values.append(round(value, 3))
plt.plot(timestamps_1, format_values, label='Wyłączony agent ML')

format_values = []
for value in link_info_2:
    if len(format_values) > rows_limit:
        break
    format_values.append(round(value, 3))
plt.plot(timestamps_2, format_values, label='Włączony agent ML')

plt.legend(fontsize=label_font_size)
plt.grid()
plt.gca().ticklabel_format(axis='y', style='plain')
plt.xlabel("Czas emulacji [s]")
plt.ylabel("Znormalizowane obciążenie łącza")
plt.title(f"Porównanie znormalizowanych obciążeń łącza {link_name} w czasie")

num_ticks = 21
tick_positions = np.linspace(timestamps_1[0], timestamps_1[-1], num_ticks)
plt.xticks(tick_positions)

plt.show()

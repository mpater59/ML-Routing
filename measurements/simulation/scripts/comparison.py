import csv
import argparse
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import yaml

from cycler import cycler


parser = argparse.ArgumentParser()
# final tests
# Sim_topo_5_test_ppo_off_v1
# Sim_topo_5_test_ppo_on_v1
# Sim_topo_5_test_ppo_off_v2
# Sim_topo_5_test_ppo_on_v2
# Sim_topo_5_test_ppo_off_v3
# Sim_topo_5_test_ppo_on_v3

# Sim_topo_10_test_ppo_off_v1
# Sim_topo_10_test_ppo_on_v1
# Sim_topo_10_test_ppo_off_v2
# Sim_topo_10_test_ppo_on_v2
parser.add_argument('-e1', '--emulation-1', dest='emulation_1', default='Sim_topo_5_test_ppo_off_v3',
                    help='Name of the first traffic emulation to comparison')
parser.add_argument('-e2', '--emulation-2', dest='emulation_2', default='Sim_topo_5_test_ppo_on_v3',
                    help='Name of the second traffic emulation to comparison')
parser.add_argument('-ln', '--link-name', dest='link_name', default='r4-r5',
                    help='Name of the link to comparison')
parser.add_argument('-f', '--file', dest='file', default='topo.yaml',
                    help='Topology file in .yaml format')
args = parser.parse_args()

font = {'family': 'monospace',
        'weight': 'bold',
        'size': 15}
matplotlib.rc('font', **font)

topo_info = {}
with open(args.file) as f:
    try:
        topo_info = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(e)

switch_loads_csv_1 = []
with open(f'measurements/simulation/results/{args.emulation_1}/switch_loads.csv') as file:
    csv_result = csv.reader(file)
    for row in csv_result:
        switch_loads_csv_1.append(row)

switch_loads_csv_2 = []
with open(f'measurements/simulation/results/{args.emulation_2}/switch_loads.csv') as file:
    csv_result = csv.reader(file)
    for row in csv_result:
        switch_loads_csv_2.append(row)

link_loads_csv_1 = []
with open(f'measurements/simulation/results/{args.emulation_1}/link_loads.csv') as file:
    csv_result = csv.reader(file)
    for row in csv_result:
        link_loads_csv_1.append(row)

link_loads_csv_2 = []
with open(f'measurements/simulation/results/{args.emulation_2}/link_loads.csv') as file:
    csv_result = csv.reader(file)
    for row in csv_result:
        link_loads_csv_2.append(row)

rows_limit = 2000

timestamps_1 = []
for row in link_loads_csv_1:
    if len(timestamps_1) > rows_limit:
        break
    if int(row[0]) not in timestamps_1:
        timestamps_1.append(int(row[0]))

timestamps_2 = []
for row in link_loads_csv_2:
    if len(timestamps_2) > rows_limit:
        break
    if int(row[0]) not in timestamps_2:
        timestamps_2.append(int(row[0]))

link_max_loads = {}
for link in topo_info['links']:
    link_max_loads[f"{link['node a']}-{link['node b']}"] = link['bw'] * 10**6 * 2

link_loads_1 = {}
for row in link_loads_csv_1:
    if row[1] not in link_loads_1:
        link_loads_1[row[1]] = {}
        link_loads_1[row[1]]['mean'] = 0
        link_loads_1[row[1]]['timestamp values'] = []
        link_loads_1[row[1]]['normalized values'] = []
    link_loads_1[row[1]]['mean'] += int(row[2])
    link_loads_1[row[1]]['timestamp values'].append(int(row[2]))
    link_loads_1[row[1]]['normalized values'].append(int(row[2]) / link_max_loads[row[1]])

link_loads_2 = {}
for row in link_loads_csv_2:
    if row[1] not in link_loads_2:
        link_loads_2[row[1]] = {}
        link_loads_2[row[1]]['mean'] = 0
        link_loads_2[row[1]]['timestamp values'] = []
        link_loads_2[row[1]]['normalized values'] = []
    link_loads_2[row[1]]['mean'] += int(row[2])
    link_loads_2[row[1]]['timestamp values'].append(int(row[2]))
    link_loads_2[row[1]]['normalized values'].append(int(row[2]) / link_max_loads[row[1]])

switch_loads_1 = {}
for row in switch_loads_csv_1:
    if row[1] not in switch_loads_1:
        switch_loads_1[row[1]] = {}
        switch_loads_1[row[1]]['mean'] = 0
        switch_loads_1[row[1]]['timestamp values'] = []
    switch_loads_1[row[1]]['mean'] += int(row[2])
    switch_loads_1[row[1]]['timestamp values'].append(int(row[2]))

switch_loads_2 = {}
for row in switch_loads_csv_2:
    if row[1] not in switch_loads_2:
        switch_loads_2[row[1]] = {}
        switch_loads_2[row[1]]['mean'] = 0
        switch_loads_2[row[1]]['timestamp values'] = []
    switch_loads_2[row[1]]['mean'] += int(row[2])
    switch_loads_2[row[1]]['timestamp values'].append(int(row[2]))

for _, value in link_loads_1.items():
    value['mean'] = value['mean'] / len(timestamps_1)

for _, value in link_loads_2.items():
    value['mean'] = value['mean'] / len(timestamps_2)

for _, value in switch_loads_1.items():
    value['mean'] = value['mean'] / len(timestamps_1)

for _, value in switch_loads_2.items():
    value['mean'] = value['mean'] / len(timestamps_2)

link_name = args.link_name

link_info_1 = link_loads_1[link_name]['normalized values']
link_info_2 = link_loads_2[link_name]['normalized values']

plt.figure(1)
format_values = []
for value in link_info_1:
    if len(format_values) > rows_limit:
        break
    format_values.append(round(value, 3))
plt.plot(timestamps_1, format_values, label='Disabled ML agent')

format_values = []
for value in link_info_2:
    if len(format_values) > rows_limit:
        break
    format_values.append(round(value, 3))
plt.plot(timestamps_2, format_values, label='Enabled ML agent')

plt.legend()
plt.grid()
plt.gca().ticklabel_format(axis='y', style='plain')
plt.xlabel("Time [s]")
plt.ylabel("Link load")
plt.title(f"{link_name} link load comparison over time")

num_ticks = 21
tick_positions = np.linspace(timestamps_1[0], timestamps_1[-1], num_ticks)
plt.xticks(tick_positions)

plt.show()

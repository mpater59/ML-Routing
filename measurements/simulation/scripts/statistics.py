import csv
import argparse
import matplotlib.pyplot as plt
import numpy as np
import yaml


parser = argparse.ArgumentParser()
# 5-node topo
# Simulation_test_v1
# Simulation_test_ppo_v1
# Simulation_test_v2
# Simulation_test_ppo_v2
# Simulation_test_ppo_v2.1
# Simulation_test_v3
# Simulation_test_ppo_v3

# 10-node topo
# Topo_10_test_v1
# Topo_10_test_ppo_v1
# Topo_10_test_v2
# Topo_10_test_ppo_v2
# Topo_10_test_v3
# Topo_10_test_ppo_v3
# Topo_10_test_ppo_v3.1

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
parser.add_argument('-e', '--emulation', dest='emulation', default='Sim_topo_10_test_ppo_on_v2',
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

switch_loads_csv = []
with open(f'measurements/simulation/results/{args.emulation}/switch_loads.csv') as file:
    csv_result = csv.reader(file)
    for row in csv_result:
        switch_loads_csv.append(row)

link_loads_csv = []
with open(f'measurements/simulation/results/{args.emulation}/link_loads.csv') as file:
    csv_result = csv.reader(file)
    for row in csv_result:
        link_loads_csv.append(row)

rows_limit = 2000

timestamps = []
for row in switch_loads_csv:
    if len(timestamps) > rows_limit:
        break
    if int(row[0]) not in timestamps:
        timestamps.append(int(row[0]))

link_max_loads = {}
for link in topo_info['links']:
    link_max_loads[f"{link['node a']}-{link['node b']}"] = link['bw'] * 10**6 * 2

link_loads = {}
for row in link_loads_csv:
    if row[1] not in link_loads:
        link_loads[row[1]] = {}
        link_loads[row[1]]['mean'] = 0
        link_loads[row[1]]['timestamp values'] = []
        link_loads[row[1]]['normalized values'] = []
    link_loads[row[1]]['mean'] += int(row[2])
    link_loads[row[1]]['timestamp values'].append(int(row[2]))
    link_loads[row[1]]['normalized values'].append(int(row[2]) / link_max_loads[row[1]])

switch_loads = {}
for row in switch_loads_csv:
    if row[1] not in switch_loads:
        switch_loads[row[1]] = {}
        switch_loads[row[1]]['mean'] = 0
        switch_loads[row[1]]['timestamp values'] = []
    switch_loads[row[1]]['mean'] += int(row[2])
    switch_loads[row[1]]['timestamp values'].append(int(row[2]))

for _, value in link_loads.items():
    value['mean'] = value['mean'] / len(timestamps)

for _, value in switch_loads.items():
    value['mean'] = value['mean'] / len(timestamps)


print('Printing switch average throughput:\n')
for switch_name, values in switch_loads.items():
    print(f"Switch {switch_name}:")
    print(f"Total average throughput: {round(values['mean'] / 1000, 3)} Kbps")
    print()

print()
print('Printing link average throughput:')
for link_name, values in link_loads.items():
    print(f"Link {link_name} - average throughput: {round(values['mean'] / 1000, 3)} Kbps")

print()
print('Printing link normalized average load:')
for link_name, values in link_loads.items():
    print(f"Link {link_name} - average load: {round(values['mean'] / link_max_loads[link_name], 3)}")

# plotting average throughput of switches
plt.figure(1)
for switch_name, values in switch_loads.items():
    format_values = []
    for value in values['timestamp values']:
        if len(format_values) > rows_limit:
            break
        format_values.append(round(value / 1000, 3))
    plt.plot(timestamps, format_values, label=f'{switch_name}')
plt.legend()
plt.grid()
plt.gca().ticklabel_format(axis='y', style='plain')
plt.xlabel("Time [s]")
plt.ylabel("Switch load [Kbps]")
plt.title("Switch load over time")

num_ticks = 21
tick_positions = np.linspace(timestamps[0], timestamps[-1], num_ticks)
plt.xticks(tick_positions)


# plotting average throughput of links
plt.figure(2)
for link_name, values in link_loads.items():
    format_values = []
    for value in values['timestamp values']:
        if len(format_values) > rows_limit:
            break
        format_values.append(round(value / 1000, 3))
    plt.plot(timestamps, format_values, label=f'{link_name}')
plt.legend()
plt.grid()
plt.gca().ticklabel_format(axis='y', style='plain')
plt.xlabel("Time [s]")
plt.ylabel("Link load [Kbps]")
plt.title("Link load over time")

num_ticks = 21
tick_positions = np.linspace(timestamps[0], timestamps[-1], num_ticks)
plt.xticks(tick_positions)

plt.figure(3)
for link_name, values in link_loads.items():
    format_values = []
    for value in values['normalized values']:
        if len(format_values) > rows_limit:
            break
        format_values.append(round(value, 3))
    plt.plot(timestamps, format_values, label=f'{link_name}')
plt.legend()
plt.grid()
plt.gca().ticklabel_format(axis='y', style='plain')
plt.xlabel("Time [s]")
plt.ylabel("Link load")
plt.title("Link load over time")

num_ticks = 21
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

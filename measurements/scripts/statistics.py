import csv
import argparse


parser = argparse.ArgumentParser()
parser.add_argument('-e', '--emulation', dest='emulation', default='test_5_42_v1',
                    help='Traffic emulation name')
args = parser.parse_args()

if_in_bytes_csv = []
with open(f'measurements/results/{args.emulation}/switches/if_in_bytes.csv') as file:
    csv_result = csv.reader(file)
    for row in csv_result:
        if_in_bytes_csv.append(row)

if_out_bytes_csv = []
with open(f'measurements/results/{args.emulation}/switches/if_out_bytes.csv') as file:
    csv_result = csv.reader(file)
    for row in csv_result:
        if_out_bytes_csv.append(row)

timestamps = []
for row in if_in_bytes_csv:
    if row[0] not in timestamps:
        timestamps.append(row[0])

# ingress interface statistics
if_in_results = {}
for row in if_in_bytes_csv:
    if row[1] not in if_in_results:
        if_in_results[row[1]] = {}
        if_in_results[row[1]]['mean'] = 0
        if_in_results[row[1]]['timestamp values'] = []
    if_in_results[row[1]]['mean'] += int(row[2])
    if_in_results[row[1]]['timestamp values'].append(int(row[2]))

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
    if_out_results[row[1]]['mean'] += int(row[2])
    if_out_results[row[1]]['timestamp values'].append(int(row[2]))

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

print('Printing average throughput:\n')
for switch_name, values in switches_results.items():
    print(f"Switch {switch_name}:")
    print(f"Total average throughput: {round(values['mean'] * 8 / 1000, 3)} Kbps")
    for interface in values['interfaces']:
        print(f"Interface {interface} average throughput: "
              f"{round(if_combine_results[interface]['mean'] * 8 / 1000, 3)} Kbps")
    print()

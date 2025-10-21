import os
import re
import json
import socket
host=socket.gethostname()
host = re.findall("[a-zA-Z]+", host)[0]
queue="pdebug"
# if host == "elcap":
#     queue="rabbit"
# elif host == "tuolumne":
#     queue="pdat_0711"
elcap_exclusion = {"elcap[2537-2552]", "elcap[2585-2600]", "elcap[2601-2616]", "elcap[2649-2664]", "elcap[2697-2712]", "elcap[2713-2728]", "elcap[2729-2744]", "elcap[2777-2792]", "elcap[2809-2824]", "elcap[2841-2856]", "elcap[2857-2872]", "elcap[2953-2968]", "elcap[2969-2984]", "elcap[2985-3000]", "elcap[3001-3016]",
                "elcap[3033-3048]",  "elcap[3049-3064]","elcap[3065-3080]","elcap[3081-3096]","elcap[3113-3128]","elcap[3161-3176]","elcap[3209-3224]","elcap[3225-3240]","elcap[3241-3256]","elcap[3257-3272]","elcap[3273-3288]"}
if queue == "pbatch":
    tuo_rabbit_queue_range = set(node_idx for node_idx in range(1049, 2148 + 1))
else:
    tuo_rabbit_queue_range = set(node_idx for node_idx in range(1005, 1044 + 1))
cmd = f"flux resource list -q {queue} | grep free | awk -F' ' {{'print $6'}} | sed 's/{host}//g' | sed 's/\]//g' | sed 's/\[//g'"
lines = os.popen(cmd).read().split("\n")
free_ranges = set()
for value in lines:
    free_ranges_str = value.split(",")
    # print(free_ranges_str)
    for range_str in free_ranges_str:
        values = range_str.split("-")
        if len(values) != 1 or values[0] != "":
            if len(values) == 1:
                free_ranges.add(int(values[0]))
            else:
                #print(values)
                free_ranges.update(set(range(int(values[0]),int(values[1])+1)))
# print(free_ranges)
cmd = f"flux resource list -q {queue} | grep allocated | awk -F' ' {{'print $6'}} | sed 's/{host}//g' | sed 's/\]//g' | sed 's/\[//g'"
lines = os.popen(cmd).read().split("\n")
allocated_ranges = set()
for value in lines:
    allocated_ranges_str = value.split(",") # value.replace("\n", "").split(",")
    for range_str in allocated_ranges_str:
        values = range_str.split("-")
        if len(values) != 1 or values[0] != "":
            # print(values)
            if len(values) == 1:
                allocated_ranges.add(int(values[0]))
            else:
                allocated_ranges.update(set(range(int(values[0]),int(values[1])+1)))
# print(allocated_ranges, free_ranges)
all_ranges = allocated_ranges
all_ranges.update(free_ranges)
# print(all_ranges)
# free_ranges = all_ranges

# project_path="/usr/workspace/haridev/rabbits"
with open(f"/etc/flux/system/rabbitmapping", "r") as jsonFile:
    mapping = json.load(jsonFile)


rabbits = mapping["rabbits"]
final_list = set()
for rabbit_node, value in rabbits.items():
    m = re.search(f'{host}\[(.+?)\]', value["hostlist"])
    if m:
        found = m.group(1)
        values = found.split("-")
        compute_nodes = set(range(int(values[0]),int(values[1])+1))
        # in_rabbit_queue = rabbit_queue_range.intersection(compute_nodes)
        #if len(in_rabbit_queue) == len(compute_nodes):
        left = compute_nodes - free_ranges
        # print(compute_nodes, left)
        if len(left) == 0:
            # print(len(left))
            final_list.add(value["hostlist"])
final = final_list
# if host == "elcap":
#     final = final - elcap_exclusion
if len(final) < 1:
    final_list = set()
    for rabbit_node, value in rabbits.items():
        m = re.search(f'{host}\[(.+?)\]', value["hostlist"])
        if m:
            found = m.group(1)
            values = found.split("-")
            compute_nodes = set(range(int(values[0]),int(values[1])+1))
            # in_rabbit_queue = rabbit_queue_range.intersection(compute_nodes)
            #if len(in_rabbit_queue) == len(compute_nodes):
            left = compute_nodes - all_ranges
            # print(compute_nodes, left)
            if len(left) == 0:
                # print(len(left))
                final_list.add(value["hostlist"])
    final = final_list

# final = ["tuolumne[1881-1896]", "tuolumne[1865-1880]"]
# if len(final) == 0:
#     final = rabbit_queue_list
# if host == "elcap":
#     final = final - elcap_exclusion
if host == "elcap":
    final = list(final)[:256]
# print(len(final))
value = " ".join(sorted(final))
print(value)

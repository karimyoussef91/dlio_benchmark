import psutil
import socket

p = psutil.Process()
cores_available = len(p.cpu_affinity())
print("cores available: " + str(cores_available) , " on host " , socket.gethostname())

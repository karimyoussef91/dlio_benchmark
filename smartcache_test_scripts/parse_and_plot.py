import argparse
import re
import matplotlib.pyplot as plt
import os

def parse_log_file(filename):
    pattern = re.compile(r'Throughput \(samples/second\): ([\d\.]+)')
    epochs = []
    throughputs = []
    with open(filename, 'r') as f:
        for line in f:
            if "Epoch" in line:
                match = pattern.search(line)
                if match:
                    epoch_match = re.search(r'Epoch (\d+)', line)
                    epoch = int(epoch_match.group(1)) if epoch_match else len(epochs) + 1
                    epochs.append(epoch)
                    throughputs.append(float(match.group(1)))
    return epochs, throughputs

def convert_to_gbps(samples_per_sec, sample_size_bytes):
    return [(s * sample_size_bytes) / (1024**3) for s in samples_per_sec]

def main():
    parser = argparse.ArgumentParser(description='Plot I/O throughput from log files.')
    parser.add_argument('sample_size', type=int, help='Sample size in bytes')
    parser.add_argument('log_files', nargs='+', help='Log file names')
    parser.add_argument('--output', '-o', type=str, default='io_throughput_latest.png', help='Output image file name (default: io_throughput.png)')
    args = parser.parse_args()

    plt.rcParams.update({'font.size': 28})
    plt.figure(figsize=(10, 6))
    for log_file in args.log_files:
        epochs, throughputs = parse_log_file(log_file)
        gbps = convert_to_gbps(throughputs, args.sample_size)
        label = os.path.splitext(os.path.basename(log_file))[0]
        plt.plot(epochs, gbps, marker='o', label=label)

    plt.xlabel('Epoch')
    plt.ylabel('I/O Throughput (GB/s)')
    plt.title('I/O Throughput per Epoch')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.gca().xaxis.set_major_locator(plt.MaxNLocator(integer=True))  # Ensure integer X axis
    plt.savefig(args.output)
    print(f"Plot saved as {args.output}")

if __name__ == '__main__':
    main()
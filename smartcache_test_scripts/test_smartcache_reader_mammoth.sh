#!/bin/bash

module --force purge
module load StdEnv  gcc/13.3.1 mvapich2/2.3.7

source /p/lustre1/youssef2/dlio_bench_venv/bin/activate

# Default values for environment variables
num_samples=320
uv_threadpool_size=4
smartcache_block_size=$((2*1024*1024))
smartcache_ranks_per_node=1
application_ranks_per_node=16
num_blocks=1024
pfs_blocks_path=/p/lustre3/youssef2/smartcache_blocks_${num_samples}
smartcache_base_path=/tmp/smartcache_dir/
smartcache_bin_dir=/p/vast1/youssef2/smartcache/build_mammoth/bin
shuffle=0
slurm=true

export DFTRACER_ENABLE=1

# ulimit -n 16384

# Parse command-line options
while [[ $# -gt 0 ]]; do
    case $1 in
        --uv_threadpool_size=*)
            uv_threadpool_size="${1#*=}"
            shift
            ;;
        --smartcache_block_size=*)
            smartcache_block_size="${1#*=}"
            shift
            ;;
        --smartcache_ranks_per_node=*)
            smartcache_ranks_per_node="${1#*=}"
            shift
            ;;
        --application_ranks_per_node=*)
            application_ranks_per_node="${1#*=}"
            shift
            ;;
        --num_blocks=*)
            num_blocks="${1#*=}"
            shift
            ;;
        --pfs_blocks_path=*)
            pfs_blocks_path="${1#*=}"
            shift
            ;;
        --smartcache_base_path=*)
            smartcache_base_path="${1#*=}"
            shift
            ;;
        --smartcache_bin_dir=*)
            smartcache_bin_dir="${1#*=}"
            shift
            ;;
        --num_samples=*)
        num_samples="${1#*=}"
        shift
        ;;
        --slurm)
            slurm=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done


# source ~/load_dev.sh
export DFTRACER_ENABLE=0
export DFTRACER_DISABLE_IO=0
export DFTRACER_INC_METADATA=0
export UV_THREADPOOL_SIZE=${uv_threadpool_size}
export SMARTCACHE_RANKS_PER_NODE=${smartcache_ranks_per_node}
export APPLICATION_RANKS_PER_NODE=${application_ranks_per_node}
export NUM_BLOCKS=${num_blocks}
export PFS_BLOCKS_PATH=${pfs_blocks_path}
export SMARTCACHE_BIN_DIR=${smartcache_bin_dir}

export SC_BLOCK_SIZE_BYTES=${smartcache_block_size}
export SC_BLOCK_DIR=${smartcache_base_path}
# export OMP_NUM_THREADS=4


# rm -rf ${pfs_blocks_path}
# mkdir ${pfs_blocks_path}

### Run SmartCache
echo "Starting smartcache service..."
# hosts="$(flux resource list --format={nodelist} | flux hostlist -e | tr ' ' '\n' | tail -n+2 | sed -e ':a' -e 'N' -e '$!ba' -e 's/\n/:'$smartcache_ranks_per_node',/g'):${smartcache_ranks_per_node}"
# echo "hosts: ${hosts}"

nnodes=0
if ${slurm}; then
    nnodes=$(scontrol show hostnames | wc -l)
else
    nnodes=$(flux resource list --format={nnodes} | tail -n 1)
fi
# nnodes=$(flux resource list --format={nnodes} | tail -n 1)
ranks=$((${nnodes}*${smartcache_ranks_per_node}))
cores=$((${nnodes}*(${smartcache_ranks_per_node} + ${uv_threadpool_size})))

run_prefix=""

if ${slurm}; then
    run_prefix="srun"
else
    run_prefix="flux run"
fi

srun -N ${nnodes} -n ${nnodes} -c 1 bash -c "rm -rf /l/ssd/*"
# valgrind --leak-check=full --show-leak-kinds=all --track-origins=yes --log-file=valgrind.%p.txt 

export DFTRACER_DISABLE_IO=0
export DFTRACER_INC_METADATA=0

# ${run_prefix} -N ${nnodes} rm -rf ${smartcache_base_path}
# mpirun -np ${ranks} --map-by slot:PE=${uv_threadpool_size} --bind-to core -host ${hosts} -x DFTRACER_ENABLE -x DFTRACER_DISABLE_IO -x DFTRACER_INC_METADATA -x UV_THREADPOOL_SIZE ${smartcache_bin_dir}/smartcache_service -b ${smartcache_base_path} -s ${smartcache_block_size} &
${run_prefix} -n ${nnodes} -c $((${uv_threadpool_size} + 1)) bash -c "export DFTRACER_ENABLE=1; export DFTRACER_DISABLE_IO=0; export DFTRACER_INC_METADATA=1; ${smartcache_bin_dir}/smartcache_service -b ${smartcache_base_path} -p ${pfs_blocks_path} -s ${smartcache_block_size}" &
smartcache_pid=$!
sleep 60 # Wait for SmartCache to start

# ${run_prefix} -N ${nnodes} ls ${smartcache_base_path}
# ${run_prefix} -N ${nnodes} ls /tmp


# export DLIO_LOG_LEVEL="debug"

# rm -rf /p/lustre5/youssef2/dlio_data/unet3d_smartcache/

# echo "Generating Data..."
# flux run -N 8 -n 8 dlio_benchmark workload=unet3d_h100 \
# ++workload.workflow.generate_data=True \
# ++workload.workflow.train=False \
# workload.dataset.data_folder=/p/lustre5/youssef2/dlio_data/unet3d_smartcache/ \
# workload.dataset.format=indexed_binary_smartcache \
# workload.dataset.num_samples_per_file=1 \
# workload.dataset.num_files_train=1280 \
# ++hydra.run.dir=/p/lustre5/youssef2/unet3d_output_baseline \
# ++workload.reader.smartcache_correctness_test=False \
# workload.dataset.record_length_bytes_stdev=0

# echo "Removing cached copies"
# flux run -N 2 -n 2 python remove_local_smartcache_blocks.py /l/ssd/smartcache_dir/

# export FI_OFI_RXM_EAGER_SIZE=$((2*1024*1024))
# export FI_LOG_LEVEL=debug
# export FI_PROVIDER=cxi   # or psm2, gni, etc., depending on your hardware

# export FI_CXI_DEFAULT_TX_SIZE=$((32*1024))
# export MPICH_OFI_MAX_RMA_TRANSACTIONS=512
ulimit -n 16384

proc_per_node=4
read_threads=4
numcores=$((${nnodes} * ${proc_per_node} * ${read_threads}))
echo "num_samples: ${num_samples}"
echo "Training..."
srun -n $((${nnodes}*${proc_per_node})) -c ${read_threads} bash -c "export DFTRACER_ENABLE=1; \
export DFTRACER_DISABLE_IO=0; \
export DFTRACER_INC_METADATA=1; \
dlio_benchmark workload=unet3d_h100 \
++workload.workflow.generate_data=False \
++workload.workflow.train=True \
workload.dataset.data_folder=/p/lustre3/youssef2/dlio_data/unet3d_smartcache_${num_samples}/ \
workload.dataset.format=indexed_binary_smartcache \
workload.dataset.num_samples_per_file=1 \
workload.dataset.num_files_train=${num_samples} \
++hydra.run.dir=/p/lustre3/youssef2/unet3d_output_smartcache_${num_samples} \
++workload.reader.smartcache_correctness_test=False \
workload.dataset.record_length_bytes_stdev=0 \
workload.train.computation_time=0"


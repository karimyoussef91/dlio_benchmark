#!/bin/bash

# export DLIO_LOG_LEVEL="debug"

module --force purge
module load StdEnv  gcc/11.2.1-magic libfabric/2.1 cray-mpich/9.0.1

source /p/lustre5/youssef2/dlio_bench_venv/bin/activate

export LD_LIBRARY_PATH=/p/lustre5/youssef2/dlio_bench_venv/lib/:${LD_LIBRARY_PATH}

flux run -N 8 --tasks-per-node=16 --cores=512 --setopt=mpibind=off dlio_benchmark workload=unet3d_h100 \
++workload.workflow.generate_data=False \
++workload.workflow.train=True \
workload.dataset.data_folder=/p/lustre5/youssef2/dlio_data/unet3d_baseline_20480/ \
workload.dataset.format=indexed_binary \
workload.dataset.num_samples_per_file=1 \
workload.dataset.num_files_train=20480 \
++hydra.run.dir=/p/lustre5/youssef2/unet3d_output_baseline_20480 \
workload.dataset.record_length_bytes_stdev=0 \
workload.train.computation_time=0

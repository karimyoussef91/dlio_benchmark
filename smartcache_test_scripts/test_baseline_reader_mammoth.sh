#!/bin/bash

# export DLIO_LOG_LEVEL="debug"

module --force purge
module load StdEnv  gcc/13.3.1 mvapich2/2.3.7

source /p/lustre1/youssef2/dlio_bench_venv/bin/activate

srun -n 32 -c 1 bash -c "export DFTRACER_ENABLE=1; \
export DFTRACER_DISABLE_IO=0; \
export DFTRACER_INC_METADATA=1; \
export DFTRACER_DISABLE_TIDS=0; \
dlio_benchmark workload=unet3d_h100 \
++workload.workflow.generate_data=False \
++workload.workflow.train=True \
workload.dataset.data_folder=/p/lustre3/youssef2/dlio_data/unet3d_baseline_320/ \
workload.dataset.format=indexed_binary \
workload.dataset.num_samples_per_file=1 \
workload.dataset.num_files_train=320 \
workload.reader.read_threads=0 \
++hydra.run.dir=/p/lustre3/youssef2/unet3d_output_baseline_320 \
workload.dataset.record_length_bytes_stdev=0 \
workload.train.computation_time=0"

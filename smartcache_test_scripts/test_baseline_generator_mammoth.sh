#!/bin/bash

# export DLIO_LOG_LEVEL="debug"
module --force purge
module load StdEnv  gcc/13.3.1 mvapich2/2.3.7

source /p/lustre1/youssef2/dlio_bench_venv/bin/activate

export num_samples=320

srun -n 16 -c 1 dlio_benchmark workload=unet3d_h100 \
++workload.workflow.generate_data=True \
++workload.workflow.train=False \
workload.dataset.data_folder=/p/lustre3/youssef2/dlio_data/unet3d_baseline_${num_samples}/ \
workload.dataset.format=indexed_binary \
workload.dataset.num_samples_per_file=1 \
workload.dataset.num_files_train=${num_samples} \
++hydra.run.dir=/p/lustre3/youssef2/unet3d_output_baseline_${num_samples}_generate \
workload.dataset.record_length_bytes_stdev=0

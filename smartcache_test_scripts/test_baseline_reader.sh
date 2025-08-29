#!/bin/bash

export DLIO_LOG_LEVEL="debug"

source /p/lustre5/youssef2/dlio_bench_venv/bin/activate

flux run -N 2 -n 8 dlio_benchmark workload=unet3d_h100 \
++workload.workflow.generate_data=False \
++workload.workflow.train=True \
workload.dataset.data_folder=/p/lustre5/youssef2/dlio_data/unet3d_baseline/ \
workload.dataset.format=indexed_binary \
++hydra.run.dir=/p/lustre5/youssef2/unet3d_output_baseline

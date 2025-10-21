#!/bin/bash

source ~/load_dev_tuo.sh

flux run -N 8 --tasks-per-node=4 --cores=128 python test_affinity.py

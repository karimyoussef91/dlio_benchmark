#!/bin/bash

base_dir="$1"

if [[ -z "$base_dir" ]]; then
    echo "Usage: $0 /path/to/base_dir"
    exit 1
fi

find "$base_dir" -maxdepth 1 -type f -name 'img_*_of_20480.indexed_binary_smartcache' | \
    parallel -j80 'tail -n 70 {} > {}.tmp && mv {}.tmp {}'
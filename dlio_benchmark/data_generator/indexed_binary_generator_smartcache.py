"""
   Copyright (c) 2025, UChicago Argonne, LLC
   All Rights Reserved

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

from dlio_benchmark.common.enumerations import Compression
from dlio_benchmark.data_generator.data_generator import DataGenerator

import logging
import numpy as np

from dlio_benchmark.utils.utility import progress, utcnow, DLIOMPI, get_first_subdirectory
from dlio_benchmark.utils.utility import Profile
from shutil import copyfile
from dlio_benchmark.common.constants import MODULE_DATA_GENERATOR
import struct
from mpi4py import MPI

import os 
import math

# SmartCache
import smartcache_py

#Debugging
import socket




dlp = Profile(MODULE_DATA_GENERATOR)

"""
Generator for creating data in NPZ format.
"""
class IndexedBinaryGeneratorSmartCache(DataGenerator):
    def __init__(self):
        super().__init__()
        self.smartcache_block_size = int(os.getenv("SC_BLOCK_SIZE_BYTES", 2 * 1024 * 1024)) # Defaults to 2MB if not set
        self.block_hash_size = 64
        self.delimiter_size = 1
        self.smartcache_mt_line_size = self.block_hash_size + self.delimiter_size
        smc_dir = os.getenv("SC_BLOCK_DIR", "/tmp/smartcache_dir")
        local_smc_rank = get_first_subdirectory(smc_dir)

        if local_smc_rank is None:
            raise Exception("Error: SmartCache directory structure -- No rank subdir")

        local_smc_rank_path = smc_dir + "/" + local_smc_rank
        self.smc_client = smartcache_py.SmartCacheClient(local_smc_rank_path, self.smartcache_block_size)

    def index_file_path_off(self, prefix_path):
        return prefix_path + '.off.idx'

    def index_file_path_size(self, prefix_path):
        return prefix_path + '.sz.idx'

    @dlp.log
    def generate(self):
        """
        Generator for creating data in binary format of 3d dataset.
        """
        super().generate()
        # np.random.seed(10)
        GB=1024*1024*1024
        samples_processed = 0
        total_samples = self.total_files_to_generate * self.num_samples
        dim = self.get_dimension(self.total_files_to_generate)
        # self.logger.info(dim)
        
        for i in dlp.iter(range(self.my_rank, int(self.total_files_to_generate), self.comm_size)):
            # np.random.seed(10 + self.my_rank + i)
            np.random.seed()
            dim1 = dim[2*i]
            dim2 = dim[2*i + 1]
            sample_size = dim1 * dim2
            total_size = sample_size * self.num_samples
            write_size = total_size

            # SmartCache specific
            sample_num_blocks = math.ceil(sample_size / self.smartcache_block_size)
            total_num_blocks = sample_num_blocks * self.num_samples # math.ceil(total_size / self.smartcache_block_size)
            sample_smartcache_metadata_bytes = self.smartcache_mt_line_size * sample_num_blocks
            total_smartcache_metadata_bytes = self.smartcache_mt_line_size * total_num_blocks

            memory_size = self._args.generation_buffer_size
            if total_size > memory_size:
                write_size = memory_size - (memory_size % sample_size)
            out_path_spec = self.storage.get_uri(self._file_list[i])
            out_path_spec_off_idx = self.index_file_path_off(out_path_spec)
            out_path_spec_sz_idx = self.index_file_path_size(out_path_spec)

            if self._args.smartcache_correctness_test:
                self.logger.debug(f"ref files ")
                out_path_spec_ref = out_path_spec + ".ref"
                out_path_spec_off_idx_ref = out_path_spec_off_idx + ".ref"
                out_path_spec_sz_idx_ref = out_path_spec_sz_idx + ".ref"
                self.logger.debug(f"ref files {out_path_spec_ref} , {out_path_spec_off_idx_ref} , {out_path_spec_sz_idx_ref} ")

            progress(i + 1, self.total_files_to_generate, "Generating Indexed Binary Data")
            prev_out_spec = out_path_spec
            written_bytes = 0
            data_file = open(out_path_spec, "a")
            off_file = open(out_path_spec_off_idx, "wb")
            sz_file = open(out_path_spec_sz_idx, "wb")

            if self._args.smartcache_correctness_test:
                data_file_ref = open(out_path_spec_ref, "wb")
                off_file_ref = open(out_path_spec_off_idx_ref, "wb")
                sz_file_ref = open(out_path_spec_sz_idx_ref, "wb")
                self.logger.debug(f"Opened ref files")

            records = np.random.randint(255, size=write_size, dtype=np.uint8)
            while written_bytes < total_size:
                data_to_write = write_size if written_bytes + write_size <= total_size else total_size - written_bytes
                samples_to_write = data_to_write // sample_size

                # Write data
                myfmt = 'B' * data_to_write
                binary_data = struct.pack(myfmt, *records[:data_to_write])

                if self._args.smartcache_correctness_test:
                    self.logger.debug(f"Writing ref files")
                    data_file_ref.write(binary_data)
                    struct._clearcache()

                    # Write offsets
                    myfmt = 'Q' * samples_to_write
                    offsets_ref = range(0, data_to_write, sample_size)
                    offsets_ref = offsets_ref[:samples_to_write]
                    binary_offsets_ref = struct.pack(myfmt, *offsets_ref)
                    off_file_ref.write(binary_offsets_ref)

                    # Write sizes
                    myfmt = 'Q' * samples_to_write
                    sample_sizes_ref = [sample_size] * samples_to_write
                    binary_sizes_ref = struct.pack(myfmt, *sample_sizes_ref)
                    sz_file_ref.write(binary_sizes_ref)
                
                samples_data = [binary_data[k*sample_size:(k+1)*sample_size] for k in range(0, self.num_samples)]

                sample_chunks = []
                for sample_idx in range(0, self.num_samples):
                    chunks = [samples_data[sample_idx][j:j + self.smartcache_block_size] for j in range(0, sample_size, self.smartcache_block_size)]
                    sample_chunks.append(chunks)
                
                for chunks in sample_chunks:
                    for chunk in chunks:
                        padded = False
                        if len(chunk) < self.smartcache_block_size:
                            padding_size = self.smartcache_block_size - len(chunk)
                            self.logger.debug(f"Padding chunk with {padding_size} bytes at the end of sample for {out_path_spec}")
                            chunk = chunk.ljust(self.smartcache_block_size, b'\x00')
                            padded = True
                        block_hash = self.smc_client.write_pfs("/p/lustre5/youssef2/smartcache_blocks_20480", chunk)
                        # debug
                        hostname = socket.gethostname()
                        self.logger.debug(f"written block with hash {block_hash} for sample in file {out_path_spec} on host {hostname}")
                        if padded:
                            self.logger.debug(f"block {block_hash} PADDED")
                        data_file.write(block_hash + "\n")
                struct._clearcache()
                
                # Write offsets
                myfmt = 'Q' * samples_to_write
                offsets = range(0, total_smartcache_metadata_bytes, sample_smartcache_metadata_bytes)

                offsets = offsets[:samples_to_write]
                binary_offsets = struct.pack(myfmt, *offsets)
                off_file.write(binary_offsets)

                # Write sizes
                myfmt = 'Q' * samples_to_write
                sample_sizes = [sample_size] * samples_to_write
                binary_sizes = struct.pack(myfmt, *sample_sizes)
                sz_file.write(binary_sizes)
                self.logger.debug(f"writing file {data_file.name} with size {write_size} offsets to write: {offsets}, sizes to write: {sample_sizes}")

                written_bytes = written_bytes + data_to_write
            data_file.close()
            off_file.close()
            sz_file.close()
        np.random.seed()
        DLIOMPI.get_instance().comm().Barrier()

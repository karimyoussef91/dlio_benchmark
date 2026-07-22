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

import math
import logging
import numpy as np

from dlio_benchmark.common.enumerations import DataLoaderSampler, DatasetType, DataLoaderType, FormatType, ReadType, Shuffle, StorageType
from dlio_benchmark.data_loader.torch_data_loader import TorchDataLoader
from dlio_benchmark.reader.reader_handler import FormatReader
from dlio_benchmark.utils.config import ConfigArguments
from dlio_benchmark.utils.utility import DLIOMPI


class RecordingIndexReader(FormatReader):
    observed_orders = {}
    expected_samples = 0

    def __init__(self, dataset_type, thread_index, epoch_number):
        self.epoch_number = epoch_number
        super().__init__(dataset_type, thread_index)

    def open(self, filename):
        return filename

    def close(self, filename):
        return None

    def get_sample(self, filename, sample_index):
        return None

    def next(self):
        raise NotImplementedError()

    def read_index(self, global_sample_idx, step):
        sample = super().read_index(global_sample_idx, step)
        filename, _ = self.global_index_map[global_sample_idx]
        observed_sample = int(filename.split("_")[-1])
        epoch_order = self.observed_orders.setdefault(self.epoch_number, [])
        if len(epoch_order) < self.expected_samples:
            epoch_order.append(observed_sample)
        return sample

    def finalize(self):
        return None

    def is_index_based(self):
        return True

    def is_iterator_based(self):
        return False


def _configure_common_args(total_samples, comm_size):
    args = ConfigArguments.get_instance()
    args.logger = logging.getLogger("dlio-test")
    args.my_rank = 0
    args.comm_size = comm_size
    args.num_samples_per_file = 1
    args.sample_shuffle = Shuffle.SEED
    args.seed = 42
    args.seed_change_epoch = True
    args.data_loader_sampler = DataLoaderSampler.INDEX
    args.data_loader = DataLoaderType.PYTORCH
    args.storage_type = StorageType.LOCAL_FS
    args.read_type = ReadType.ON_DEMAND
    args.read_threads = 0
    args.prefetch_size = 2
    args.pin_memory = False
    args.batch_size = 2
    args.batch_size_eval = 2
    args.epochs = 2
    args.total_samples_train = total_samples
    args.total_samples_eval = total_samples
    args.training_steps = int(math.ceil(total_samples / args.batch_size / comm_size))
    args.eval_steps = args.training_steps
    args.resized_image = np.zeros((1,), dtype=np.uint8)
    args.file_list_train = [f"file_{sample_idx}" for sample_idx in range(total_samples)]
    args.file_list_eval = list(args.file_list_train)
    args.train_file_map = {args.my_rank: {}}
    args.val_file_map = {args.my_rank: {}}
    args.train_global_index_map = {}
    args.val_global_index_map = {}
    args.train_sample_index_sum = total_samples * (total_samples - 1) // 2
    args.eval_sample_index_sum = args.train_sample_index_sum
    args.reader_class = RecordingIndexReader
    RecordingIndexReader.expected_samples = total_samples
    return args


def _build_rank_epoch_order(rank, comm_size, total_samples, epoch_number):
    args = ConfigArguments.get_instance()
    args.my_rank = rank
    args.comm_size = comm_size
    args.num_samples_per_file = 1
    args.sample_shuffle = Shuffle.SEED
    args.seed = 42
    args.seed_change_epoch = True
    args.data_loader_sampler = DataLoaderSampler.INDEX

    file_list = [f"file_{sample_idx}" for sample_idx in range(total_samples)]
    global_index_map, sample_sum = args.get_global_map_index(file_list, total_samples, epoch_number)
    samples_per_proc = int(math.ceil(total_samples / comm_size))
    shard_keys = range(rank * samples_per_proc, min((rank + 1) * samples_per_proc, total_samples))
    order = [int(global_index_map[shard_key][0].split("_")[-1]) for shard_key in shard_keys]
    return order, sample_sum


def test_global_shuffle_changes_between_epochs_and_preserves_coverage():
    DLIOMPI.get_instance().initialize()
    ConfigArguments.reset()
    _configure_common_args(total_samples=8, comm_size=2)

    total_samples = 8
    comm_size = 2

    epoch0_orders = []
    epoch1_orders = []
    epoch0_sum = 0
    epoch1_sum = 0

    for rank in range(comm_size):
        order, sample_sum = _build_rank_epoch_order(rank, comm_size, total_samples, epoch_number=0)
        epoch0_orders.append(order)
        epoch0_sum += sample_sum

    for rank in range(comm_size):
        order, sample_sum = _build_rank_epoch_order(rank, comm_size, total_samples, epoch_number=1)
        epoch1_orders.append(order)
        epoch1_sum += sample_sum

    assert sorted(epoch0_orders[0] + epoch0_orders[1]) == list(range(total_samples))
    assert sorted(epoch1_orders[0] + epoch1_orders[1]) == list(range(total_samples))
    assert epoch0_orders != epoch1_orders
    assert epoch0_sum == total_samples * (total_samples - 1) // 2
    assert epoch1_sum == total_samples * (total_samples - 1) // 2


def test_torch_dataloader_uses_epoch_shuffled_global_index_map():
    DLIOMPI.get_instance().initialize()
    ConfigArguments.reset()
    args = _configure_common_args(total_samples=8, comm_size=1)
    RecordingIndexReader.observed_orders = {}

    args.reconfigure(0)
    loader = TorchDataLoader(FormatType.NPY, DatasetType.TRAIN, epoch_number=0)
    loader.read()
    assert id(loader._args) == id(args)
    assert id(loader._dataset.dataset.global_index_map) == id(args.train_global_index_map)
    epoch0_map = tuple(
        int(path.split("_")[-1])
        for _, (path, _) in sorted(loader._dataset.dataset.global_index_map.items())
    )
    list(loader.next())

    args.reconfigure(1)
    loader = TorchDataLoader(FormatType.NPY, DatasetType.TRAIN, epoch_number=1)
    loader.read()
    assert id(loader._args) == id(args)
    assert id(loader._dataset.dataset.global_index_map) == id(args.train_global_index_map)
    epoch1_map = tuple(
        int(path.split("_")[-1])
        for _, (path, _) in sorted(loader._dataset.dataset.global_index_map.items())
    )
    list(loader.next())

    epoch0_order = RecordingIndexReader.observed_orders[0]
    epoch1_order = RecordingIndexReader.observed_orders[1]

    assert epoch0_map != epoch1_map
    assert sorted(epoch0_order) == list(range(args.total_samples_train))
    assert sorted(epoch1_order) == list(range(args.total_samples_train))
    assert epoch0_order != epoch1_order
import os
from pathlib import Path

import h5py
import numpy as np

from .util import np_equal


class Snapshot(object):
    HEADER_FIELDS_HETERO = [
        'NumPart_ThisFile'
    ]

    def __init__(self, prefix, suffix='.hdf5'):
        # Determine snapshot paths
        pre_path = Path(prefix).expanduser().resolve()
        if pre_path.is_dir():
            self.dir = pre_path
            glob_pattern = '*' + suffix
        else:
            self.dir = pre_path.parent
            glob_pattern = pre_path.name + '*' + suffix
        self.paths = [path for path in sorted(self.dir.glob(glob_pattern))]
        self.name = os.path.commonprefix(
            [path.stem for path in self.paths]).rstrip('.')

        # There must be at least one path
        assert len(self.paths) > 0

        # Read header
        self.header = self._read_header()

        # Initialize field cache
        self._field_cache = {}

    def _read_header(self):
        # Read header from the first file
        with h5py.File(self.paths[0]) as h5f:
            hdr = dict(h5f['Header'].attrs)

        # Check the number of files
        assert hdr['NumFilesPerSnapshot'] == len(self.paths)

        # Prepare to collect heterogeneous header fields
        for key in self.HEADER_FIELDS_HETERO:
            hdr[key] = [hdr[key]]

        # Check header with the rest files
        for path in self.paths[1:]:
            with h5py.File(path) as h5f:
                hdr_this = dict(h5f['Header'].attrs)
                assert set(hdr_this.keys()) == set(hdr.keys())
                for key in hdr_this.keys():
                    if key in self.HEADER_FIELDS_HETERO:
                        # Collect heterogeneous fields
                        hdr[key] += [hdr_this[key]]
                    else:
                        # Verify homogeneous fields
                        assert np_equal(hdr[key], hdr_this[key])

        # NumPart_ThisFile should add up to NumPart_Total
        assert np_equal(hdr['NumPart_Total'],
                        np.sum(hdr['NumPart_ThisFile'], axis=0))

        return hdr

    def __getitem__(self, key):
        # Read from file if field cache doesn't exist
        if key not in self._field_cache:
            data = []
            for path in self.paths:
                with h5py.File(path) as h5f:
                    data += [h5f['/'.join(key)][()]]
            data = np.concatenate(data)
            self._field_cache[key] = data

        return self._field_cache[key]

    def __delitem__(self, key):
        # Delete cache
        del self._field_cache[key]

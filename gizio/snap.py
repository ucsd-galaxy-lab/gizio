import os
from pathlib import Path

import h5py
import numpy as np
import unyt

from .unit import create_unit_registry
from .util import np_equal


class Snapshot(object):
    HEADER_FIELDS_HETERO = [
        'NumPart_ThisFile'
    ]

    def __init__(self, prefix, suffix='.hdf5', cosmological=None):
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

        # Determine whether this snapshot is cosmological or not
        if cosmological is None:
            # Guess if not specified
            a = self.header['Time']
            z = self.header['Redshift']
            if np.isclose(a, 1 / (1 + z)):
                cosmological = True;
            else:
                cosmological = False;
        self.cosmological = cosmological

        # Create unit registry
        h = float(self.header['HubbleParam'])
        if self.cosmological:
            a = float(self.header['Time'])
        else:
            a = 1.0
        self.unit_registry = create_unit_registry(a=a, h=h)

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

    def array(self, value, unit):
        return unyt.unyt_array(value, unit, registry=self.unit_registry)

    def quantity(self, value, unit):
        return unyt.unyt_quantity(value, unit, registry=self.unit_registry)

    def __getitem__(self, key):
        # Read from file if cache doesn't exist
        if key not in self._field_cache:
            data = []
            for path in self.paths:
                with h5py.File(path) as h5f:
                    data += [h5f['/'.join(key)][()]]
            data = np.concatenate(data)
            unit = self._get_field_unit(key[1])
            self._field_cache[key] = self.array(data, unit)

        return self._field_cache[key]

    def __delitem__(self, key):
        # Delete cache
        del self._field_cache[key]

    def _get_field_unit(self, field):
        from .unit import KNOWN_GIZMO_FIELD_UNITS
        if field in KNOWN_GIZMO_FIELD_UNITS:
            return KNOWN_GIZMO_FIELD_UNITS[field]
        else:
            return 'dimensionless'

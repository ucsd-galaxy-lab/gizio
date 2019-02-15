import json
import os
from pathlib import Path
from pkg_resources import resource_string

import h5py
import numpy as np
import unyt


class Snapshot(object):
    def __init__(self, prefix, suffix='.hdf5', cosmological=None, spec='gizmo'):
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

        # Load spec
        if os.path.isfile(spec):
            with open(spec, 'r') as f:
                spec = f.read()
        else:
            spec = resource_string(__name__, f'spec/h5/{spec}.json')
        self.spec = json.loads(spec)

        # Load header from the first file
        with h5py.File(self.paths[0], 'r') as h5f:
            self.header = dict(h5f[self.spec['header']['group']].attrs)

        # Load core header fields
        def load_core(key):
            return self.header[self.spec['header']['core'][key]]
        a = float(load_core('time'))
        z = float(load_core('redshift'))
        h = float(load_core('hubble'))

        # Determine whether this snapshot is cosmological or not
        if cosmological is None:
            # Guess if not specified
            if np.isclose(a, 1 / (1 + z)):
                cosmological = True;
            else:
                cosmological = False;
        self.cosmological = cosmological

        # Create unit registry
        if not self.cosmological:
            a = 1.0
        unit_system = self.spec['unit_system']
        self.unit_registry = create_unit_registry(
            a=a, h=h,
            solar_abundance=unit_system['SolarAbundance'],
            unit_length_cgs=unit_system['UnitLength_in_cm'],
            unit_mass_cgs=unit_system['UnitMass_in_g'],
            unit_velocity_cgs=unit_system['UnitVelocity_in_cm_per_s'],
            unit_magnetic_field_cgs=unit_system['UnitMagneticField_in_gauss'],
        )

        # Configure fields
        field_abbrs = {}
        field_units = {}
        for abbr, name, unit in self.spec['fields']:
            field_abbrs[abbr] = name
            field_units[name] = unit
        self._field_abbrs = field_abbrs
        self._field_units = field_units
        self._field_cache = {}

        # Set up particle type accessors
        self.pt = [
            ParticleTypeAccessor(self, ptype)
            for ptype in self.spec['particle_types']
        ]

    def array(self, value, unit):
        return unyt.unyt_array(value, unit, registry=self.unit_registry)

    def quantity(self, value, unit):
        return unyt.unyt_quantity(value, unit, registry=self.unit_registry)

    def __getitem__(self, key):
        # Read from file if cache doesn't exist
        if key not in self._field_cache:
            data = []
            for path in self.paths:
                with h5py.File(path, 'r') as h5f:
                    data += [h5f['/'.join(key)][()]]
            data = np.concatenate(data)
            unit = self._get_field_unit(key[1])
            self._field_cache[key] = self.array(data, unit)

        return self._field_cache[key]

    def __delitem__(self, key):
        # Delete cache
        del self._field_cache[key]

    def _get_field_unit(self, field_name):
        if field_name in self._field_units:
            return self._field_units[field_name]
        else:
            return 'dimensionless'


class ParticleTypeAccessor(object):
    def __init__(self, snap, ptype):
        self._snap = snap
        self._ptype = ptype

    def __getitem__(self, key):
        return self._snap[self._ptype, key]

    def __delitem__(self, key):
        del self._snap[self._ptype, key]

    def __getattr__(self, abbr):
        return self[self._snap._field_abbrs[abbr]]

    def __delattr__(self, alias):
        del self[self._snap._field_abbrs[abbr]]


# Reference:
# http://www.tapir.caltech.edu/~phopkins/Site/GIZMO_files/gizmo_documentation.html#snaps-units
def create_unit_registry(
        a=1.0, h=0.7, solar_abundance=0.02,
        unit_length_cgs=3.085678e21,
        unit_mass_cgs=1.989e43,
        unit_velocity_cgs=1e5,
        unit_magnetic_field_cgs=1.0,
    ):
    reg = unyt.UnitRegistry()

    def def_unit(symbol, value):
        value = unyt.unyt_quantity(*value, registry=reg)
        base_value = float(value.in_base(unit_system='mks'))
        dimensions = value.units.dimensions
        reg.add(symbol, base_value, dimensions)

    def_unit('a', (a, ''))
    def_unit('h', (h, ''))
    def_unit('code_metallicity', (solar_abundance, ''))

    def_unit('code_length', (unit_length_cgs / h * a, 'cm'))
    def_unit('code_mass', (unit_mass_cgs / h, 'g'))
    def_unit('code_velocity', (unit_velocity_cgs * np.sqrt(a), 'cm / s'))
    def_unit('code_magnetic_field', (unit_magnetic_field_cgs, 'gauss'))

    def_unit('code_specific_energy', (unit_velocity_cgs**2, '(cm / s)**2'))
    def_unit('code_time', (1, 'code_length / code_velocity'))

    return reg

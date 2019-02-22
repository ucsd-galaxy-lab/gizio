"""Objects representing simulation snapshot."""
import json
import os
from pathlib import Path
from pkg_resources import resource_string

from astropy.cosmology import LambdaCDM
import h5py
import numpy as np
import unyt

from .field.shop import add_default_derived_fields
from .field.system import ParticleSelector
from .unit import create_unit_registry


class Snapshot:
    """Simulation snapshot."""
    def __init__(self, prefix, suffix='.hdf5', spec='gizmo'):
        # Determine snapshot paths
        prefix = Path(prefix).expanduser().resolve()
        if prefix.is_dir():
            # Directory case
            self.dir = prefix
            glob_pattern = '*' + suffix
        else:
            self.dir = prefix.parent
            # Single file case
            glob_pattern = prefix.name
            if not prefix.is_file():
                # Glob prefix case
                glob_pattern += ('*' + suffix)
        self.paths = [path for path in sorted(self.dir.glob(glob_pattern))]
        stems = [path.stem for path in self.paths]
        self.name = os.path.commonprefix(stems).rstrip('.')
        # Check paths are not empty
        assert self.paths

        # Load specification
        self.spec = Specification(spec)

        # Load header
        self.header = Header(self, self.spec.header)

        # Set up unit system
        unit_system = self.spec.unit_system
        self.unit_registry = create_unit_registry(
            a=self.header.a, h=self.header.h,
            solar_abundance=unit_system['SolarAbundance'],
            unit_length_cgs=unit_system['UnitLength_in_cm'],
            unit_mass_cgs=unit_system['UnitMass_in_g'],
            unit_velocity_cgs=unit_system['UnitVelocity_in_cm_per_s'],
            unit_magnetic_field_cgs=unit_system['UnitMagneticField_in_gauss'],
        )
        self.header.attach_units(self.unit_registry)

        # Detect available keys
        self.keys = []
        with h5py.File(self.paths[0], 'r') as h5f:
            for ptype in self.spec.ptypes:
                if ptype in h5f:
                    for field in h5f[ptype].keys():
                        self.keys += [(ptype, field)]
        # Record detected ptypes in spec order
        ptypes = set(ptype for ptype, _ in self.keys)
        self.ptypes = [ptype for ptype in self.spec.ptypes if ptype in ptypes]
        # Record detected fields in alphabetic order
        fields = set(field for _, field in self.keys)
        self.fields = sorted(fields)

        # Set up particle type accessor
        self.pt = ParticleTypeAccessor(self)

        # Initialize cache
        self.clear_cache()

    def is_cosmological(self):
        """Whether this snapshot is cosmological."""
        return self.header.cosmo is not None

    def array(self, value, unit):
        """Create an array with simulation unit registry."""
        return unyt.unyt_array(value, unit, registry=self.unit_registry)

    def quantity(self, value, unit):
        """Create a quantity with simulation unit registry."""
        return unyt.unyt_quantity(value, unit, registry=self.unit_registry)

    def __getitem__(self, key):
        # Load from file if cache doesn't exist
        if key not in self._cache:
            # Load value
            value = []
            for path in self.paths:
                with h5py.File(path, 'r') as h5f:
                    value += [h5f['/'.join(key)][()]]
            value = np.concatenate(value)
            # Determine unit
            _, field = key
            if field in self.spec.field_units:
                unit = self.spec.field_units[field]
            else:
                unit = 'dimensionless'
            # Cache
            self._cache[key] = self.array(value, unit)
        # Retrieve cache
        return self._cache[key]

    def __delitem__(self, key):
        # Delete cache
        del self._cache[key]

    def clear_cache(self):
        """Clear data cache."""
        self._cache = {}


class Header:
    """Snapshot header."""
    def __init__(self, snap, spec):
        # Load raw headers
        raw = []
        for path in snap.paths:
            with h5py.File(path, 'r') as h5f:
                raw += [dict(h5f[spec['group']].attrs)]
        self.raw = raw

        def get(key, i=0):
            return raw[i][spec['mapping'][key]]

        # File and particle
        self.n_file = get('n_file')
        self.n_part = [get('n_part', i) for i in range(self.n_file)]
        self.n_part_tot = get('n_part_tot')

        # Time and cosmology
        self.a = get('time')
        self.z = get('redshift')
        self.h = get('hubble')
        if np.isclose(self.a, 1 / (1 + self.z)):
            self.cosmo = LambdaCDM(self.h * 100, get('Om0'), get('OmL'))
            self.time = self.cosmo.age(self.z).to_value('Gyr')
        else:
            self.cosmo = None
            self.time = self.a / self.h  # in Gyr
            self.a = 1.0

        # Flags
        self.flag = {}
        prefix = spec['flag_prefix']
        for key in raw[0].keys():
            if key.startswith(prefix):
                k = key[len(prefix):]
                self.flag[k] = raw[0][key]

        # Other quantities
        self.box_size = get('box_size')
        self.mass_tab = get('mass_tab')

    def attach_units(self, reg):
        """Attach proper units to attributes."""
        def attach(attr, unit):
            value = getattr(self, attr)
            if not hasattr(value, 'units'):
                setattr(self, attr, value * unyt.Unit(unit, registry=reg))
        attach('time', 'Gyr')
        attach('box_size', 'code_length')
        attach('mass_tab', 'code_mass')


class ParticleTypeAccessor:
    """Accessor for individual particle types."""
    def __init__(self, snap):
        self._snap = snap

        def init_ps(ptypes):
            ps = ParticleSelector.from_ptype(snap, ptypes)
            add_default_derived_fields(ps)
            return ps

        for pa, ptype in snap.spec.ptype_alias.items():
            if ptype in snap.ptypes:
                setattr(self, pa, init_ps([ptype]))
        self.all = init_ps(snap.ptypes)

    def __getitem__(self, key):
        pa = list(self._snap.ptypes_alias.keys())[key]
        return getattr(self, pa)


class Specification:
    """Snapshot format specification."""
    def __init__(self, spec):
        # Load spec
        if os.path.isfile(spec):
            # Load from user file
            with open(spec, 'r') as f:
                spec = f.read()
        else:
            # Load from builtin file
            spec = resource_string(__name__, f'spec/h5/{spec}.json')
        # Parse JSON string
        spec = json.loads(spec)

        # Header and unit system
        self.header = spec['header']
        self.unit_system = spec['unit_system']

        # Particle types
        self.ptypes = []
        self.ptype_alias = {}
        for ptype, pa in spec['particle_types']:
            self.ptypes += [ptype]
            self.ptype_alias[pa] = ptype

        # Fields
        self.fields = []
        self.field_alias = {}
        self.field_units = {}
        for field, fa, unit in spec['fields']:
            self.fields += [field]
            self.field_alias[fa] = field
            self.field_units[field] = unit

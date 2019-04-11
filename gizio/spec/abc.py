import abc
from collections import OrderedDict

import h5py
import numpy as np
import unyt


class Specification(abc.ABC):
    """Snapshot format specification."""

    HEADER_BLOCK = None
    HEADER_N_PART = None
    HEADER_PER_FILE = None
    HEADER_SPEC = None
    UNIT_SPEC = None
    PTYPE_SPEC = None
    FIELD_SPEC = None

    def __init__(self):
        # Parse ptype spec
        self.ptypes = []
        self.ptype_abbrs = {}
        for raw, abbr in self.PTYPE_SPEC:
            self.ptypes += [raw]
            self.ptype_abbrs[raw] = abbr

        # Parse field spec
        self.fields = []
        self.field_abbrs = {}
        self.field_units = {}
        for raw, abbr, unit in self.FIELD_SPEC:
            self.fields += [raw]
            self.field_abbrs[raw] = abbr
            self.field_units[raw] = unit

    def apply_to(self, snap):
        header = self.read_header(snap)
        shape = self.get_shape(header)
        a, h, cosmology = self.get_cosmology(header)
        unit_registry = self.create_unit_registry(a, h)
        self.add_header_units(header, unit_registry)
        return header, shape, cosmology, unit_registry

    def read_header(self, snap):
        headers = []
        for path in snap.paths:
            with h5py.File(path, "r") as f:
                headers += [dict(f[self.HEADER_BLOCK].attrs)]

        header = {}
        for key, alias in self.HEADER_SPEC:
            if key in self.HEADER_PER_FILE:
                header[alias] = [h[key] for h in headers]
            else:
                header[alias] = headers[0][key]
        return header

    def get_shape(self, header):
        return OrderedDict(zip(self.ptypes, header[self.HEADER_N_PART]))

    # Reference:
    # http://www.tapir.caltech.edu/~phopkins/Site/GIZMO_files/gizmo_documentation.html#snaps-units
    def create_unit_registry(self, a, h):
        """Create a unit registry from unit system constants."""
        solar_abundance = self.UNIT_SPEC["SolarAbundance"]
        unit_length_cgs = self.UNIT_SPEC["UnitLength_in_cm"]
        unit_mass_cgs = self.UNIT_SPEC["UnitMass_in_g"]
        unit_velocity_cgs = self.UNIT_SPEC["UnitVelocity_in_cm_per_s"]
        unit_magnetic_field_cgs = self.UNIT_SPEC["UnitMagneticField_in_gauss"]
        reg = unyt.UnitRegistry()

        def def_unit(symbol, value):
            value = unyt.unyt_quantity(*value, registry=reg)
            base_value = float(value.in_base(unit_system="mks"))
            dimensions = value.units.dimensions
            reg.add(symbol, base_value, dimensions)

        def_unit("a", (a, ""))
        def_unit("h", (h, ""))
        def_unit("code_metallicity", (solar_abundance, ""))

        def_unit("code_length", (unit_length_cgs / h * a, "cm"))
        def_unit("code_mass", (unit_mass_cgs / h, "g"))
        def_unit("code_velocity", (unit_velocity_cgs * np.sqrt(a), "cm / s"))
        def_unit("code_magnetic_field", (unit_magnetic_field_cgs, "gauss"))

        def_unit(
            "code_specific_energy", (unit_velocity_cgs ** 2, "(cm / s)**2")
        )
        def_unit("code_time", (1, "code_length / code_velocity"))

        return reg

    @abc.abstractmethod
    def get_cosmology(self, header):
        pass

    @abc.abstractmethod
    def add_header_units(self, header, unit_registry):
        pass

    @abc.abstractmethod
    def register_derived_fields(self, field_system, ptype):
        pass

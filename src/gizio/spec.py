"""Snapshot format specification."""
import abc
from collections import OrderedDict

from astropy.cosmology import LambdaCDM
import h5py
import numpy as np
import unyt


SPEC_REGISTRY = {}


class SpecBase(abc.ABC):
    """Snapshot format specification base class."""

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
        """Apply specification to snapshot.

        Parameters
        ----------
        snap : Snapshot
            The snapshot to apply to.

        Returns
        -------
        header : dict
            Snapshot header.
        shape : collections.OrderedDict
            Data shape composed of {ptype_name: n_part} entries, in the
            specification ptypes order.
        cosmology : astropy.cosmology.LambdaCDM
            An astropy cosmology calculator.
        unit_registry : unyt.unit_registry.UnitRegistry
            Simulation unit registry.

        """
        header = self._read_header(snap)
        shape = self._get_shape(header)
        a, h, cosmology = self._get_cosmology(header)
        unit_registry = self._create_unit_registry(a, h)
        self._add_header_units(header, unit_registry)
        return header, shape, cosmology, unit_registry

    def _read_header(self, snap):
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

    def _get_shape(self, header):
        return OrderedDict(zip(self.ptypes, header[self.HEADER_N_PART]))

    # Reference:
    # http://www.tapir.caltech.edu/~phopkins/Site/GIZMO_files/gizmo_documentation.html#snaps-units
    def _create_unit_registry(self, a, h):
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
    def _get_cosmology(self, header):
        pass

    @abc.abstractmethod
    def _add_header_units(self, header, unit_registry):
        pass

    @abc.abstractmethod
    def register_derived_fields(self, ps, ptype):
        """Register default derived fields to a field system.

        Parameters
        ----------
        ps : ParticleSelector
            The particle selector to register fields to.
        ptype : str
            The particle type to register fields with.

        """


class GIZMOSpec(SpecBase):
    """GIZMO snapshot format specification."""

    HEADER_BLOCK = "Header"
    HEADER_N_PART = "n_part"
    HEADER_PER_FILE = ["NumPart_ThisFile"]
    HEADER_SPEC = [
        # (name, key)
        ("Time", "time"),
        ("NumFilesPerSnapshot", "n_file"),
        ("MassTable", "mass_tab"),
        ("Flag_Sfr", "f_sfr"),
        ("Flag_Cooling", "f_cool"),
        ("Flag_Feedback", "f_fb"),
        ("Flag_StellarAge", "f_age"),
        ("Flag_Metals", "f_met"),
        ("NumPart_Total", "n_part"),
        ("NumPart_ThisFile", "n_part_pf"),
        ("BoxSize", "box_size"),
        ("Omega0", "Om0"),
        ("OmegaLambda", "OmL"),
        ("HubbleParam", "h"),
        ("Redshift", "z"),
    ]
    UNIT_SPEC = {
        "SolarAbundance": 0.02,
        "UnitLength_in_cm": 3.085678e21,
        "UnitMass_in_g": 1.989e43,
        "UnitVelocity_in_cm_per_s": 1e5,
        "UnitMagneticField_in_gauss": 1.0,
    }
    PTYPE_SPEC = [
        # (name, key)
        ("PartType0", "gas"),
        ("PartType1", "hdm"),
        ("PartType2", "ldm"),
        ("PartType3", "dum"),
        ("PartType4", "star"),
        ("PartType5", "bh"),
    ]
    FIELD_SPEC = [
        # (name, key, unit)
        ("Coordinates", "p", "code_length"),
        ("Velocities", "v", "code_velocity"),
        ("ParticleIDs", "id", ""),
        ("Masses", "m", "code_mass"),
        ("InternalEnergy", "u", "code_specific_energy"),
        ("Density", "rho", "code_mass / code_length**3"),
        ("SmoothingLength", "h", "code_length"),
        ("ElectronAbundance", "ne", ""),
        ("NeutralHydrogenAbundance", "nh", ""),
        ("StarFormationRate", "sfr", "Msun / yr"),
        ("Metallicity", "z", "code_metallicity"),
        ("ArtificialViscosity", "alpha", ""),
        ("MagneticField", "b", "code_magnetic_field"),
        (
            "DivergenceOfMagneticField",
            "divb",
            "code_magnetic_field / code_length",
        ),
        ("StellarFormationTime", "sft", ""),
        ("BH_Mass", "mbh", "code_mass"),
        ("BH_Mdot", "mdot", "code_mass / code_time"),
        ("BH_Mass_AlphaDisk", "mad", "code_mass"),
    ]

    def _get_cosmology(self, header):
        h = header["h"]
        cosmology = LambdaCDM(h * 100, header["Om0"], header["OmL"])

        a = header["time"]
        z = header["z"]
        if np.isclose(a, 1 / (1 + z)):
            # cosmological case
            header["time"] = cosmology.age(z).to_value("Gyr")
            header["cosmological"] = True
        else:
            # non-cosmological case
            header["time"] = a / h  # in Gyr
            header["a"] = 1.0
            header["z"] = 0.0
            header["cosmological"] = False

        return a, h, cosmology

    def _add_header_units(self, header, unit_registry):
        def attach_unit(key, unit):
            header[key] *= unyt.Unit(unit, registry=unit_registry)

        attach_unit("time", "Gyr")
        attach_unit("box_size", "code_length")
        attach_unit("mass_tab", "code_mass")

    def register_derived_fields(self, ps, ptype):
        """Register default derived fields to a field system.

        Parameters
        ----------
        ps : ParticleSelector
            The particle selector to register fields to.
        ptype : str
            The particle type to register fields with.

        """
        if ptype == "gas":
            ps.register_field("t", self.compute_temperature)
        if ptype == "star":
            ps.register_field("age", self.compute_age)

    @staticmethod
    def compute_age(ps):
        """Compute age from formation time.

        Parameters
        ----------
        ps : ParticleSelector
            A particle selector.

        Returns
        -------
        unyt.unyt_array
            The age array.

        """
        # See the note following StellarFormationTime on this page:
        # http://www.tapir.caltech.edu/~phopkins/Site/GIZMO_files/gizmo_documentation.html#snaps-reading
        sft = ps["sft"].d

        snap = ps.snap
        if snap.header["cosmological"]:
            a_form = sft
            z_form = 1 / a_form - 1
            t_form = snap.cosmology.age(z_form).to_value("Gyr")
            t_form = snap.array(t_form, "Gyr")
        else:
            t_form = snap.array(sft, "code_time")
        age = snap.header["time"] - t_form
        return age.to("Gyr")

    @staticmethod
    def compute_temperature(ps):
        """Compute temperature from internal energy.

        Parameters
        ----------
        ps : ParticleSelector
            A particle selector.

        Returns
        -------
        unyt.unyt_array
            The temperature array.

        """
        # See the note following InternalEnergy on this page:
        # http://www.tapir.caltech.edu/~phopkins/Site/GIZMO_files/gizmo_documentation.html#snaps-reading
        ne = ps["ne"]
        u = ps["u"]
        z_he = ps["z"][:, 1]

        from unyt.physical_constants import kb, mp

        gamma = 5 / 3

        y = z_he / (4 * (1 - z_he))
        mu = (1 + 4 * y) / (1 + y + ne)
        temperature = mu * mp * (gamma - 1) * u / kb
        return temperature.to("K")


SPEC_REGISTRY["gizmo"] = GIZMOSpec

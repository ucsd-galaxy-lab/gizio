"""GIZMO specification."""
from astropy.cosmology import LambdaCDM
import numpy as np
import unyt

from .abc import Specification


class GIZMOSpecification(Specification):
    """GIZMO snapshot format specification."""

    HEADER_BLOCK = "Header"
    HEADER_N_PART = "n_part"
    HEADER_PER_FILE = ["NumPart_ThisFile"]
    HEADER_SPEC = [
        # (raw, abbr)
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
        # (raw, abbr)
        ("PartType0", "gas"),
        ("PartType1", "hdm"),
        ("PartType2", "ldm"),
        ("PartType3", "dum"),
        ("PartType4", "star"),
        ("PartType5", "bh"),
    ]
    FIELD_SPEC = [
        # (raw, abbr, unit)
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

    def register_derived_fields(self, field_system, ptype):
        """Register default derived fields to a field system."""
        if ptype == "gas":
            field_system.register("t", compute_temperature)
        if ptype == "star":
            field_system.register("age", compute_age)


def compute_age(field_system):
    """Compute age from formation time."""
    # See the note following StellarFormationTime on this page:
    # http://www.tapir.caltech.edu/~phopkins/Site/GIZMO_files/gizmo_documentation.html#snaps-reading
    sft = field_system["sft"].d

    snap = field_system.snap
    if snap.header["cosmological"]:
        a_form = sft
        z_form = 1 / a_form - 1
        t_form = snap.cosmology.age(z_form).to_value("Gyr")
        t_form = snap.array(t_form, "Gyr")
    else:
        t_form = snap.array(sft, "code_time")
    age = snap.header["time"] - t_form
    return age.to("Gyr")


def compute_temperature(field_system):
    """Compute temperature from internal energy."""
    # See the note following InternalEnergy on this page:
    # http://www.tapir.caltech.edu/~phopkins/Site/GIZMO_files/gizmo_documentation.html#snaps-reading
    ne = field_system["ne"]
    u = field_system["u"]
    z_he = field_system["z"][:, 1]

    from unyt.physical_constants import kb, mp

    gamma = 5 / 3

    y = z_he / (4 * (1 - z_he))
    mu = (1 + 4 * y) / (1 + y + ne)
    temperature = mu * mp * (gamma - 1) * u / kb
    return temperature.to("K")

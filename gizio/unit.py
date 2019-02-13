from functools import partial

import numpy as np
import unyt


KNOWN_GIZMO_FIELD_UNITS = {
    'Coordinates': 'code_length',
    'Velocities': 'code_velocity',
    'ParticleIDs': '',
    'Masses': 'code_mass',
    'InternalEnergy': 'code_specific_energy',
    'Density': 'code_mass / code_length**3',
    'SmoothingLength': 'code_length',
    'ElectronAbundance': '',
    'NeutralHydrogenAbundance': '',
    'StarFormationRate': 'Msun / yr',
    'Metallicity': 'code_metallicity',
    'ArtificialViscosity': '',
    'MagneticField': 'code_magnetic_field',
    'DivergenceOfMagneticField': 'code_magnetic_field / code_length',
    'StellarFormationTime': '',
    'BH_Mass': 'code_mass',
    'BH_Mdot': 'code_mass / code_time',
    'BH_Mass_AlphaDisk': 'code_mass'
}


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

"""Field shop."""
from functools import partial


def add_default_derived_fields(fs):
    """Add default derived fields to a field system."""
    fs.derived_fields['age'] = partial(
        age, cosmological=fs.snap.is_cosmological()
    )
    fs.derived_fields['t'] = temperature


def age(fs, f_sft='sft', cosmological=True):
    """Calculate age from formation time."""
    # See the note following StellarFormationTime on this page:
    # http://www.tapir.caltech.edu/~phopkins/Site/GIZMO_files/gizmo_documentation.html#snaps-reading
    sft = fs[f_sft].d
    snap = fs.snap
    if cosmological:
        a_form = sft
        z_form = 1 / a_form - 1
        t_form = snap.header.cosmo.age(z_form).to_value('Gyr')
        t_form = snap.array(t_form, 'Gyr')
    else:
        t_form = snap.array(sft, 'code_time')
    _age = snap.header.time - t_form
    return _age.to('Gyr')


def temperature(fs, f_ne='ne', f_u='u', f_z='z', i_he=1):
    """Calculate temperature from internal energy."""
    # See the note following InternalEnergy on this page:
    # http://www.tapir.caltech.edu/~phopkins/Site/GIZMO_files/gizmo_documentation.html#snaps-reading
    ne = fs[f_ne]
    u = fs[f_u]
    z_he = fs[f_z][:, i_he]

    from unyt.physical_constants import kb, mp
    gamma = 5 / 3

    y = z_he / (4 * (1 - z_he))
    mu = (1 + 4 * y) / (1 + y + ne)
    temp = mu * mp * (gamma - 1) * u / kb
    return temp.to('K')

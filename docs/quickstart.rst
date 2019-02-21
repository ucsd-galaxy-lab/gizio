Quickstart
==========

First, :doc:`install gizio <installation>` and download the `sample data <http://yt-project.org/data/FIRE_M12i_ref11.tar.gz>`_ kindly provided by `yt <http://yt-project.org>`_.

Snapshot examination
--------------------

Load a snapshot::

    >>> import gizio
    >>> snap = gizio.Snapshot('FIRE_M12i_ref11/snapshot_600.hdf5')

Examine the raw header, which is loaded as a dictionary::

    >>> snap.header.raw[0]
    {'BoxSize': 60000.0,
     'Flag_Cooling': 1,
     'Flag_DoublePrecision': 0,
     'Flag_Feedback': 1,
     'Flag_IC_Info': 3,
     'Flag_Metals': 11,
     'Flag_Sfr': 1,
     'Flag_StellarAge': 1,
     'HubbleParam': 0.702,
     'MassTable': array([0., 0., 0., 0., 0., 0.]),
     'NumFilesPerSnapshot': 1,
     'NumPart_ThisFile': array([ 753678, 1104128, 2567905,       0,  361239,       0], dtype=int32),
     'NumPart_Total': array([ 753678, 1104128, 2567905,       0,  361239,       0], dtype=uint32),
     'NumPart_Total_HighWord': array([0, 0, 0, 0, 0, 0], dtype=uint32),
     'Omega0': 0.272,
     'OmegaLambda': 0.728,
     'Redshift': 0.0,
     'Time': 1.0}

Actually ``header.raw`` is a list of header dictionaries, which is useful when the snapshot is composed of multiple files.

Several preconfigured header fields are loaded as attributes for easier access. For example::

    >>> snap.header.z
    0.0
    >>> snap.header.time
    unyt_quantity(13.79874688, 'Gyr')
    >>> snap.header.box_size
    unyt_quantity(60000., 'code_length')

If the snapshot is cosmological, an `astropy Cosmology <http://docs.astropy.org/en/stable/cosmology/>`_ object is provided for cosmological calculations::

    >>> snap.header.cosmo
    LambdaCDM(H0=70.2 km / (Mpc s), Om0=0.272, Ode0=0.728, Tcmb0=0 K, Neff=3.04, m_nu=None, Ob0=None)

Raw fields on disk can be loaded on demand through a dictionary interface::

    >>> snap['PartType0', 'Coordinates']
    unyt_array([[30711.56320229, 33303.32765069, 33743.24254345],
                [30801.09893721, 33396.72993339, 33673.13785209],
                [30721.03179246, 33313.72662534, 33657.53180413],
                ...,
                [28702.32012144, 32308.36857189, 32512.44014079],
                [28695.79401442, 32304.20735574, 32514.23300421],
                [28700.69483794, 32308.30239816, 32518.00387993]], 'code_length')

The fields are loaded as unyt arrays. All available fields can be queried like::

    >>> snap.keys
    [('PartType0', 'Coordinates'),
     ('PartType0', 'Density'),
     ('PartType0', 'ElectronAbundance'),
     ('PartType0', 'InternalEnergy'),
     ('PartType0', 'Masses'),
     ('PartType0', 'Metallicity'),
     ('PartType0', 'NeutralHydrogenAbundance'),
     ('PartType0', 'ParticleIDs'),
     ('PartType0', 'Potential'),
     ('PartType0', 'SmoothingLength'),
     ('PartType0', 'StarFormationRate'),
     ('PartType0', 'Velocities'),
     ('PartType1', 'Coordinates'),
     ('PartType1', 'Masses'),
     ('PartType1', 'ParticleIDs'),
     ('PartType1', 'Potential'),
     ('PartType1', 'Velocities'),
     ('PartType2', 'Coordinates'),
     ('PartType2', 'Masses'),
     ('PartType2', 'ParticleIDs'),
     ('PartType2', 'Potential'),
     ('PartType2', 'Velocities'),
     ('PartType4', 'Coordinates'),
     ('PartType4', 'Masses'),
     ('PartType4', 'Metallicity'),
     ('PartType4', 'ParticleIDs'),
     ('PartType4', 'Potential'),
     ('PartType4', 'StellarFormationTime'),
     ('PartType4', 'Velocities')]

.. note::
   Whenever possible, fields and header attributes have units, which is supported by the `unyt <https://unyt.readthedocs.io/en/latest/>`_ package. The only exception is ``snap.header.cosmo``, which is an ``astropy`` object, thus using ``astropy.units``. Be cautious when mixing these two systems. See further `notes <https://unyt.readthedocs.io/en/latest/usage.html#working-with-code-that-uses-astropy-units>`_ here.

Particle selector and field access
----------------------------------

Particle selectors provide a more flexible way to access fields. Several particle selectors are preconfigured according to particle types. For example, gas particles could be accessed through::

    >>> snap.pt.gas
    <gizio.field.system.ParticleSelector at ...>

One major difference between the particle selector and the snapshot API is that fields can be accessed by predefined aliases through particle selectors. For example, to access the same ``('PartType0', 'Coordinates')`` field, we could simply do::

    >>> snap.pt.gas['p']
    unyt_array([[30711.56320229, 33303.32765069, 33743.24254345],
                [30801.09893721, 33396.72993339, 33673.13785209],
                [30721.03179246, 33313.72662534, 33657.53180413],
                ...,
                [28702.32012144, 32308.36857189, 32512.44014079],
                [28695.79401442, 32304.20735574, 32514.23300421],
                [28700.69483794, 32308.30239816, 32518.00387993]], 'code_length')

Particle selectors can be combined as if they are boolean arrays. For example, to define baryon as gas and star particles::

    >>> baryon = snap.pt.gas | snap.pt.star
    >>> snap.pt.gas.n_part
    753678
    >>> snap.pt.star.n_part
    361239
    >>> baryon.n_part
    1114917

Another way to generate new particle selectors is masking. For example, to define hot gas::

    >>> gas = snap.pt.gas
    >>> hot_gas = gas[gas['t'].to('K').v > 1e6]
    >>> hot_gas.n_part
    13549
    >>> hot_gas['t'].min()
    unyt_quantity(1000064.29406434, 'K')

A special predefined particle selector is ``snap.pt.all``, which selects all particles on disk.

Derived field
-------------

Particle selectors are field systems. Our field system supports derived field. As you might have noticed, the temperature field ``'t'`` is not a direct field on disk, but a derived field calculated from internal energy. The source code for the calculation could be examined by::

    >>> import inspect
    >>> print(inspect.getsource(gas.derived_fields['t']))
    def temperature(fs, f_ne='ne', f_u='u', f_z='z', i_he=1):
        # See the note following InternalEnergy on this page:
        # http://www.tapir.caltech.edu/~phopkins/Site/GIZMO_files/gizmo_documentation.html#snaps-reading
        ne = fs[f_ne]
        u = fs[f_u]
        z_he = fs[f_z][:, i_he]

        from unyt import kb, mp
        gamma = 5 / 3

        y = z_he / (4 * (1 - z_he))
        mu = (1 + 4 * y) / (1 + y + ne)
        temp = mu * mp * (gamma - 1) * u / kb
        return temp.to('K')

Only a minimum number of derived fields are added by default. Adding new derived fields is fairly easy. For example::

    >>> def m2(fs):
    >>>     return (fs['m']**2).to('Msun**2')
    >>> gas.derived_fields['m2'] = m2
    >>> gas['m2']
    unyt_array([2.0470067e+11, 2.0470067e+11, 2.0470067e+11, ...,
                2.0470067e+11, 2.0470067e+11, 2.0470067e+11], 'Msun**2')

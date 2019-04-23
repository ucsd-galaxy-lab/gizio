from collections import OrderedDict
from pathlib import Path

from astropy.cosmology import LambdaCDM
from unyt import UnitRegistry
from unyt import unyt_array

import gizio


def test_snapshot():
    rel_path = "data/FIRE_M12i_ref11/snapshot_600.hdf5"
    snap = gizio.Snapshot(rel_path)

    assert len(snap.paths) == 1
    assert snap.paths[0] == (Path(__file__).parent / rel_path).resolve()
    assert snap.name == "snapshot_600"
    assert isinstance(snap.spec, gizio.spec.abc.Specification)
    assert isinstance(snap.header, dict)
    assert isinstance(snap.shape, OrderedDict)
    assert isinstance(snap.cosmology, LambdaCDM)
    assert isinstance(snap.unit_registry, UnitRegistry)
    assert isinstance(snap.keys, list)
    for ptype, field in snap.keys:
        assert isinstance(snap[ptype, field], unyt_array)
    assert isinstance(snap.pt, dict)
    for key, value in snap.pt.items():
        assert isinstance(key, str)
        assert isinstance(value, gizio.field.ParticleSelector)

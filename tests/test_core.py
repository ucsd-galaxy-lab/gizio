from collections import OrderedDict
from pathlib import Path

from astropy.cosmology import LambdaCDM
from unyt import UnitRegistry
from unyt import unyt_array
from unyt import unyt_quantity

import gizio
from gizio.core import Snapshot
from gizio.core import ParticleSelector


SNAP_PATH = (
    Path(__file__).parent / "data/FIRE_M12i_ref11/snapshot_600.hdf5"
).resolve()


def test_load():
    """Test Snapshot class."""
    for prefix in [
        "data/FIRE_M12i_ref11/snapshot_600.hdf5",
        "data/FIRE_M12i_ref11/snapshot_600",
        "data/FIRE_M12i_ref11",
    ]:
        snap = gizio.load(prefix, suffix=".hdf5", spec="gizmo")
        assert isinstance(snap, Snapshot)
        assert tuple(snap.paths) == (SNAP_PATH,)


def test_snapshot():
    """Test Snapshot class."""
    snap = gizio.load(SNAP_PATH, spec="gizmo")

    # Test attributes
    assert isinstance(snap.paths, list)
    assert isinstance(snap.prefix, str)
    assert isinstance(snap.spec, gizio.spec.SpecBase)
    assert isinstance(snap.header, dict)
    assert isinstance(snap.shape, OrderedDict)
    assert isinstance(snap.cosmology, LambdaCDM)
    assert isinstance(snap.unit_registry, UnitRegistry)
    assert isinstance(snap.pt, dict)
    for key, value in snap.pt.items():
        assert isinstance(key, str)
        assert isinstance(value, ParticleSelector)

    # Test dictionay interface
    for key in snap.keys():
        assert isinstance(key, tuple)
        assert len(key) == 2
        data = snap[key]
        assert isinstance(data, unyt_array)
        assert key in snap.cached_keys()
    assert tuple(snap.cached_keys()) == tuple(snap.keys())
    for key in snap.keys():
        del snap[key]
        assert key not in snap.cached_keys()
    for key in snap.keys():
        snap[key]
    snap.clear_cache()
    assert len(snap.cached_keys()) == 0

    # Test unyt helpers
    x = snap.array([0, 0, 0], "m")
    assert isinstance(x, unyt_array)
    x = snap.quantity(0, "m")
    assert isinstance(x, unyt_quantity)


def test_particle_selector():
    """Test ParticleSelector class."""
    snap = gizio.load(SNAP_PATH)
    gas = snap.pt["gas"]
    star = snap.pt["star"]

    # Test attributes
    for ps in snap.pt.values():
        assert isinstance(gas.snap, Snapshot)
        assert isinstance(gas.pmask, OrderedDict)
        assert isinstance(gas.shape, OrderedDict)

    # Test field system
    for key in gas.keys():
        isinstance(gas[key], unyt_array)
    assert isinstance(gas.direct_fields(), dict)

    # Test mask operation
    hot_gas = gas[gas["t"].to_value("K") > 1e5]
    assert isinstance(hot_gas, ParticleSelector)
    baryon = gas | star
    assert isinstance(baryon, ParticleSelector)
    assert len(baryon) == len(gas) + len(star)
    assert isinstance(baryon & gas, ParticleSelector)
    assert len(baryon & gas) == len(gas)
    assert isinstance(baryon - gas, ParticleSelector)
    assert len(baryon - gas) == len(star)
    assert isinstance(baryon ^ gas, ParticleSelector)
    assert len(baryon ^ gas) == len(star)

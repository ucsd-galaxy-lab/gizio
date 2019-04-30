import gizio
from gizio.spec import SPEC_REGISTRY


def test_gizmo_spec():
    snap = gizio.load("data/FIRE_M12i_ref11", spec="gizmo")
    assert isinstance(snap.spec, SPEC_REGISTRY["gizmo"])

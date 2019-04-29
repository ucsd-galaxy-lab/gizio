import gizio


def test_gizmo_spec():
    snap = gizio.load("data/FIRE_M12i_ref11", spec="gizmo")
    assert isinstance(snap.spec, gizio.spec.GIZMOSpec)

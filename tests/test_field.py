from gizio.field import FieldSystem


def test_field_system():
    fs = FieldSystem(None)
    assert fs.snap is None

    fields_to_register = {"a": 1, "b": 2, "c": 3}

    for k, v in fields_to_register.items():
        fs.register(k, lambda fs: v)
    assert set(fs.keys()) == set(fields_to_register.keys())
    for k, v in fields_to_register.items():
        assert k in fs
        assert fs[k] == v
    assert "whatever" not in fs

    fs.unregister("a")
    assert "a" not in fs

    del fs["b"]
    assert "b" in fs

    fs.clear_cache()
    assert "c" in fs


def test_particle_selector():
    pass

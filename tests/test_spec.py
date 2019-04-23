import abc

from gizio.spec.abc import Specification


def test_specification():
    assert issubclass(Specification, abc.ABC)

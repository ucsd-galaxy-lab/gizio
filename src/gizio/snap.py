"""Simulation snapshot representation."""
import os
from pathlib import Path

import h5py
import numpy as np
import unyt

from .field import ParticleSelector
from .spec import SPEC_REGISTRY


class Snapshot:
    """Simulation snapshot.

    Fields could be loaded lazily through a dictionary interface:

    >>> snap[ptype, field]

    Parameters
    ----------
    prefix : str or pathlib.Path
    suffix : str, optional
        Snapshot file suffix. (default: ".hdf5")
    spec : str or Specification, optional
        Snapshot format specification. If given as str, a built-in
        specification will be used. (default: "gizmo")

    Attributes
    ----------
    paths : list
        Snapshot file paths.
    name : str
        Snapshot name.
    spec : Specification
        Snapshot format specification.
    header : dict
        Snapshot header.
    shape : collections.OrderedDict
        Data shape composed of {ptype_name: n_part} entries, in the
        specification ptypes order.
    cosmology : astropy.cosmology.LambdaCDM
        An astropy cosmology calculator.
    unit_registry : unyt.unit_registry.UnitRegistry
        Simulation unit registry.
    keys : list[tuple[str, str]]
        List of field keys.
    pt : dict[str, str]
        Dictionary of particle type selectors.

    """

    def __init__(self, prefix, suffix=".hdf5", spec="gizmo"):
        # Determine snapshot paths
        prefix = Path(prefix).expanduser().resolve()
        if prefix.is_dir():
            # Directory case
            self.dir = prefix
            glob_pattern = "*" + suffix
        else:
            self.dir = prefix.parent
            # Single file case
            glob_pattern = prefix.name
            if not prefix.is_file():
                # Glob prefix case
                glob_pattern += "*" + suffix
        self.paths = [path for path in sorted(self.dir.glob(glob_pattern))]
        stems = [path.stem for path in self.paths]
        self.name = os.path.commonprefix(stems).rstrip(".")
        # Check paths are not empty
        assert self.paths

        # Apply spec to extract meta info
        if isinstance(spec, str):
            spec = SPEC_REGISTRY[spec]()
        header, shape, cosmology, unit_registry = spec.apply_to(self)
        self.spec = spec
        self.header = header
        self.shape = shape
        self.cosmology = cosmology
        self.unit_registry = unit_registry

        # Detect available keys
        keys = []
        with h5py.File(self.paths[0], "r") as f:
            for ptype in self.spec.ptypes:
                if ptype in f:
                    for field in f[ptype].keys():
                        keys += [(ptype, field)]
        self.keys = keys

        # Set up particle type accessors
        self.pt = {}
        for ptype, abbr in self.spec.ptype_abbrs.items():
            if self.shape[ptype] > 0:
                ps = ParticleSelector.from_ptypes(self, [ptype])
                self.spec.register_derived_fields(ps, abbr)
                self.pt[abbr] = ps
        self.pt["all"] = ParticleSelector.from_ptypes(self, self.spec.ptypes)
        self.spec.register_derived_fields(self.pt["all"], "all")

        # Initialize cache
        self._cache = {}

    def array(self, value, unit):
        """Create an array with simulation unit registry.

        Parameters
        ----------
        value : typing.Iterable
            The value.
        unit : str
            The unit.

        Returns
        -------
        unyt.array.unyt_array
            An array with unit.

        """
        return unyt.unyt_array(value, unit, registry=self.unit_registry)

    def quantity(self, value, unit):
        """Create a quantity with simulation unit registry.

        Parameters
        ----------
        value : float
            The value.
        unit : str
            The unit.

        Returns
        -------
        unyt.array.unyt_quantity
            A quantity with unit.

        """
        return unyt.unyt_quantity(value, unit, registry=self.unit_registry)

    def clear_cache(self):
        """Clear all field caches."""
        self._cache = {}

    def __getitem__(self, key):
        # Load from file if cache doesn't exist
        if key not in self._cache:
            # Load value
            value = []
            for path in self.paths:
                with h5py.File(path, "r") as h5f:
                    value += [h5f["/".join(key)][()]]
            value = np.concatenate(value)
            # Determine unit
            _, field = key
            if field in self.spec.field_units:
                unit = self.spec.field_units[field]
            else:
                unit = "dimensionless"
            # Cache
            self._cache[key] = self.array(value, unit)
        # Retrieve cache
        return self._cache[key]

    def __delitem__(self, key):
        # Delete cache
        del self._cache[key]

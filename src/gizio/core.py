"""Core interface."""
from collections import OrderedDict
from copy import copy, deepcopy
import os
from pathlib import Path

import h5py
import numpy as np
import unyt

from .spec import SPEC_REGISTRY


def load(prefix, suffix=".hdf5", spec="gizmo"):
    """Load snapshot.

    Parameters
    ----------
    prefix : str or pathlib.Path
        Snapshot file(s) prefix.
    suffix : str, optional
        Snapshot file(s) suffix. (default: ".hdf5")
    spec : str or SpecBase, optional
        Snapshot format specification. If given as str, will use a built-in
        one. (default: "gizmo")

    Returns
    -------
    Snapshot
        The loaded snapshot.

    """
    # Determine snapshot paths
    prefix = Path(prefix).expanduser().resolve()
    if prefix.is_dir():
        # Directory case
        parent = prefix
        glob_pattern = "*" + suffix
    else:
        parent = prefix.parent
        # Single file case
        glob_pattern = prefix.name
        if not prefix.is_file():
            # Glob prefix case
            glob_pattern += "*" + suffix
    paths = sorted(parent.glob(glob_pattern))
    if isinstance(spec, str):
        spec = SPEC_REGISTRY[spec]()
    return Snapshot(paths, spec)


class Snapshot:
    """Simulation snapshot.

    .. describe:: snap[key]
    .. describe:: snap[ptype, field]

        Load the field from file and cache in memory.

    .. describe:: del snap[key]
    .. describe:: del snap[ptype, field]

        Delete the cache.

    Parameters
    ----------
    paths : typing.Iterable
        Snapshot file paths in correct order.
    spec : SpecBase
        Snapshot format specification.

    Attributes
    ----------
    paths : list
        Snapshot file paths.
    prefix : str
        Common prefix of paths without trailing dot.
    spec : SpecBase
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
    pt : dict
        Dictionary of particle type selectors.

    """

    def __init__(self, paths, spec):
        self.paths = [Path(path).resolve() for path in paths]
        self.prefix = os.path.commonprefix(self.paths).rstrip(".")

        # Apply spec to extract meta info
        header, shape, cosmology, unit_registry = spec.apply_to(self)
        self.spec = spec
        self.header = header
        self.shape = shape
        self.cosmology = cosmology
        self.unit_registry = unit_registry

        # Set up default particle selectors according to particle types
        self.pt = {}
        for ptype, abbr in self.spec.ptype_abbrs.items():
            if self.shape[ptype] > 0:
                self.pt[abbr] = ParticleSelector.from_ptypes(self, [ptype])
                self.spec.register_derived_fields(self.pt[abbr], abbr)
        self.pt["all"] = ParticleSelector.from_ptypes(self, self.spec.ptypes)
        self.spec.register_derived_fields(self.pt["all"], "all")

        # Initialize field cache
        self._field_cache = {}

    # dictionay interface

    def keys(self):
        """A list of available keys."""
        keys = []
        # It suffices to check the first file
        with h5py.File(self.paths[0], "r") as f:
            for ptype in self.spec.ptypes:
                if ptype in f:
                    for field in f[ptype].keys():
                        keys += [(ptype, field)]
        return keys

    def cached_keys(self):
        """A list of cached keys."""
        return list(self._field_cache.keys())

    def clear_cache(self):
        """Clear field cache."""
        self._field_cache = {}

    def __getitem__(self, key):
        # Create cache if not existing
        if key not in self._field_cache:
            # Load from file
            value = []
            for path in self.paths:
                with h5py.File(path, "r") as h5f:
                    value += [h5f["/".join(key)][()]]
            value = np.concatenate(value)
            # Determine unit
            _, field = key
            if field in self.spec.field_units:
                # Use spec unit if defined
                unit = self.spec.field_units[field]
            else:
                # Assume dimentionless otherwise
                unit = "dimensionless"
            # Create cache
            self._field_cache[key] = self.array(value, unit)
        # Retrieve cache
        return self._field_cache[key]

    def __delitem__(self, key):
        # Delete cache
        del self._field_cache[key]

    # unyt helpers

    def array(self, value, unit):
        """Helper method to create unyt array with snapshot unit registry.

        Parameters
        ----------
        value : typing.Iterable
            The value.
        unit : str
            The unit.

        Returns
        -------
        unyt.array.unyt_array
            A unyt array.

        """
        return unyt.unyt_array(value, unit, registry=self.unit_registry)

    def quantity(self, value, unit):
        """Helper method to create unyt quantity with snapshot unit registry.

        Parameters
        ----------
        value : float
            The value.
        unit : str
            The unit.

        Returns
        -------
        unyt.array.unyt_quantity
            A unyt quantity.

        """
        return unyt.unyt_quantity(value, unit, registry=self.unit_registry)


class ParticleSelector:
    """High level snapshot field access for selected particles.

    .. describe:: len(ps)

        Return the number of selected particles.

    .. describe:: ps[key]

        Retrieve the field. Compute and create cache if not existing already.

    .. describe:: del ps[key]

        Delete the cache.

    Parameters
    ----------
    snap : Snapshot
        The snapshot to access.

    Attributes
    ----------
    snap : Snapshot
        The snapshot to access.

    """

    @property
    def pmask(self):
        """collections.OrderedDict: Particle mask."""
        return OrderedDict(zip(self.snap.spec.ptypes, self._masks))

    @property
    def shape(self):
        """collections.OrderedDict: Shape."""
        return OrderedDict(
            [
                (ptype, mask.sum()) if mask is not None else (ptype, 0)
                for ptype, mask in self.pmask.items()
            ]
        )

    @classmethod
    def from_ptypes(cls, snap, ptypes):
        """Create particle selector for specified particle types.

        Parameters
        ----------
        snap : Snapshot
            The snapshot to access.
        ptypes : list
            A list of particle types to select.

        Returns
        -------
        ParticleSelector
            The corresponding particle selector.

        """
        spec_ptypes = deepcopy(snap.spec.ptypes)
        masks = []
        for ptype in spec_ptypes:
            if ptype in ptypes:
                n_part = snap.shape[ptype]
                mask = np.ones(n_part, dtype=bool)
            else:
                mask = None
            masks.append(mask)
        return cls(snap, masks)

    def __init__(self, snap, masks):
        # Initialize field system
        self.snap = snap
        self._masks = masks
        self.normalize_mask()
        self._field_registry = {}
        self._field_cache = {}

        # Register direct fields
        for key, field in self.direct_fields().items():
            self.register_direct_field(key, field)

    def __copy__(self):
        ps = ParticleSelector(self.snap, deepcopy(self._masks))
        ps._field_registry = deepcopy(self._field_registry)
        return ps

    def __len__(self):
        return sum(self.shape.values())

    # field system

    def keys(self):
        """All registered fields.

        Returns
        -------
        dict_keys
            A view on keys.

        """
        return self._field_registry.keys()

    def direct_fields(self):
        """Known direct fields.

        Returns
        -------
        dict
            A dictionary mapping shorhand keys to raw field names.

        """
        ptype_fields = {}
        for ptype, field in self.snap.keys():
            if self.pmask[ptype] is not None:
                if ptype not in ptype_fields:
                    ptype_fields[ptype] = {field}
                else:
                    ptype_fields[ptype].add(field)
        common_fields = set.intersection(*ptype_fields.values())

        direct_fields = {}
        for field in common_fields:
            if field in self.snap.spec.field_abbrs:
                key = self.snap.spec.field_abbrs[field]
            else:
                key = field
            direct_fields[key] = field
        return direct_fields

    def register_field(self, key, func):
        """Register a field.

        Parameters
        ----------
        key : str
            The key to retrieve the field.
        func : typing.Callable
            The function to compute the field.

        """
        self._field_registry[key] = func

    def register_direct_field(self, key, field):
        """Register a direct field.

        Parameters
        ----------
        key : str
            The key to retrieve the field.
        field : str
            The raw field name.

        """

        def load_direct_field(ps):
            data = []
            for ptype, mask in ps.pmask.items():
                if mask is not None:
                    data += [ps.snap[ptype, field][mask]]
            return unyt.array.uconcatenate(data)

        self.register_field(key, load_direct_field)

    def unregister_field(self, key):
        """Unregister a field.

        Parameters
        ----------
        key : str
            The key of the field.

        """
        del self._field_registry[key]
        del self[key]

    def clear_cache(self):
        """Clear all field caches."""
        self._field_cache = {}

    def __contains__(self, key):
        return key in self._field_registry

    def __getitem__(self, key):
        if isinstance(key, np.ndarray) and key.dtype == bool:
            # Boolean masking
            return self._where(key)
        if isinstance(key, str):
            # Field access
            if key not in self._field_cache:
                self._field_cache[key] = self._field_registry[key](self)
            return self._field_cache[key]
        raise KeyError

    def __delitem__(self, key):
        if key in self._field_cache:
            del self._field_cache[key]

    # mask operation

    def normalize_mask(self):
        """Normalize mask arrays."""
        # Consistently substitute all-false arrays by None
        self._masks = [
            mask if mask is not None and mask.any() else None
            for mask in self._masks
        ]

    def _where(self, cond):
        assert len(cond) == len(self)
        # Create new ParticleMask
        ps = copy(self)
        left = 0
        for mask in ps._masks:
            if mask is not None:
                # Update one mask array
                n_part = mask.sum()
                mask[mask] = cond[left : left + n_part]
                left += n_part
        ps.normalize_mask()
        return ps

    def _update_mask(self, operator, other):
        # Initialize object
        self.clear_cache()
        keys_to_unregister = [key for key in self.keys() if key not in other]
        for key in keys_to_unregister:
            self.unregister_field(key)

        # Evaluate operation
        from itertools import starmap

        def apply_op(mask1, mask2):
            if mask1 is None and mask2 is None:
                return None
            if mask1 is None:
                mask1 = np.zeros_like(mask2)
            if mask2 is None:
                mask2 = np.zeros_like(mask1)
            return operator(mask1, mask2)

        self._masks = tuple(starmap(apply_op, zip(self._masks, other._masks)))
        self.normalize_mask()
        return self

    ## | union

    def __or__(self, other):
        return copy(self).__ior__(other)

    def __ior__(self, other):
        return self._update_mask(np.logical_or, other)

    ## & intersection

    def __and__(self, other):
        return copy(self).__iand__(other)

    def __iand__(self, other):
        return self._update_mask(np.logical_and, other)

    ## - difference

    def __sub__(self, other):
        return copy(self).__isub__(other)

    def __isub__(self, other):
        return self._update_mask(lambda a, b: a ^ (a & b), other)

    ## ^ symmetric difference

    def __xor__(self, other):
        return copy(self).__ixor__(other)

    def __ixor__(self, other):
        return self._update_mask(np.logical_xor, other)

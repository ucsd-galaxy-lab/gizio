"""Field system."""
from copy import copy
from copy import deepcopy

import numpy as np
import unyt


class FieldSystem:
    """Field system of a snapshot.

    A field system is a set of fields potentially dependant on each other.
    A function is associated with each field to compute it in a lazy mannar.

    .. describe:: fs[key]

        Retrieve the field. Compute and create cache if not existing before.

    .. describe:: del fs[key]

        Removed the field cache.

    Parameters
    ----------
    snap : Snapshot
        The snapshot to associate with.

    Attributes
    ----------
    snap : Snapshot
        The snapshot associated with.

    """

    def __init__(self, snap):
        self.snap = snap
        self._func_registry = {}
        self._data_cache = {}

    def register(self, key, func):
        """Register a field.

        Parameters
        ----------
        key : str
            The key to retrieve the field.
        func : typing.Callable
            The function to compute the field.

        """
        self._func_registry[key] = func

    def unregister(self, key):
        """Unregister a field.

        Parameters
        ----------
        key : str
            The key of the field.

        """
        del self._func_registry[key]
        del self[key]

    def keys(self):
        """Available fields."""
        return self._func_registry.keys()

    def __contains__(self, key):
        return key in self._func_registry

    def __getitem__(self, key):
        if key not in self._data_cache:
            self._data_cache[key] = self._func_registry[key](self)
        return self._data_cache[key]

    def __delitem__(self, key):
        if key in self._data_cache:
            del self._data_cache[key]

    def clear_cache(self):
        """Clear all field caches."""
        self._data_cache = {}


class ParticleSelector(FieldSystem):
    """Particle selector.

    .. describe:: len(ps)

        Return the number of selected particles.

    """

    @classmethod
    def from_ptypes(cls, snap, ptypes):
        """Create particle selector for specified ptypes."""
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
        super().__init__(snap)

        # Register direct fields
        for ptype, field in snap.keys:
            i = snap.spec.ptypes.index(ptype)
            if masks[i] is not None:
                if field in snap.spec.fields:
                    key = snap.spec.field_abbrs[field]
                    self.register_direct_field(key, field)
                else:
                    self.register_direct_field(field, field)

        # Set masks
        self.masks = masks
        self._normalize()

    def __copy__(self):
        ps = ParticleSelector(self.snap, deepcopy(self.masks))
        ps._func_registry = deepcopy(self._func_registry)
        return ps

    def __len__(self):
        return sum(mask.sum() for mask in self.masks if mask is not None)

    def _normalize(self):
        # Consistently substitute all-false arrays by None
        self.masks = [
            mask if mask is not None and mask.any() else None
            for mask in self.masks
        ]

    # Field system

    def __getitem__(self, key):
        if isinstance(key, np.ndarray) and key.dtype == bool:
            # Boolean masking
            return self._update_mask(key)
        if isinstance(key, str):
            # Field access
            return super().__getitem__(key)
        raise KeyError

    def _update_mask(self, key):
        assert len(key) == len(self)
        # Create new ParticleMask
        ps = copy(self)
        left = 0
        for mask in ps.masks:
            if mask is not None:
                # Update one mask array
                n_part = mask.sum()
                mask[mask] = key[left : left + n_part]
                left += n_part
        return ps

    def register_direct_field(self, key, field):
        """Register a direct field.

        Parameters
        ----------
        key : str
            The key to retrieve the field.
        field : str
            The raw field name.

        """

        def load_direct_field(field_system):
            data = []
            snap = field_system.snap
            ptypes = snap.spec.ptypes
            masks = field_system.masks
            for ptype, mask in zip(ptypes, masks):
                if mask is not None:
                    data += [snap[ptype, field][mask]]
            return unyt.array.uconcatenate(data)

        self.register(key, load_direct_field)

    # Set-like operations

    def _set_op(self, operator, other, inplace):
        # Parse operator
        if operator == "sub":
            # Subtraction
            operator = lambda a, b: a ^ (a & b)
        else:
            # Built-in numpy boolean operations
            operator = getattr(np, "logical_" + operator)

        # Initialize object
        obj = self
        if not inplace:
            obj = deepcopy(obj)
        obj.clear_cache()
        keys_to_unregister = [key for key in obj.keys() if key not in other]
        for key in keys_to_unregister:
            obj.unregister(key)

        # Evaluate operation
        from itertools import starmap

        def eval_op(mask1, mask2):
            if mask1 is None and mask2 is None:
                return None
            if mask1 is None:
                mask1 = np.zeros_like(mask2)
            if mask2 is None:
                mask2 = np.zeros_like(mask1)
            return operator(mask1, mask2)

        obj.masks = list(starmap(eval_op, zip(obj.masks, other.masks)))
        obj._normalize()

        if not inplace:
            return obj

    ## | union

    def __or__(self, other):
        return self._set_op("or", other, inplace=False)

    def __ior__(self, other):
        self._set_op("or", other, inplace=True)

    ## & intersection

    def __and__(self, other):
        return self._set_op("and", other, inplace=False)

    def __iand__(self, other):
        self._set_op("and", other, inplace=True)

    ## - difference

    def __sub__(self, other):
        return self._set_op("sub", other, inplace=False)

    def __isub__(self, other):
        self._set_op("sub", other, inplace=True)

    ## ^ symmetric difference

    def __xor__(self, other):
        return self._set_op("xor", other, inplace=False)

    def __ixor__(self, other):
        self._set_op("xor", other, inplace=True)

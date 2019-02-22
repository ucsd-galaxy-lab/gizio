"""Field system objects."""
from copy import deepcopy
from inspect import getsource

import numpy as np
import unyt


class FieldSystem:
    """Field system."""
    def __init__(self, snap, direct_fields):
        self.snap = snap
        self.direct_fields = direct_fields
        self.derived_fields = {}
        self.alias = {}

        # Initialize cache
        self.clear_cache()

    def parse_alias(self, alias):
        """Parse alias field names."""
        norm = alias
        while norm in self.alias:
            norm = self.alias[norm]
        return norm

    def _load_direct_field(self, field):
        raise NotImplementedError

    def __getitem__(self, key):
        key = self.parse_alias(key)
        if key not in self._cache:
            if key in self.direct_fields:
                self._cache[key] = self._load_direct_field(key)
            elif key in self.derived_fields:
                self._cache[key] = self.derived_fields[key](self)
            else:
                raise KeyError
        return self._cache[key]

    def __delitem__(self, key):
        del self._cache[key]

    def getsource(self, key):
        """Get source code for derived fields."""
        if key not in self.derived_fields:
            raise KeyError
        func = self.derived_fields[key]
        # To deal with functools.partial
        while hasattr(func, 'func'):
            func = getattr(func, 'func')
        return getsource(func)

    def clear_cache(self):
        """Clear data cache."""
        self._cache = {}

    def intersect(self, other):
        """Intersect with another field system."""
        def dict_intersect(d1, d2):
            return dict(set(d1.items()) & set(d2.items()))

        self.direct_fields = set(self.direct_fields) & set(other.direct_fields)
        self.derived_fields = dict_intersect(
            self.derived_fields, other.derived_fields
        )
        self.alias = dict_intersect(
            self.alias, other.alias
        )


class ParticleSelector(FieldSystem):
    """Particle selector."""
    @classmethod
    def from_ptype(cls, snap, ptypes):
        """Create from a list of particle types."""
        mask = {}
        for ptype in ptypes:
            iptype = snap.spec.ptypes.index(ptype)
            n_part = snap.header.n_part_tot[iptype]
            mask[ptype] = np.ones(n_part, dtype=bool)
        return cls(snap, mask)

    def __init__(self, snap, mask):
        # Specify direct fields
        direct_fields = set(
            field for ptype, field in snap.keys if ptype in mask
        )

        super().__init__(snap, direct_fields)
        self.mask = mask

        # Set aliases
        for fa, field in snap.spec.field_alias.items():
            self.alias[fa] = field

    @property
    def n_part(self):
        """Number of particles selected."""
        return sum([ma.sum() for ma in self.mask.values()])

    def _load_direct_field(self, field):
        data = []
        for ptype in sorted(self.mask.keys()):
            data += [self.snap[ptype, field][self.mask[ptype]]]
        return unyt.array.uconcatenate(data)

    def __getitem__(self, key):
        if isinstance(key, np.ndarray) and key.dtype == bool:
            # Boolean masking
            mask = {}
            left = 0
            for ptype in self.snap.ptypes:
                if ptype in self.mask:
                    # Mask for each ptype
                    mask[ptype] = self.mask[ptype].copy()
                    n_true = mask[ptype].sum()
                    mask_ptype = key[left:left + n_true]
                    mask[ptype][mask[ptype]] = mask_ptype
                    left += n_true
            ps = deepcopy(self)
            ps.clear_cache()
            ps.mask = mask
            return ps
        if isinstance(key, str):
            return super().__getitem__(key)
        raise KeyError

    # Boolean operations

    def __logical__(self, operator, other=None):
        if other is not None:
            assert self.snap is other.snap

        mask = {}
        for ptype in self.mask.keys():
            mask[ptype] = self.mask[ptype]
        if other is not None:
            # Binary operator case
            for ptype in other.mask.keys():
                if ptype not in mask:
                    mask[ptype] = np.zeros_like(other.mask[ptype])
                mask[ptype] = operator(mask[ptype], other.mask[ptype])
        else:
            # Unary operator case
            for pmask in mask.values():
                pmask = operator(pmask)

        ps = deepcopy(self)
        ps.clear_cache()
        ps.mask = mask
        if other is not None:
            ps.intersect(other)
        return ps

    def __and__(self, other):
        return self.__logical__(np.logical_and, other)

    def __xor__(self, other):
        return self.__logical__(np.logical_xor, other)

    def __or__(self, other):
        return self.__logical__(np.logical_or, other)

    def __invert__(self):
        return self.__logical__(np.logical_not)

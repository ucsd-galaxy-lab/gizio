import numpy as np
import unyt


class FieldSystem(object):
    def __init__(self, direct_fields):
        self.direct_fields = direct_fields
        self.derived_fields = {}
        self._alias = {}

        # Initialize cache
        self.clear_cache()

    def set_alias(self, norm, alias):
        self._alias[alias] = norm

    def parse_alias(self, alias):
        norm = alias
        while norm in self._alias:
            norm = self._alias[norm]
        return norm

    def _load_direct_field(self, key):
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

    def clear_cache(self):
        self._cache = {}


class ParticleSelector(FieldSystem):
    @classmethod
    def from_ptype(cls, snap, ptypes):
        mask = {}
        for ptype in ptypes:
            iptype = snap.spec.ptypes.index(ptype)
            n_part = snap.header.n_part_tot[iptype]
            mask[ptype] = np.ones(n_part, dtype=bool)
        return cls(snap, mask)

    def __init__(self, snap, mask):
        self.snap = snap
        self.mask = mask

        # Specify direct fields
        direct_fields = set(
            field for ptype, field in snap.keys if ptype in mask
        )
        super().__init__(direct_fields)

        # Set aliases
        for fa, field in snap.spec.field_alias.items():
            self.set_alias(field, fa)

    @property
    def n_part(self):
        return sum([ma.sum() for ma in self.mask.values()])

    def _load_direct_field(self, field):
        data = []
        for ptype in sorted(self.mask.keys()):
            data += [self.snap[ptype, field][self.mask[ptype]]]
        return unyt.array.uconcatenate(data)

    def __getitem__(self, key):
        if isinstance(key, np.ndarray) and key.dtype == bool:
            # Boolean masking
            mask = self.mask.copy()
            mask[mask] = key
            return ParticleSelector(self.snap, mask)
        elif isinstance(key, str):
            return super().__getitem__(key)
        else:
            raise KeyError

    # Boolean operations

    def __logical__(self, operator, other=None):
        if other is not None:
            assert self.snap is other.snap
        snap = self.snap

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
            for ptype in mask.keys():
                mask[ptype] = operator(mask[ptype])

        return ParticleSelector(snap, mask)

    def __and__(self, other):
        return self.__logical__(np.logical_and, other)

    def __xor__(self, other):
        return self.__logical__(np.logical_xor, other)

    def __or__(self, other):
        return self.__logical__(np.logical_or, other)

    def __invert__(self):
        return self.__logical__(np.logical_not)

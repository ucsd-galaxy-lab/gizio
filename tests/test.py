from pprint import pprint

import gizio

snap = gizio.Snapshot('~/data/yt/FIRE_M12i_ref11/snapshot_600.hdf5')
pprint(snap.header)
pprint(snap.shape)
pprint(snap.keys)
print(snap['PartType0', 'Coordinates'])

gas = snap.pt.gas
print(gas.keys())
print(gas['p'])
print(gas['t'])

star = snap.pt.star
print(star.keys())
print(star['p'])
print(star['age'])

baryon = gas | star
print(baryon.keys())
print(baryon['p'])

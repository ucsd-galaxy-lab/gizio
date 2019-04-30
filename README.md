# gizio
A light-weight Python package for [GIZMO](http://www.tapir.caltech.edu/~phopkins/Site/GIZMO.html) snapshot IO

[![Build Status](https://travis-ci.org/galaxy-lab/gizio.svg?branch=master)](https://travis-ci.org/galaxy-lab/gizio)
[![Documentation Status](https://readthedocs.org/projects/gizio/badge/?version=latest)](https://gizio.readthedocs.io/en/latest/?badge=latest)

- Development: https://github.com/galaxy-lab/gizio
- Documentation: https://gizio.readthedocs.io

## About

There are [two snapshot reading scripts](http://www.tapir.caltech.edu/~phopkins/Site/GIZMO_files/gizmo_documentation.html#snaps-reading) `readsnap.py` and `load_from_snapshot.py` accompanying the [GIZMO source code](https://bitbucket.org/phopkins/gizmo-public/src/). gizio aims to replace `load_from_snapshot.py` with several improvements:

- A more flexible interface to access field
- A unit system powered by [unyt](https://unyt.readthedocs.io)
- Easier format spec customization without source code modification
- Easier to install and maintain as a Python package

We acknowledge [yt](https://yt-project.org) and [pynbody](https://pynbody.github.io/pynbody/) for interface design inspirations.

## Demo

The sample data could be downloaded [here](http://yt-project.org/data/FIRE_M12i_ref11.tar.gz).

Load a snapshot:

```python
>>> import gizio
>>> snap = gizio.load('data/FIRE_M12i_ref11/snapshot_600.hdf5')
```

View its header:

```python
>>> snap.header
{'time': unyt_quantity(13.79874688, 'Gyr'),
 'n_file': 1,
 'mass_tab': unyt_array([0., 0., 0., 0., 0., 0.], 'code_mass'),
 'f_sfr': 1,
 'f_cool': 1,
 'f_fb': 1,
 'f_age': 1,
 'f_met': 11,
 'n_part': array([ 753678, 1104128, 2567905,       0,  361239,       0], dtype=uint32),
 'n_part_pf': [array([ 753678, 1104128, 2567905,       0,  361239,       0], dtype=int32)],
 'box_size': unyt_quantity(60000., 'code_length'),
 'Om0': 0.272,
 'OmL': 0.728,
 'h': 0.702,
 'z': 0.0,
 'cosmological': True}
```

Load a field:

```python
>>> snap['PartType0', 'Masses']
unyt_array([3.175186e-05, 3.175186e-05, 3.175186e-05, ..., 3.175186e-05,
            3.175186e-05, 3.175186e-05], dtype=float32, units='code_mass')
```

Load a field using shorthands:

```python
>>> snap.pt['gas']['m']
unyt_array([3.175186e-05, 3.175186e-05, 3.175186e-05, ..., 3.175186e-05,
            3.175186e-05, 3.175186e-05], dtype=float32, units='code_mass')
```

Select particles by masking:

```python
>>> gas = snap.pt['gas']
>>> hot_gas = gas[gas['t'].to_value('K') > 1e5]
>>> hot_gas['t'].min()
unyt_quantity(100000.79, dtype=float32, units='K')
```

Select particles by composing:

```python
>>> star = snap.pt['star']
>>> baryon = gas | star
>>> len(gas)
753678
>>> len(star)
361239
>>> len(baryon)
1114917
>>> baryon['m']
unyt_array([3.1751861e-05, 3.1751861e-05, 3.1751861e-05, ...,
            2.2581291e-05, 2.3056862e-05, 2.7417644e-05], dtype=float32, units='code_mass')
```

## Installation

Install latest stable version from PyPI:

```bash
pip install gizio
```

Install development version from source:

```bash
git clone https://github.com/galaxy-lab/gizio.git
cd gizio
pip install -e .
```

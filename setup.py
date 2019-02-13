from setuptools import find_packages, setup

setup(
    name='gizio',
    packages=find_packages(),
    install_requires=[
        'h5py',
        'numpy',
        'unyt',
    ]
)

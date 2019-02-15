from setuptools import find_packages, setup

setup(
    name='gizio',
    packages=find_packages(),
    package_data={
        '': ['*.json'],
    },
    install_requires=[
        'h5py',
        'numpy',
        'unyt',
    ]
)

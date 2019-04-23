from setuptools import find_packages, setup

setup(
    name="gizio",
    package_dir={"": "src"},
    packages=find_packages("src"),
    install_requires=["astropy", "h5py", "numpy", "unyt"],
)

import os
from setuptools import find_packages, setup

here = os.path.abspath(os.path.dirname(__file__))

about = {}
with open(os.path.join(here, "src/gizio", "__about__.py"), "r") as f:
    exec(f.read(), about)

with open("README.md", "r") as f:
    long_description = f.read()

setup(
    name="gizio",
    version=about["__version__"],
    author=about['__author__'],
    description=about["__description__"],
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://gizio.readthedocs.io",
    package_dir={"": "src"},
    packages=find_packages("src"),
    install_requires=["astropy", "h5py", "numpy", "unyt"],
    classifiers=[
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
    ],
)

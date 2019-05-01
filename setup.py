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
    author=about["__author__"],
    description=about["__description__"],
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://gizio.readthedocs.io",
    packages=find_packages("src"),
    package_dir={"": "src"},
    python_requires=">=3.6",
    install_requires=["astropy", "h5py", "numpy", "unyt"],
    # https://pypi.org/classifiers/
    classifiers=[
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Scientific/Engineering",
    ],
)

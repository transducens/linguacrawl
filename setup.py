#!/usr/bin/env python

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()
with open("requirements.txt") as rf:
    requirements = rf.read().splitlines()
    
setuptools.setup(
    name="linguacrawl",
    version="0.1",
    install_requires=requirements,
    license="GNU General Public License v3.0",
    author="Miquel Esplà-Gomis (Universitat d'Alacant)",
    author_email="mespla@dlsi.ua.es",
    maintainer="Miquel Esplà-Gomis",
    maintainer_email="mespla@dlsi.ua.es",
    description="Tool to crawl a TLD looking for data in specific languages",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/transducens/linguacrawl",
    packages=setuptools.find_packages(),
    classifiers=[
        "Environment :: Console",
        "Intended Audience :: Science/Research",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: POSIX :: Linux",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Text Processing :: Linguistic",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Text Processing :: Filters"
    ],
    project_urls={
        "Linguacrawl on GitHub": "https://github.com/transducens/linguacrawl",
        "Departament de Llenguatges i Sistemes Informàtics de la Universitat d'Alacant": "https://www.dlsi.ua.es",
        "GoURMET": "https://gourmet-project.eu",
        "Paracrawl": "https://paracrawl.eu/"
         },
    scripts=[
         "scripts/linguacrawl",
         ]     
)

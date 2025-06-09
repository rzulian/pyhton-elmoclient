#!/usr/bin/env python

from setuptools import setup, find_packages
import os

# Read the contents of README.md file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="python-elmoclient",
    version="0.0.5",
    license="MIT",
    description="Python library for Elmo control units",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Riccardo Zulian",
    author_email="riccardo.zulian@gmail.com",
    url="https://github.com/rzulian/python-elmoclient",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.9",
        "Topic :: Home Automation",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    install_requires=[],
    python_requires=">=3.6",
    zip_safe=True,
)

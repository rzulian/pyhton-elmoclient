#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name = 'python-elmoclient',
    version = '0.0.1',
    license = 'MIT',
    description = 'Python library for Elmo control units',
    author = 'Riccardo Zulian',
    author_email = 'riccardo.zulian@gmail.com',
    url = 'https://github.com/rzulian/pyhton-elmoclient',
    packages=find_packages(),
    classifiers = [
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.9',
        'Topic :: Home Automation',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    install_requires=[],
    zip_safe=True,
)
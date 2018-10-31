#!/usr/bin/env python

from setuptools import setup, find_packages

exec(open("kin/version.py").read())

with open('requirements.txt') as f:
    requires = [line.split(' ')[0] for line in f]
with open('requirements-dev.txt') as f:
    tests_requires = [line.split(' ')[0] for line in f]

setup(
    name='kin-sdk',
    version=__version__,
    description='KIN SDK for Python',
    author='Kin Ecosystem',
    author_email='david.bolshoy@kik.com',
    maintainer='Ron Serruya',
    maintainer_email='ron.serruya@kik.com',
    url='https://github.com/kinecosystem/kin-core-python/tree/v2-master',
    license='MIT',
    packages=find_packages(),
    long_description=open("README.md").read(),
    keywords=["kin", "stellar", "blockchain", "cryptocurrency"],
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
    ],
    install_requires=requires,
    tests_require=tests_requires,
    python_requires='>=2.7',
)

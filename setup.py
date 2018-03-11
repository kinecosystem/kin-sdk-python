#!/usr/bin/env python

from setuptools import setup, find_packages

exec(open("kin/version.py").read())

with open('requirements.txt') as f:
    requires = [line.strip() for line in f if line.strip()]
with open('requirements-dev.txt') as f:
    tests_requires = [line.strip() for line in f if line.strip()]

setup(
    name='kin',
    version=__version__,
    description='KIN Stellar SDK for Python',
    author='Kin Foundation',
    author_email='david.bolshoy@kik.com',
    maintainer='David Bolshoy',
    maintainer_email='david.bolshoy@kik.com',
    url='https://github.com/kinfoundation/kin-core-python',
    license='MIT',
    packages=find_packages(),
    long_description=open("README.md").read(),
    keywords=["kin", "stellar", "blockchain", "cryptocurrency"],
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Developers',
        'Development Status :: 0 - Alpha/unstable',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
    ],
    install_requires=requires,
    tests_require=tests_requires,
    python_requires='>=2.7',
)

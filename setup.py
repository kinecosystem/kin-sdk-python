#!/usr/bin/env python

from setuptools import setup, find_packages

exec(open("kin/version.py").read())

with open('requirements.txt') as f:
    requires = f.readlines()
with open('requirements-dev.txt') as f:
    tests_requires = f.readlines()

setup(
    name='kin-sdk',
    version=__version__,
    description='KIN SDK for Python',
    author='Kin Ecosystem',
    author_email='david.bolshoy@kik.com',
    maintainer='Ron Serruya',
    maintainer_email='ron.serruya@kik.com',
    url='https://github.com/kinecosystem/kin-sdk-python/tree/v2-master',
    license='MIT',
    packages=find_packages(),
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    keywords=["kin", "stellar", "blockchain", "cryptocurrency"],
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
    ],
    install_requires=requires,
    tests_require=tests_requires,
    python_requires='>=3.6',
)

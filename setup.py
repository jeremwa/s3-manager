# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
with open('requirements.txt') as f:
    required = f.read().splitlines()
setup(
    name='s3_manager',
    version="1.0",
    author = "Jeremy Walker",
    author_email = "jeremw@amazon.com",
    license = "BSD",
    packages=find_packages(),
    include_package_data=False,
    install_requires=required,
    entry_points = {
        "console_scripts": ['s3-manager=s3_manager.s3_manager:main']
    },
)

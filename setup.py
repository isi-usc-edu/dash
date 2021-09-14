#!/usr/bin/env python
# encoding: utf-8

from distutils.core import setup
from setuptools import find_packages

setup(name='Dash2', 
      version='0.1', 
      description='DASH agent-based modeling framework', 
      author='Jim Blythe <blythe@isi.edu>', 
      license='MIT',                        
      packages=find_packages(exclude=['papers', 'docs']),
      install_requires=['numpy', 'pandas']
)

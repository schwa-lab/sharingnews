# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

setup(
  name='likeable',
  description='likeable linkage project',
  packages=find_packages(),
  entry_points={
    'console_scripts': [
        #'likeable-manage = likeable.manage:main',
    ],
  },
  # TODO: dependencies
  install_requires=[
  ],
)

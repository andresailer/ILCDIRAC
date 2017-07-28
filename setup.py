"""
Setup script for ILCDIRAC
"""

import os
import re

from setuptools import setup


PACKAGES= [
  'Core',
  'DataManagementSystem',
  'ILCTransformationSystem',
  'Interfaces',
  'OverlaySystem',
  'RequestManagementSystem',
  'Resources',
  'Tests',
  'Workflow',
  'WorkloadManagementSystem',
]

def find_packages( path='.' ):
  """ find all packages, need to re-implement from setuptools because we need to follow the links """
  ret = []
  for root, _dirs, files in os.walk(path, followlinks=True):
    if '__init__.py' in files:
      ret.append(re.sub('^[^A-z0-9_]+', '', root.replace('/', '.')))

  return ret

def read( fname ):
  """ read fname and return the string """
  return open(os.path.join(os.path.dirname(__file__), fname)).read()

def makeILCDIRAC( bf="ILCDIRAC" ):
  """ create a ILCDIRAC module with the existing PACKAGES """
  if not os.path.exists( bf ):
    os.mkdir( bf )
  for folder in PACKAGES+['__init__.py']:
    newFolder=os.path.join( bf, folder )
    if not os.path.exists( newFolder ):
      os.symlink( "../%s" % folder, newFolder )

makeILCDIRAC()

setup(
  name = "ILCDIRAC",
  version = "26",
  keywords = "",
  packages=find_packages( "ILCDIRAC" ),
  license = "GPL3",
  long_description='README.md',
  classifiers=[
    "Development Status :: 3 - Production",
    "Topic :: Grid",
  ],
)

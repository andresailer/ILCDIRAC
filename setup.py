""" setup script for ILCDIRAC

get a copy of DIRAC and make a link to ILCDIRAC in this folder so we have the structure expected by landscape
"""

import zipfile
import urllib2
import os
import shutil
from setuptools import setup
from setuptools import find_packages
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


def getDIRAC( version ):
    """ get the dirac zip file from github """
    if os.path.exists( "DIRAC" ):
        shutil.rmtree( "DIRAC" )
    
    remotezip = urllib2.urlopen("https://github.com/DIRACGrid/DIRAC/archive/%s.zip" % version )
    with open( "dirac.zip", "wb") as dirzip:
        dirzip.write( remotezip.read() )
    
    with zipfile.ZipFile( "dirac.zip", "r") as zipref:
        zipref.extractall(".")

    os.rename( "DIRAC-%s" % version, "DIRAC" )

def makeLink():
    """ make a link for ILCDIRAC """
    if not os.path.exists( "ILCDIRAC" ):
        os.symlink( ".", "ILCDIRAC" )

makeLink()
getDIRAC( "rel-v6r14" )

setup(
    name = "iLCDirac",
    version = "25.0.8",
    author = "Andre Sailer",
    author_email = "andre.philippe.sailer@cern.ch",
    description = ("An demonstration of how to create, document, and publish "
                                   "to the cheese shop a5 pypi.org."),
    keywords = "",
    packages=find_packages( exclude=["Test*"] ),
    license = "GPL3",
    long_description='README.md',
    install_requires=[
        "DIRAC",
    ],
    dependency_links = [
        "https://github.com/DIRACGrid/DIRAC/archive/rel-v6r14.zip#egg=DIRAC",
    ],
    classifiers=[
        "Development Status :: 3 - Production",
        "Topic :: Grid",
    ],
)

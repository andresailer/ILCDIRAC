'''
Created on Apr 7, 2010

@author: sposs
'''
import DIRAC

import os, urllib, tarfile

def TARinstall(app,config,area):
  os.chdir(area)
  appName    = app[0]
  appVersion = app[1]
  appName = appName.lower()
  app_tar = DIRAC.gConfig.getValue('/Operations/AvailableTarBalls/%s/%s/%s'%(config,appName,appVersion),'')
  if not app_tar:
    DIRAC.gLogger.error('Could not find tar ball for %s %s'%(appName,appVersion))
    return DIRAC.S_ERROR('Could not find tar ball for %s %s'%(appName,appVersion))
  TarBallURL = DIRAC.gConfig.getValue('/Operations/AvailableTarBalls/%s/%s/TarBallURL'%(config,appName),'')
  if not TarBallURL:
    DIRAC.gLogger.error('Could not find TarBallURL in CS for %s %s'%(appName,appVersion))
    return DIRAC.S_ERROR('Could not find TarBallURL in CS')
  #downloading file from url, but don't do if file is already there.
  if not os.path.exists("%s/%s"%(os.getcwd(),app_tar)):
    try :
      DIRAC.gLogger.debug("Downloading software", '%s_%s' %(appName,appVersion))
      #Copy the file locally, don't try to read from remote, soooo slow
      #Use string conversion %s%s to set the address, makes the system more stable
      tarball,headers = urllib.urlretrieve("%s%s"%(TarBallURL,app_tar),app_tar)
    except:
      DIRAC.gLogger.exception()
      return DIRAC.S_ERROR('Exception during url retrieve')
  if not os.path.exists("%s/%s"%(os.getcwd(),app_tar)):
    DIRAC.gLogger.error('Failed to download software','%s_%s' %(appName,appVersion))
    return DIRAC.S_ERROR('Failed to download software')

  app_tar_to_untar = tarfile.open(app_tar)
  app_tar_to_untar.extractall()
  
  #remove now useless tar ball
  try:
    os.unlink(app_tar)
  except:
    DIRAC.gLogger.exception()
  return DIRAC.S_OK()

def remove():
  pass

#!/bin/env python
'''
Add software from CVMFS to the CS

Give list of applications, init_script path, MokkaDBSlice, ILDConfigPath (if set)

Created on May 5, 2010
'''

__RCSID__ = "$Id$"

from DIRAC.Core.Base import Script
from DIRAC import gLogger, gConfig, S_OK, exit as dexit
import os


class Params(object):
  """Collection of Parameters set via CLI switches"""
  def __init__( self ):
    self.version = ''
    self.platform = 'x86_64-slc5-gcc43-opt'
    self.comment = ''
    self.applicationList = ''
    self.dbSliceLocation = ''
    self.initScriptLocation = ''
    self.basePath = ''
    self.ildConfigPath = ''

  def setVersion(self, optionValue):
    self.version = optionValue
    return S_OK()

  def setPlatform(self, optionValue):
    self.platform = optionValue
    return S_OK()

  def setName(self, optionValue):
    self.applicationList = optionValue.split(',')
    return S_OK()

  def setComment(self, optionValue):
    self.comment = optionValue
    return S_OK()

  def setDBSlice(self, optionValue):
    self.dbSliceLocation = optionValue
    return S_OK()

  def setInitScript(self, optionValue):
    self.initScriptLocation = optionValue
    return S_OK()

  def setBasePath(self, optionValue):
    self.basePath = optionValue
    return S_OK()

  def setILDConfig(self, optionValue):
    self.ildConfigPath = optionValue
    return S_OK()


  def registerSwitches(self):
    Script.registerSwitch("P:", "Platform=", "Platform ex. %s" % self.platform, self.setPlatform)
    Script.registerSwitch("A:", "Applications=", "Comma separated list of applications", self.setName)
    Script.registerSwitch("V:", "Version=", "Version name", self.setVersion)
    Script.registerSwitch("C:", "Comment=", "Comment", self.setComment)
    Script.registerSwitch("S:", "Script=", "Full path to initScript", self.setInitScript)
    Script.registerSwitch("B:", "Base=", "Path to Installation Base", self.setBasePath)

    Script.registerSwitch("O:", "ILDConfig=", "Path To ILDConfig (if it is in ApplicationPath)", self.setILDConfig)

    Script.setUsageMessage( '\n'.join( [ __doc__.split( '\n' )[1],
                                         '\nUsage:',
                                         '  %s [option|cfgfile] ...\n' % Script.scriptName ] ) )

class CVMFSAdder(object):
  """Container for all the objects and functions to add software to ILCDirac"""
  def __init__(self, cliParams ):
    from DIRAC.Interfaces.API.DiracAdmin import DiracAdmin
    self.diracAdmin = DiracAdmin()
    self.modifiedCS = False
    self.softSec = "/Operations/Defaults/AvailableTarBalls"
    self.mailadress = 'ilc-dirac@cern.ch'
    self.params = cliParams

  #FIXME!!!!
  def checkConsistency(self):
    """checks if platform is defined, application exists, etc."""
    gLogger.notice("Checking consistency")
    av_platforms = gConfig.getSections(self.softSec, [])
    if av_platforms['OK']:
      if not self.platform in av_platforms['Value']:
        gLogger.error("Platform %s unknown, available are %s." % (self.platform, ", ".join(av_platforms['Value'])))
        gLogger.error("If yours is missing add it in CS")
        dexit(255)
    else:
      gLogger.error("Could not find all platforms available in CS")
      dexit(255)

    av_apps = gConfig.getSections("%(softSec)s/%(platform)s" % self.parameter, [])
    if not av_apps['OK']:
      gLogger.error("Could not find all applications available in CS")
      dexit(255)

  def commitToCS(self):
    """write changes to the CS to the server"""
    gLogger.notice("Commiting changes to the CS")
    if self.modifiedCS:
      result = self.diracAdmin.csCommitChanges(False)
      if not result[ 'OK' ]:
        gLogger.error('Commit failed with message = %s' % (result[ 'Message' ]))
        dexit(255)
      gLogger.info('Successfully committed changes to CS')
    else:
      gLogger.info('No modifications to CS required')

  def notifyAboutNewSoftware(self):
    """Send an email to the mailing list if a new software version was defined"""

    #Only send email when something was actually added
    if not self.modifiedCS:
      return

    subject = '%s %s added to DIRAC CS' % (self.appName, self.appVersion)
    msg = 'New application %s %s declared into Configuration service\n %s' % (self.appName,
                                                                              self.appVersion,
                                                                              self.comment)
    from DIRAC.Core.Security.ProxyInfo import getProxyInfo
    from DIRAC.ConfigurationSystem.Client.Helpers.Registry import getUserOption
    from DIRAC.FrameworkSystem.Client.NotificationClient       import NotificationClient

    notifyClient = NotificationClient()
    gLogger.notice('Sending mail for software installation to %s' % (self.mailadress))
    res = getProxyInfo()
    if not res['OK']:
      sender = 'ilcdirac-admin@cern.ch'
    else:
      if 'username' in res['Value']:
        sender = getUserOption(res['Value']['username'],'Email')
      else:
        sender = 'nobody@cern.ch'
    gLogger.info('*'*80)# surround email with stars
    res = notifyClient.sendMail(self.mailadress, subject, msg, sender, localAttempt = False)
    gLogger.info('*'*80)
    if not res[ 'OK' ]:
      gLogger.error('The mail could not be sent: %s' % res['Message'])




  def addVersionToCS(self):
    """adds the version of the application to the CS"""
    gLogger.notice("Adding version %(appVersion)s to the CS" % self.parameter)
    existingVersions = gConfig.getSections("%(softSec)s/%(platform)s/%(appname)s" % self.parameter, [])
    if not existingVersions['OK']:
      gLogger.error("Could not find all versions available in CS: %s" % existingVersions['Message'])
      dexit(255)
    if self.appVersion in existingVersions['Value']:
      gLogger.always('Application %s %s for %s already in CS, nothing to do' % (self.appName.lower(),
                                                                                self.appVersion,
                                                                                self.platform))
      dexit(0)

    result = self.diracAdmin.csSetOption("%(softSec)s/%(platform)s/%(appname)s/%(appVersion)s/TarBall" % self.parameter,
                                         self.parameter['appTar_name'])
    if result['OK']:
      self.modifiedCS = True
    else:
      gLogger.error ("Could not add version to CS")
      dexit(255)

  def addCommentToCS(self):
    """adds the comment for the TarBall to the CS"""
    gLogger.notice("Adding comment to CS: %s" % self.comment)
    result = self.diracAdmin.csSetOptionComment("%(softSec)s/%(platform)s/%(appname)s/%(appVersion)s/TarBall"% self.parameter,
                                                self.comment)
    if not result['OK']:
      gLogger.error("Error setting comment in CS")

  def addSoftware(self):
    """run all the steps to add software to grid and CS"""

    self.checkConsistency()
    self.addVersionToCS()
    self.addCommentToCS()
    self.commitToCS()
    self.notifyAboutNewSoftware()



def addSoftware():
  """uploads, registers, and sends email about new software package"""
  cliParams = Params()
  cliParams.registerSwitches()
  Script.parseCommandLine( ignoreErrors = True )

  softAdder = CVMFSAdder(cliParams)
  resCheck = softAdder.checkConsistency()
  
  if resCheck['OK']:
    Script.showHelp()
    dexit(2)

  softAdder.addSoftware()

  gLogger.notice("All done!")
  dexit(0)

if __name__=="__main__":
  addSoftware()

#!/bin/env python
"""
Prepare the production summary tables



Options:
   -P, --prods prodID            Productions: greater than with gt1234, range with 32-56, list with 34,56
   -p, --precise_detail          Precise detail, slow
   -v, --verbose                 Verbose output
   -t, --types prodTypeList      Production Types, comma separated, default all
   -S, --Statuses statusList     Statuses, comma separated, default all

"""

import os
from collections import defaultdict

from DIRAC.Core.Base import Script
from DIRAC import S_OK, exit as dexit, gLogger

__RCSID__ = "$Id$"

def _translate(detail):
  """ Replace whizard naming convention by human conventions
  """
  detail = detail.replace('v','n1:n2:n3:N1:N2:N3')
  detail = detail.replace('qli','u:d:s:U:D:S')
  detail = detail.replace('ql','u:d:s:c:b:U:D:S:C:B')
  detail = detail.replace('q','u:d:s:c:b:t')
  detail = detail.replace('Q','U:D:S:C:B:T')
  detail = detail.replace('e1','e-')
  detail = detail.replace('E1','e+')
  detail = detail.replace('e2','mu-')
  detail = detail.replace('E2','mu+')
  detail = detail.replace('e3','tau-')
  detail = detail.replace('E3','tau+')
  detail = detail.replace('n1','nue')
  detail = detail.replace('N1','nueb')
  detail = detail.replace('n2','numu')
  detail = detail.replace('N2','numub')
  detail = detail.replace('n3','nutau')
  detail = detail.replace('N3','nutaub')
  detail = detail.replace('U','ubar')
  detail = detail.replace('C','cbar')
  detail = detail.replace('T','tbar')
  detail = detail.replace('tbareV','TeV')
  detail = detail.replace('D','dbar')
  detail = detail.replace('S','sbar')
  detail = detail.replace('B','bbar')
  detail = detail.replace('Z0','Z')
  detail = detail.replace('Z','Z0')
  detail = detail.replace('gghad','gamma gamma -> hadrons')
  detail = detail.replace(',','')
  detail = detail.replace('n N','nu nub')
  detail = detail.replace('se--','seL-')
  detail = detail.replace('se-+','seL+')
  detail = detail.replace(' -> ','->')
  detail = detail.replace('->',' -> ')
  detail = detail.replace(' H ->',', H ->')
  detail = detail.replace(' Z0 ->',', Z0 ->')
  detail = detail.replace(' W ->',', W ->')

  return detail

#def getAncestor(lfn):
#  from DIRAC.Resources.Catalog.FileCatalogClient import FileCatalogClient
#  fc = FileCatalogClient()
#  res = fc.getFileAncestors([lfn],1)
#  if not res['OK']:
#    return S_ERROR("Failed getting ancestor")
#  for ancestor in res['Value']['Successful'][lfn].keys():
#    if not ancestor.count("stdhep"):
#      res = getAncestor(ancestor)
#      if not res['OK']:
#        return S_ERROR("Failed geting ancestor")
#    else:
#      return S_OK(ancestor)

class _Params(object):
  """ CLI Parameters class
  """
  def __init__(self):
    """ Initialize
    """
    self.prod = []
    self.minprod = 0
    self.full_det = False
    self.verbose = False
    self.ptypes = ['MCGeneration','MCSimulation','MCReconstruction',"MCReconstruction_Overlay"]
    self.statuses = ['Active','Stopped','Completed','Archived']

  def setProdID(self, opt):
    """ Set the prodID to use. can be a range, a list, a unique value
    and a 'greater than' value
    """
    if opt.count(","):
      parts = opt.split(",")
    else:
      parts = [opt]
    prods = []
    for part in parts:
      if part.count("gt"):
        self.minprod = int(part.replace("gt",""))
        continue
      if part.count("-"):
        prods.extend(range(int(part.split("-")[0]), int(part.split("-")[1])+1))
      else:
        prods.append(int(part))
    self.prod = prods

    return S_OK()

  def setFullDetail(self,dummy_opt):
    """ Get every individual file's properties, makes this
    very very slow
    """
    self.full_det = True
    return S_OK()

  def setVerbose(self, dummy_opt):
    """ Extra printouts
    """
    self.verbose = True
    return S_OK()

  def setProdTypes(self, opt):
    """ The prod types to consider
    """
    self.ptypes = opt.split(",")
    return S_OK()

  def setStatuses(self, opt):
    ''' The prod statuses
    '''
    self.statuses = opt.split(",")
    return S_OK()

  def registerSwitch(self):
    """ Register all CLI switches
    """
    Script.registerSwitch("P:", "prods=", "Productions: greater than with gt1234, range with 32-56, list with 34,56", self.setProdID)
    Script.registerSwitch("p", "precise_detail", "Precise detail, slow", self.setFullDetail)
    Script.registerSwitch("v", "verbose", "Verbose output", self.setVerbose)
    Script.registerSwitch("t:", "types=", "Production Types, comma separated, default all", self.setProdTypes)
    Script.registerSwitch("S:", "Statuses=", "Statuses, comma separated, default all", self.setStatuses)
    Script.setUsageMessage( '\n'.join( [ __doc__.split( '\n' )[1],
                                         '\nUsage:',
                                         '  %s [option|cfgfile] ...\n' % Script.scriptName ] ) )


class ProductionSummary( object ):
  """ create production summary table """

  def __init__( self, clip ):
    from DIRAC.Resources.Catalog.FileCatalogClient import FileCatalogClient
    from DIRAC.TransformationSystem.Client.TransformationClient   import TransformationClient

    self.prod = clip.prod
    self.fullDetail = clip.full_det
    self.minprod = clip.minprod
    self.statuses = clip.statuses
    self.ptypes = clip.ptypes
    self.fcc = FileCatalogClient()
    self.trc = TransformationClient()
    
  def getProductionSummary( self ):
    """ create the production summary overview table """
    from ILCDIRAC.Core.Utilities.HTML                             import Table

    prodids = self.prod if self.prod else self._getProdIDs( )
    gLogger.info( "Will run on prods: %s" % prodids )

    if not prodids:
      return 1

    metadata = []

    for prodID in prodids:
      if prodID < self.minprod:
        continue
      self.getMetadata( metadata, prodID )

    detectors = {}
    detectors['ILD'] = {}
    corres = {"MCGeneration":'gen',"MCSimulation":'SIM',"MCReconstruction":"REC","MCReconstruction_Overlay":"REC"}
    detectors['ILD']['SIM'] = []
    detectors['ILD']['REC'] = []
    detectors['SID'] = {}
    detectors['SID']['SIM'] = []
    detectors['SID']['REC'] = []
    detectors['sid'] = {}
    detectors['sid']['SIM'] = []
    detectors['sid']['REC'] = []
    detectors['gen']=[]
    for channel in metadata:
      if 'DetectorType'  not in channel:
        detectors['gen'].append((channel['detail'],
                                 channel['Energy'],
                                 channel['ProdID'],
                                 channel['nb_files'],
                                 channel['NumberOfEvents']/channel['nb_files'],
                                 channel['NumberOfEvents'],
                                 channel['CrossSection'],str(channel['proddetail'])))
      else:
        if not channel['DetectorType'] in detectors:
          gLogger.error("This is unknown detector", channel['DetectorType'])
          continue
        detectors[channel['DetectorType']][corres[channel['prodtype']]].append((channel['detail'],
                                                                                channel['Energy'],
                                                                                channel['DetectorType'],
                                                                                channel['ProdID'],
                                                                                channel['nb_files'],
                                                                                channel['NumberOfEvents']/channel['nb_files'],
                                                                                channel['NumberOfEvents'],
                                                                                channel['CrossSection'],
                                                                                channel['MomProdID'],
                                                                                str(channel['proddetail'])))

    with open("tables.html","w") as of:
      of.write("""<!DOCTYPE html>
<html>
 <head>
<title> Production summary </title>
</head>
<body>
""")
      if len(detectors['gen']):
        of.write("<h1>gen prods</h1>\n")
        table = Table(header_row = ('Channel', 'Energy','ProdID','Tasks','Average Evts/task','Statistics','Cross Section (fb)','Comment'))
        for item in detectors['gen']:
          table.rows.append( item )
        of.write(str(table))
        gLogger.info("Gen prods")
        gLogger.info(str(table))

      if len(detectors['ILD']):
        of.write("<h1>ILD prods</h1>\n")
        for ptype in detectors['ILD'].keys():
          if len(detectors['ILD'][ptype]):
            of.write("<h2>%s</h2>\n"%ptype)
            table = Table(header_row = ('Channel', 'Energy','Detector','ProdID','Number of Files','Events/File','Statistics','Cross Section (fb)','Origin ProdID','Comment'))
            for item in detectors['ILD'][ptype]:
              table.rows.append( item )
            of.write(str(table))
            gLogger.info("ILC CDR prods %s" % ptype)
            gLogger.info(str(table))

      if len(detectors['SID']):
        of.write("<h1>SID prods</h1>\n")
        for ptype in detectors['SID'].keys():
          if len(detectors['SID'][ptype]):
            of.write("<h2>%s</h2>\n"%ptype)
            table = Table(header_row = ('Channel', 'Energy','Detector','ProdID','Number of Files','Events/File','Statistics','Cross Section (fb)','Origin ProdID','Comment'))
            for item in detectors['SID'][ptype]:
              table.rows.append( item )
            of.write(str(table))
            gLogger.info("SID CDR prods %s"%ptype)
            gLogger.info(str(table))

      if len(detectors['sid']):
        of.write("<h1>sid dbd prods</h1>\n")
        for ptype in detectors['sid'].keys():
          if len(detectors['sid'][ptype]):
            of.write("<h2>%s</h2>\n"%ptype)
            table = Table(header_row = ('Channel', 'Energy','Detector','ProdID','Number of Files','Events/File','Statistics','Cross Section (fb)','Origin ProdID','Comment'))
            for item in detectors['sid'][ptype]:
              table.rows.append( item )
            of.write(str(table))
            gLogger.info("sid DBD prods %s"%ptype)
            gLogger.info(str(table))

      of.write("""
</body>
</html>
""")
    gLogger.notice("Check ./tables.html in any browser for the results")
    dexit(0)

  def _getProdIDs( self ):
    """ get the production ids if none are given """
    prodids = []
    conddict = { 'Status': self.statuses }
    if self.ptypes:
      conddict['Type'] = self.ptypes
    res = self.trc.getTransformations( conddict )
    if res['OK']:
      for transfs in res['Value']:
        prodids.append( transfs['TransformationID'] )
    return prodids

  def getMetadata( self, metadata, prodID ):
    """ get metadata for production, append to metadata """
    meta = { 'ProdID': prodID }
    res = self.trc.getTransformation(str(prodID))
    if not res['OK']:
      gLogger.error("Error getting transformation %s" % prodID )
      return
    prodtype = res['Value']['Type']
    proddetail = res['Value']['Description']
    if prodtype == 'MCReconstruction' or prodtype == 'MCReconstruction_Overlay' :
      meta['Datatype']='DST'
    elif prodtype == 'MCGeneration':
      meta['Datatype']='gen'
    elif prodtype == 'MCSimulation':
      meta['Datatype']='SIM'
    elif prodtype in ['Split','Merge']:
      gLogger.warn("Invalid query for %s productions" % prodtype)
      return
    else:
      gLogger.error("Unknown production type %s"% prodtype)
      return
    res = self.fcc.findFilesByMetadata(meta)
    if not res['OK']:
      gLogger.error(res['Message'])
      return
    lfns = res['Value']
    nb_files = len(lfns)
    path = ""
    if not len(lfns):
      gLogger.warn("No files found for prod %s" % prodID)
      return
    path = os.path.dirname(lfns[0])
    res = self.fcc.getDirectoryUserMetadata(path)
    if not res['OK']:
      gLogger.warn('No meta data found for %s' % path)
      return
    dirmeta = {}
    dirmeta['proddetail'] = proddetail
    dirmeta['prodtype'] = prodtype
    dirmeta['nb_files']=nb_files
    dirmeta.update(res['Value'])
    lumi  = 0.
    nbevts = 0
    addinfo = None
    files = 0
    xsec = 0.0
    if not self.fullDetail:
      info = self._getFileInfo( lfns[0] )
      nbevts = info[1]*len(lfns)
      lumi = info[0]*len(lfns)
      addinfo = info[2]
      if 'xsection' in addinfo and 'sum' in addinfo['xsection'] and 'xsection' in addinfo['xsection']['sum']:
        xsec += addinfo['xsection']['sum']['xsection']
        files += 1
    else:
      for lfn in lfns:
        info = self._getFileInfo( lfn )
        lumi += info[0]
        nbevts += info[1]
        addinfo = info[2]
        if 'xsection' in addinfo and 'sum' in addinfo['xsection'] and 'xsection' in addinfo['xsection']['sum']:
          xsec += addinfo['xsection']['sum']['xsection']
          files += 1

    if not lumi:
      xsec, files = self.getXSecFromFilesMetadata( lfns )

    if xsec and files:
      xsec /= files
      dirmeta['CrossSection']=xsec
    else:
      dirmeta['CrossSection']=0.0

    if nbevts:
      dirmeta['NumberOfEvents']=nbevts

    #if not lumi:
    #  dirmeta['Luminosity']=0
    #  dirmeta['CrossSection']=0
    #else:
    #  if nbevts:
    #    dirmeta['CrossSection']=nbevts/lumi
    #  else:
    #    dirmeta['CrossSection']=0
    #if addinfo:
    #  if 'xsection' in addinfo:
    #    if 'sum' in addinfo['xsection']:
    #      if 'xsection' in addinfo['xsection']['sum']:
    #        dirmeta['CrossSection']=addinfo['xsection']['sum']['xsection']

    if 'NumberOfEvents' not in dirmeta:
      dirmeta['NumberOfEvents']=0
    #print processesdict[dirmeta['EvtType']]
    from ILCDIRAC.Core.Utilities.ProcessList                      import ProcessList
    from DIRAC import gConfig

    processlist = gConfig.getValue('/LocalSite/ProcessListPath')
    prl = ProcessList(processlist)
    processesdict = prl.getProcessesDict()

    dirmeta['detail']=''
    if dirmeta['EvtType'] not in processesdict:
      if 'Detail' in processesdict[dirmeta['EvtType']]:
        detail = processesdict[dirmeta['EvtType']]['Detail']

    else:
      detail=dirmeta['EvtType']


    if not prodtype == 'MCGeneration':
      res = self.trc.getTransformationInputDataQuery(str(prodID))
      if res['OK']:
        if 'ProdID' in res['Value']:
          dirmeta['MomProdID']=res['Value']['ProdID']
    if 'MomProdID' not in dirmeta:
      dirmeta['MomProdID']=0
    dirmeta['detail']= _translate(detail)

    metadata.append(dirmeta)

  def getXSecFromFilesMetadata( self, lfns ):
    xsec = 0
    files = 0
    depthDict = defaultdict( list )
    depSet = set()
    res = self.fcc.getFileAncestors( lfns, [1,2,3,4] )
    if not res['OK']:
      raise RuntimeError("Faild to get file ancestors: %s " % res['Message'] )

    temp_ancestorlist = []
    for _lfn,ancestorsDict in res['Value']['Successful'].iteritems():
      for ancestor,dep in ancestorsDict.items():
        if ancestor not in temp_ancestorlist:
          depthDict[dep].append(ancestor)
          depSet.add(dep)
          temp_ancestorlist.append(ancestor)
    depList = list(depSet)
    depList.sort()
    for ancestor in depthDict[depList[-1]]:
      info = self._getFileInfo(ancestor)
      addinfo = info[2]
      if 'xsection' in addinfo and 'sum' in addinfo['xsection'] and 'xsection' in addinfo['xsection']['sum']:
        xsec += addinfo['xsection']['sum']['xsection']
        files += 1

    return xsec, files

  def _getFileInfo(self, lfn):
    """ Retrieve the file info
    """
    from DIRAC.Core.Utilities import DEncode

    lumi = 0
    nbevts = 0
    res = self.fcc.getFileUserMetadata(lfn)
    if not res['OK']:
      gLogger.error("Failed to get metadata of %s" % lfn)
      return (0,0,{})
    if 'Luminosity' in res['Value']:
      lumi += float(res['Value']['Luminosity'])
    addinfo = {}
    if 'AdditionalInfo' in res['Value']:
      addinfo = res['Value']['AdditionalInfo']
      if addinfo.count("{"):
        addinfo = eval(addinfo)
      else:
        addinfo = DEncode.decode(addinfo)[0]
    if "NumberOfEvents" in res['Value']:
      nbevts += int(res['Value']['NumberOfEvents'])
    return (float(lumi),int(nbevts),addinfo)

if __name__=="__main__":
  CLIP = _Params()
  CLIP.registerSwitch()
  Script.parseCommandLine()
  PRODSUM = ProductionSummary( CLIP )
  RES = PRODSUM.getProductionSummary()
  exit( RES )

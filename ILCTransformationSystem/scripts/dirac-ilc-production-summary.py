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
from DIRAC.Core.Utilities import DEncode
from DIRAC import S_OK, gLogger

from ILCDIRAC.Core.Utilities.HTML import Table

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
    self.log = gLogger.getSubLogger( "ProdSum" )

  def getProductionSummary( self ):
    """ create the production summary overview table """

    prodids = self.prod if self.prod else self._getProdIDs( )
    self.log.info( "Will run on prods: %s" % prodids )

    if not prodids:
      return 1

    metadata = []

    for prodID in prodids:
      if prodID < self.minprod:
        continue
      self.getMetadata( metadata, prodID )

    detectors = {}
    detectors['ILD'] = {}
    corres = { "MCGeneration":'gen',
               "MCSimulation":'SIM',
               "MCReconstruction":"REC",
               "MCReconstruction_Overlay":"REC"
             }
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
      if 'DetectorType' not in channel:
        detectors['gen'].append((channel['detail'],
                                 channel['Energy'],
                                 channel['ProdID'],
                                 channel['nb_files'],
                                 channel['NumberOfEvents']/channel['nb_files'],
                                 channel['NumberOfEvents'],
                                 channel['CrossSection'],str(channel['proddetail'])))
      else:
        if channel['DetectorType'] not in detectors:
          self.log.error("This is unknown detector", channel['DetectorType'])
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

    self._createTable( detectors )

    return 0

  def _createTable( self, detectors ):
    """ create the html file and fill the table """
    with open("tables.html","w") as of:
      of.write("""<!DOCTYPE html>
<html>
 <head>
<title> Production summary </title>
</head>
<body>
""")
      self._writeGenInfo( of, detectors )
      self._writeILDInfo( of, detectors )
      self._writeSiDInfo( of, detectors )
      self._writeSIDDBDInfo( of, detectors )
      of.write("""
</body>
</html>
""")
    self.log.notice("Check ./tables.html in any browser for the results")


  def _writeGenInfo( self, of, detectors ):
    """ write info about generation productions to table """
    if not len(detectors['gen']):
      return
    of.write("<h1>gen prods</h1>\n")
    table = Table( header_row = ('Channel',
                                 'Energy',
                                 'ProdID',
                                 'Tasks',
                                 'Average Evts/task',
                                 'Statistics',
                                 'Cross Section (fb)',
                                 'Comment') )

    for item in detectors['gen']:
      table.rows.append( item )

    of.write( str(table) )
    self.log.info( "Gen prods" )
    self.log.info( str(table) )

  def _writeILDInfo( self, of, detectors ):
    """ write table info about ILD productions """
    if not len(detectors['ILD']):
      return

    of.write("<h1>ILD prods</h1>\n")
    for ptype in detectors['ILD']:
      if not len(detectors['ILD'][ptype]):
        continue
      of.write("<h2>%s</h2>\n"%ptype)
      table = Table(header_row = ('Channel',
                                  'Energy',
                                  'Detector',
                                  'ProdID',
                                  'Number of Files',
                                  'Events/File',
                                  'Statistics',
                                  'Cross Section (fb)',
                                  'Origin ProdID',
                                  'Comment'))
      for item in detectors['ILD'][ptype]:
        table.rows.append( item )
      of.write(str(table))
      self.log.info("ILC CDR prods %s" % ptype)
      self.log.info(str(table))

  def _writeSiDInfo( self, of, detectors ):
    """ write table info about SiD productions """
    if not len(detectors['SID']):
      return

    of.write("<h1>SID prods</h1>\n")
    for ptype in detectors['SID']:
      if not len(detectors['SID'][ptype]):
        continue
      of.write("<h2>%s</h2>\n"%ptype)
      table = Table(header_row = ('Channel',
                                  'Energy',
                                  'Detector',
                                  'ProdID',
                                  'Number of Files',
                                  'Events/File',
                                  'Statistics',
                                  'Cross Section (fb)',
                                  'Origin ProdID',
                                  'Comment'))
      for item in detectors['SID'][ptype]:
        table.rows.append( item )
      of.write(str(table))
      self.log.info("SID CDR prods %s"%ptype)
      self.log.info(str(table))

  def _writeSIDDBDInfo( self, of, detectors ):
    """ write table about sid dbd productions """
    if not len(detectors['sid']):
      return
    of.write("<h1>sid dbd prods</h1>\n")
    for ptype in detectors['sid']:
      if not len(detectors['sid'][ptype]):
        continue
      of.write("<h2>%s</h2>\n"%ptype)
      table = Table(header_row = ('Channel',
                                  'Energy',
                                  'Detector',
                                  'ProdID',
                                  'Number of Files',
                                  'Events/File',
                                  'Statistics',
                                  'Cross Section (fb)',
                                  'Origin ProdID',
                                  'Comment'))
      for item in detectors['sid'][ptype]:
        table.rows.append( item )
      of.write(str(table))
      self.log.info("sid DBD prods %s"%ptype)
      self.log.info(str(table))

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
    resTransInfo = self.trc.getTransformation( str(prodID) )
    if not resTransInfo['OK']:
      self.log.error("Error getting transformation %s" % prodID )
      return

    prodtype = resTransInfo['Value']['Type']

    meta['Datatype'] ={ 'MCReconstruction': 'DST',
                        'MCReconstruction_Overlay': 'DST',
                        'MCGeneration': 'gen',
                        'MCSimulation': 'SIM',
                        'Split': 'Invalid',
                        'Merge': 'Invalid',
                      }.get( prodtype, 'Unknown')

    if meta['Datatype'] in ('Invalid', 'Unknown'):
      self.log.error("%s production type: %s" % ( meta['Datatype'], prodtype ) )
      return

    resFiles = self.fcc.findFilesByMetadata(meta)
    if not resFiles['OK']:
      self.log.error( "Failed to find files by metadata", resFiles['Message'] )
      return
    lfns = resFiles['Value']
    nb_files = len(lfns)
    if not len(lfns):
      self.log.warn("No files found for prod %s" % prodID)
      return

    path = os.path.dirname(lfns[0])
    resDir = self.fcc.getDirectoryUserMetadata(path)
    if not resDir['OK']:
      self.log.warn('No meta data found for %s' % path)
      return

    dirmeta = {}
    dirmeta['proddetail'] = resTransInfo['Value']['Description']
    dirmeta['prodtype'] = prodtype
    dirmeta['nb_files']=nb_files
    dirmeta.update( resDir['Value'] )

    self.getXSecAndFiles( dirmeta, lfns )

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

    self.getProcessDetails( dirmeta )

    if prodtype != 'MCGeneration':
      resINQ = self.trc.getTransformationInputDataQuery(str(prodID))
      if resINQ['OK'] and 'ProdID' in resINQ['Value']:
        dirmeta['MomProdID']=resINQ['Value']['ProdID']

    if 'MomProdID' not in dirmeta:
      dirmeta['MomProdID']=0

    metadata.append(dirmeta)

  def getProcessDetails( self, dirmeta):
    """ get information about the process """
    self.log.info( "Getting process information" )
    #print processesdict[dirmeta['EvtType']]
    from ILCDIRAC.Core.Utilities.ProcessList import ProcessList
    from DIRAC import gConfig

    processlist = gConfig.getValue('/LocalSite/ProcessListPath')
    processesdict = ProcessList(processlist).getProcessesDict()

    if dirmeta['EvtType'] not in processesdict:
      if 'Detail' in processesdict[dirmeta['EvtType']]:
        detail = processesdict[dirmeta['EvtType']]['Detail']
    else:
      detail=dirmeta['EvtType']

    dirmeta['detail']= _translate(detail)

  def getXSecAndFiles( self, dirmeta, lfns ):
    """ get cross-section and number of files """
    lumi = 0.
    nbevts = 0
    addinfo = None
    files = 0
    xsec = 0.0
    for lfn in lfns:
      info = self._getFileInfo( lfn )
      lumi += info[0]
      nbevts += info[1]
      addinfo = info[2]
      if 'xsection' in addinfo and 'sum' in addinfo['xsection'] and 'xsection' in addinfo['xsection']['sum']:
        xsec += addinfo['xsection']['sum']['xsection']
        files += 1
      if not self.fullDetail:
        nbevts *= len(lfns)
        lumi *= len(lfns)
        break

    if not lumi:
      xsec, files = self.getXSecFromFilesMetadata( lfns )

    if xsec and files:
      xsec /= files
      dirmeta['CrossSection']=xsec
    else:
      dirmeta['CrossSection']=0.0

    if nbevts:
      dirmeta['NumberOfEvents']=nbevts


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

  def _getFileInfo( self, lfn ):
    """ Retrieve the file info
    """
    lumi = 0
    nbevts = 0
    res = self.fcc.getFileUserMetadata(lfn)
    if not res['OK']:
      self.log.error("Failed to get metadata of %s" % lfn)
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

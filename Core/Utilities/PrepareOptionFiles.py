# $HeadURL$
# $Id$
'''
ILCDIRAC.Core.Utilities.PrepareOptionFiles

This provides a set of methods to prepare the option files needed by the ILC applications.

Created on Jan 29, 2010

@author: Stephane Poss
'''
from xml.etree.ElementTree import ElementTree
from xml.etree.ElementTree import Element

def PrepareSteeringFile(inputSteering,outputSteering,detectormodel,stdhepFile,mac,nbOfRuns,startFrom,debug,outputlcio=None):
  """Writes out a steering file for Mokka
  
  Using specified parameters in the job definition passed from MokkaAnalysis
  
  @param inputSteering: input steering file name
  @type inputSteering: string
  @param outputSteering: new steering file that will be used by Mokka
  @type outputSteering: string
  @param detectormodel: detector model to use from the DB
  @type detectormodel: string
  @param stdhepFile: generator file name to put in the mac file, if needed
  @type stdhepFile: string
  @param mac: input mac file
  @type mac: string
  @param nbOfRuns: number of runs to use
  @type nbOfRuns: string
  @param startFrom: First event to read from the generator file
  @type startFrom: int
  @param debug: overwrite default print level, if set to True, don't change input steering parameter
  @type debug: bool
  @param outputlcio: output slcio file name, not used
  @type outputlcio: string
  
  @return True
  
  """
  macname = "mokkamac.mac"
  if len(mac)<1:
    macfile = file(macname,"w")
    if len(stdhepFile)>0:
      macfile.write("/generator/generator %s\n"%stdhepFile)
    macfile.write("/run/beamOn %s\n"%nbOfRuns)
    macfile.close()
  else:
    macname = mac
    
  input = file(inputSteering,"r")
  output = file(str(outputSteering),"w")
  for line in input:
    if line.find("/Mokka/init/initialMacroFile")<0:
      if line.find("/Mokka/init/BatchMode")<0:
        if outputlcio:
          if line.find("lcioFilename")<0:
            #if line.find("#")>1:
              if detectormodel:
                if line.find("/Mokka/init/detectorModel")<0:
                  output.write(line)
                else:
                  output.write(line)
              else:
                output.write(line)
        else:
          #if line.find("#")==1:
            if detectormodel:
              if line.find("/Mokka/init/detectorModel")<0:
                output.write(line)
            else:
              output.write(line)
  if detectormodel:
    output.write("/Mokka/init/detectorModel %s\n"%detectormodel)
  
  if not debug:
    output.write("/Mokka/init/printLevel 0\n")

  output.write("/Mokka/init/BatchMode true\n")
  output.write("/Mokka/init/initialMacroFile %s\n"%macname)
  if outputlcio:
    output.write("/Mokka/init/lcioFilename %s\n"%outputlcio)
  output.write("/Mokka/init/startEventNumber %d"%startFrom)
  output.close()
  return True

def PrepareXMLFile(finalxml,inputXML,inputGEAR,inputSLCIO,numberofevts,debug):
  """Write out a xml file for Marlin
  
  Takes in input the specified job parameters for Marlin application given from MarlinAnalysis
  
  @param finalxml: name of the xml file that will be used by Marlin
  @type finalxml: string
  @param inputXML: name of the provided input XML file
  @type inputXML: string
  @param inputSLCIO: input slcio file list
  @type inputSLCIO: list of strings
  @param numberofevts: number of events to process
  @type numberofevts: int
  @param debug: set to True to use given mode, otherwise set verbosity to SILENT
  @type debug: bool
  @return: True
  
  """
  tree = ElementTree()
  tree.parse(inputXML)
  params = tree.findall('global/parameter')
  for param in params:
    if param.attrib.has_key('name'):
      if param.attrib['name']=='LCIOInputFiles':
        param.text = inputSLCIO
      if len(numberofevts)>0:
        if param.attrib['name']=='MaxRecordNumber':
          if param.attrib.has_key('value'):
            param.attrib['value'] = numberofevts
      if param.attrib['name']=="GearXMLFile":
        if param.attrib.has_key('value'):
          param.attrib['value'] = inputGEAR
      if not debug:
        if param.attrib['name']=='Verbosity':
          param.text = "SILENT"

  #outxml = file(finalxml,'w')
  #inputxml = file(inputXML,"r")
  #for line in inputxml:
    #if line.find("<!--")<0:
  #  if line.find("LCIOInputFiles")<0:
  #    outxml.write(line)
  #  else:
  #    outxml.write('<parameter name="LCIOInputFiles"> %s </parameter>\n'%inputSLCIO)
  #outxml.close()
  tree.write(finalxml)
  return True

def PrepareMacFile(inputmac,outputmac,stdhep,nbevts,startfrom,detector=None,outputlcio=None):
  """Writes out a mac file for SLIC
  
  Takes the parameters passed from SLICAnalysis to define a new mac file if none was provided
  
  @param inputmac: name of the specified mac file
  @type inputmac: string
  @param outputmac: name of the final mac file used by SLIC
  @type outputmac: string
  @param stdhep: name of the generator file to use
  @type stdhep: string
  @param nbevts: number of events to process
  @type nbevts: string
  @param startfrom: event nu,ber to start from in the generator file
  @type startfrom: string
  @param detector: Detector model to use.  
  @type detector: string
  @param outputlcio: name of the produced output slcio file, this is useful when combined with setOutputData of ILCJob class
  @type outputlcio: string

  @return: True
  """
  inputmacfile = file(inputmac,'r')
  output = file(outputmac,'w')
  for line in inputmacfile:
    if line.find("/generator/filename")<0:
      if line.find("/generator/skipEvents")<0:
        if line.find("/run/beamOn")<0:
          if detector:
            if line.find("/lcdd/url")< 0:
              if outputlcio:
                if line.find("/lcio/filename")<0:
                  output.write(line)
              else:
                output.write(line)
          else :
            if outputlcio:
              if line.find("/lcio/filename")<0:
                output.write(line)
            else:
              output.write(line)
        
  if detector:
    output.write("/lcdd/url %s.lcdd\n"%detector)
  if outputlcio:
    output.write("/lcio/filename %s\n"%outputlcio)
  output.write("/generator/filename %s\n"%stdhep)
  output.write("/generator/skipEvents %s\n"%startfrom)
  output.write("/run/beamOn %s\n"%nbevts)
  inputmacfile.close()
  output.close()
  return True

def PrepareLCSIMFile(inputlcsim,outputlcsim,inputslcio,jars=None,debug=False):
  """Writes out a lcsim file for LCSIM
  
  Takes the parameters passed from LCSIMAnalysis
  
  @param inputlcsim: name of the provided lcsim
  @type inputlcsim: string
  @param outputlcsim: name of the lcsim file on which LCSIM is going to run, defined in LCSIMAnalysis
  @type outputlcsim: string
  @param inputslcio: list of slcio files on which LCSIM should run
  @type inputslcio: list of string
  @param jars: list of jar files that should be added in the classpath definition
  @type jars: list of strings
  @param debug: By default set verbosity to true
  @type debug: bool
  
  @return: True
  """
  tree = ElementTree()
  tree.parse(inputlcsim)
  ##handle the input slcio file list
  filesinlcsim = tree.find("inputFiles")
  if filesinlcsim:
    filesinlcsim.clear()
  else:
    baseelem = tree.find("lcsim")
    filesinlcsim = Element("inputFiles")
    baseelem.append(filesinlcsim)
  set = Element("fileSet")
  for slcio in inputslcio:
    newfile = Element('file')
    newfile.text = slcio
    set.append(newfile)
  filesinlcsim.append(set)

  if jars:
    if len(jars)>0:
      classpath = tree.find("classpath")
      if classpath:
        classpath.clear()
      else:
        baseelem = tree.find("lcsim")
        classpath = Element("classpath")    
        baseelem.append(classpath)
      for jar in jars:
        newjar = Element("jar")
        newjar.text = jar
        classpath.append(newjar)
        
  #handle verbosity
  if debug:
    debugline = tree.find("verbose")
    if debugline :
      debugline.text = 'true'
    else:
      control = tree.find('control')
      debugelem = Element('verbose')
      debugelem.text = 'true'
      control.append(debugelem)        
      
  tree.write(outputlcsim)
  return True
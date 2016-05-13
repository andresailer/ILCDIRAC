"""
Unit tests for the MarlinAnalysis.py file
"""

import unittest
import os
from mock import mock_open, patch, MagicMock as Mock
from ILCDIRAC.Workflow.Modules.MarlinAnalysis import MarlinAnalysis
from ILCDIRAC.Tests.Utilities.GeneralUtils import assertInImproved
from DIRAC import S_OK, S_ERROR

# TODO: add case for undefined steering file
class MarlinAnalysisTestCase( unittest.TestCase ):
  """ Base class for the ProductionJob test cases
  """

  def setUp(self):
    """set up the objects"""
    self.marAna = MarlinAnalysis()
    self.marAna.OutputFile = ""

  def tearDown(self):
    del self.marAna


  def test_resolveinput_productionjob1( self ):
    self.marAna.workflow_commons[ "IS_PROD" ] = True
    outputfile1 = "/dir/a_REC_.a"
    outputfile2 = "/otherdir/b_DST_.b"
    inputfile = "/inputdir/input_SIM_.i"
    self.marAna.workflow_commons[ "ProductionOutputData" ] = ";".join([outputfile1, outputfile2, inputfile])
    self.assertEquals(S_OK("Parameters resolved"), self.marAna.applicationSpecificInputs())
    self.assertEquals((self.marAna.outputREC, self.marAna.outputDST, self.marAna.InputFile), ("a_REC_.a", "b_DST_.b", ["input_SIM_.i"]))

  def test_resolveinput_productionjob2( self ):
    self.marAna.workflow_commons[ "IS_PROD" ] = False
    self.marAna.workflow_commons[ "PRODUCTION_ID" ] = "123"
    self.marAna.workflow_commons[ "JOB_ID" ] = 456
    
    self.assertEquals(S_OK("Parameters resolved"), self.marAna.applicationSpecificInputs())
    self.assertFalse(self.marAna.InputFile or self.marAna.InputData)

    
  def test_resolveinput_productionjob3( self ):
    self.marAna.workflow_commons[ "IS_PROD" ] = True

    self.marAna.OutputFile = "c.c"
    self.marAna.InputFile = []
    inputlist = ["a.slcio", "b.slcio", "c.exe"]
    self.marAna.InputData = inputlist
    
    self.assertEquals(S_OK("Parameters resolved"), self.marAna.applicationSpecificInputs())
    self.assertEquals([inputlist[0], inputlist[1]], self.marAna.InputFile)
    
  def test_resolveinput_productionjob4( self ):
    self.marAna.workflow_commons[ "IS_PROD" ] = True
    self.marAna.OutputFile = ''
    prodId = "123"
    self.marAna.workflow_commons[ "PRODUCTION_ID" ] = prodId
    jobId = "456"
    self.marAna.workflow_commons[ "JOB_ID" ] = jobId
    self.marAna.workflow_commons.pop('ProductionOutputData', None) #default value needed, else maybe KeyError
    self.marAna.InputFile = 'in3.slcio'
    self.marAna.outputREC = 'out1.stdhep'
    self.marAna.outputDST = 'test2.stdhep'
    
    self.assertEquals(S_OK("Parameters resolved"), self.marAna.applicationSpecificInputs())
    files = [self.marAna.outputREC, self.marAna.outputDST, self.marAna.InputFile[0]]
    for filename in files:
      # TODO: check for file extension, differentiate 'test'/'test2' in filename...
      self.assertInMultiple([prodId,jobId], filename)
    self.assertInMultiple(['in3', '.slcio'], self.marAna.InputFile[0])
    self.assertInMultiple(['out1', '.stdhep'], self.marAna.outputREC)
    self.assertInMultiple(['test2', '.stdhep'], self.marAna.outputDST)
      
  def test_runit_noplatform( self ):
    self.marAna.platform = None
    result = self.marAna.runIt()
    self.assertFalse( result['OK'] )
    assertInImproved('no ilc platform selected', result['Message'].lower(), self)

  def test_runit_noapplog( self ):
    self.marAna.platform = "Testplatform123"
    self.marAna.applicationLog = None
    result = self.marAna.runIt()
    self.assertFalse( result['OK'] )
    assertInImproved('no log', result['Message'].lower(), self)

  def test_runit_workflowbad( self ):
    self.marAna.platform = "Testplatform123"
    self.marAna.applicationLog = "testlog123"
    self.marAna.workflowStatus = { 'OK' : False }
    result = self.marAna.runIt()
    self.assertTrue(result['OK'])
    assertInImproved("should not proceed", result['Value'].lower(), self)

  def test_runit_stepbad( self ):
    self.marAna.platform = "Testplatform123"
    self.marAna.applicationLog = "testlog123"
    self.marAna.stepStatus = { 'OK' : False }
    result = self.marAna.runIt()
    self.assertTrue(result['OK'])
    assertInImproved("should not proceed", result['Value'].lower(), self)

  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.getEnvironmentScript", new=Mock(return_value=S_ERROR("failed to get env script")))
  def test_runit_getEnvScriptFails( self ):
    self.marAna.platform = "Testplatform123"
    self.marAna.applicationLog = "testlog123"
    self.marAna.stepStatus = S_OK()
    self.marAna.workflowStatus = S_OK()
    result = self.marAna.runIt()
    self.assertFalse( result['OK'] )
    msg = result['Message'].lower()
    assertInImproved('env script', msg, self)

  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.getEnvironmentScript", new=Mock(return_value=S_OK('Testpath123')))
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.MarlinAnalysis.GetInputFiles", new=Mock(return_value=S_ERROR('missing slcio file')))
  def test_runit_getInputFilesFails( self ):
    self.marAna.platform = "Testplatform123"
    self.marAna.applicationLog = "testlog123"
    self.marAna.stepStatus = S_OK()
    self.marAna.workflowStatus = S_OK()
    result = self.marAna.runIt()
    self.assertFalse( result['OK'] )
    #Only checks that the patch annotation is passed as the result
    assertInImproved('missing slcio file', result['Message'].lower(), self)

  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.getEnvironmentScript", new=Mock(return_value=S_OK('Testpath123')))
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.MarlinAnalysis.GetInputFiles", new=Mock(return_value=S_OK("testinputfiles")))
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.getSteeringFileDirName", new=Mock(return_value=S_OK('testdir')))
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.os.path.exists", new=Mock(side_effect=[False, True, False, True, False, True, False, False]))
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.prepareXMLFile", new=Mock(return_value=S_OK('testdir')))
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.MarlinAnalysis.prepareMARLIN_DLL", new=Mock(return_value=S_OK('testdir')))
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.MarlinAnalysis.runMarlin", new=Mock(return_value=S_OK('testdir')))
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.shutil.copy")
  def test_runit_handlepandorasettings_no_log( self, mock_copy ):
    self.marAna.platform = "Testplatform123"
    self.marAna.applicationLog = "testlog123"
    self.marAna.stepStatus = S_OK()
    self.marAna.workflowStatus = S_OK()
    result = self.marAna.runIt()
    self.assertFalse(result['OK'])
    assertInImproved('not produce the expected log', result['Message'].lower(), self)
    mock_copy.assert_called_with('testdir/PandoraSettings.xml', '%s/PandoraSettings.xml' % os.getcwd())

  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.getEnvironmentScript", new=Mock(return_value=S_OK('Testpath123')))
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.MarlinAnalysis.GetInputFiles", new=Mock(return_value=S_OK("testinputfiles")))
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.getSteeringFileDirName", new=Mock(return_value=S_OK('testdir')))
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.os.path.exists", new=Mock(side_effect=[False, True, False, True, False, True, False]))
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.shutil.copy", new=Mock())
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.prepareXMLFile", new=Mock(return_value=S_ERROR('prepxml')))
  def test_runit_xmlgenerationfails( self ):
    self.marAna.platform = "Testplatform123"
    self.marAna.applicationLog = "testlog123"
    self.marAna.stepStatus = S_OK()
    self.marAna.workflowStatus = S_OK()
    result = self.marAna.runIt()
    self.assertFalse(result['OK'])
    assertInImproved('prepxml', result['Message'].lower(), self)

  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.getEnvironmentScript", new=Mock(return_value=S_OK('Testpath123')))
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.MarlinAnalysis.GetInputFiles", new=Mock(return_value=S_OK("testinputfiles")))
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.getSteeringFileDirName", new=Mock(return_value=S_OK('testdir')))
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.os.path.exists", new=Mock(side_effect=[False, True, False, True, False, True, False]))
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.shutil.copy", new=Mock())
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.prepareXMLFile", new=Mock(return_value=S_OK('testdir')))
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.MarlinAnalysis.prepareMARLIN_DLL", new=Mock(return_value=S_ERROR('mardll')))
  def test_runit_marlindllfails( self ):
    self.marAna.platform = "Testplatform123"
    self.marAna.applicationLog = "testlog123"
    self.marAna.stepStatus = S_OK()
    self.marAna.workflowStatus = S_OK()
    result = self.marAna.runIt()
    self.assertFalse(result['OK'])
    assertInImproved('wrong with software installation', result['Message'].lower(), self)

  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.getEnvironmentScript", new=Mock(return_value=S_OK('Testpath123')))
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.MarlinAnalysis.GetInputFiles", new=Mock(return_value=S_OK("testinputfiles")))
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.getSteeringFileDirName", new=Mock(return_value=S_OK('testdir')))
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.os.path.exists", new=Mock(side_effect=[False, True, False, True, False, True, False]))
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.prepareXMLFile", new=Mock(return_value=S_OK('testdir')))
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.MarlinAnalysis.prepareMARLIN_DLL", new=Mock(return_value=S_OK('testdir')))
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.MarlinAnalysis.runMarlin", new=Mock(return_value=S_ERROR('marlin failed')))
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.shutil.copy")
  def test_runit_runmarlinfails( self, mock_copy ):
    self.marAna.platform = "Testplatform123"
    self.marAna.applicationLog = "testlog123"
    self.marAna.stepStatus = S_OK()
    self.marAna.workflowStatus = S_OK()
    result = self.marAna.runIt()
    self.assertFalse(result['OK'])
    assertInImproved('failed to run', result['Message'].lower(), self)
    mock_copy.assert_called_with('testdir/PandoraSettings.xml', '%s/PandoraSettings.xml' % os.getcwd())


  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.getEnvironmentScript", new=Mock(return_value=S_OK('Testpath123')))
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.MarlinAnalysis.GetInputFiles", new=Mock(return_value=S_OK("testinputfiles")))
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.getSteeringFileDirName", new=Mock(return_value=S_OK('testdir')))
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.os.path.exists", new=Mock(side_effect=[False, True, False, True, True, True, True, True]))
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.prepareXMLFile", new=Mock(return_value=S_OK('testdir')))
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.MarlinAnalysis.prepareMARLIN_DLL", new=Mock(return_value=S_OK('testdir')))
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.MarlinAnalysis.runMarlin", new=Mock(return_value=S_OK([""])))
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.shutil.copy")
  def test_runit_complete( self, mock_copy ):
    self.marAna.platform = "Testplatform123"
    self.marAna.applicationLog = "testlog123"
    self.marAna.stepStatus = S_OK()
    self.marAna.workflowStatus = S_OK()
    result = self.marAna.runIt()
    self.assertTrue(result['OK'])
    mock_copy.assert_called_with('testdir/PandoraSettings.xml', '%s/PandoraSettings.xml' % os.getcwd())


  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.getSoftwareFolder", new=Mock(return_value=S_ERROR('')))
  def test_getenvscript_getsoftwarefolderfails( self ):
    self.assertFalse(self.marAna.getEnvScript(None, None, None)['OK'])

  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.getSoftwareFolder", new=Mock(return_value=S_OK('')))
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.removeLibc", new=Mock(return_value=None))
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.getNewLDLibs", new=Mock(return_value=None))
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.os.path.exists", new=Mock(return_value=False))
  def test_getenvscript_pathexists( self ):
    result = self.marAna.getEnvScript(None, None, None)
    self.assertFalse(result['OK'])
    assertInImproved('marlin_dll folder not found', result['Message'].lower(), self)

  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.getSoftwareFolder", new=Mock(return_value=S_OK('aFolder')))
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.removeLibc", new=Mock(return_value=None))
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.getNewLDLibs", new=Mock(return_value='bFolder'))
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.os.path.exists", new=Mock(return_value=True))
  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.os.listdir", new=Mock(return_value=['testdir']))
  def test_getenvscript( self ):
    moduleName = "ILCDIRAC.Workflow.Modules.MarlinAnalysis"
    file_contents = []
    text_file_data = '\n'.join(file_contents)
    result = {}
    with patch('%s.open' % moduleName, mock_open(read_data=text_file_data), create=True) as file_mocker:
      result = self.marAna.getEnvScript(None, None, None)
    self.assertTrue(result['OK'])
    assertInImproved('/MarlinEnv.sh', result['Value'], self)
    check_in_script = [ 'declare -x PATH=aFolder/Executable:$PATH\n', 'declare -x ROOTSYS=aFolder/ROOT\n', 'declare -x LD_LIBRARY_PATH=$ROOTSYS/lib:aFolder/LDLibs:bFolder\n', "declare -x MARLIN_DLL=aFolder/MARLIN_DLL/testdir:\n", "declare -x PANDORASETTINGS=aFolder/Settings/PandoraSettings.xml" ]
    file_mocker.assert_called_with('MarlinEnv.sh', 'w')
    mocker_handle = file_mocker()
    print mocker_handle.write.mock_calls
    for expected in check_in_script:
      mocker_handle.write.assert_any_call(expected)
    self.assertEquals(len(check_in_script), mocker_handle.__enter__.return_value.write.call_count - 4)

  def test_getinputfiles_ignore( self ):
    self.marAna.ignoremissingInput = True
    self.assertTrue(self.marAna.GetInputFiles()['OK'])

  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.resolveIFpaths", new=Mock(return_value=S_ERROR()))
  def test_getinputfiles_resolvepathsfails( self ):
    res = self.marAna.GetInputFiles()
    self.assertFalse(res['OK'])
    assertInImproved('missing slcio', res['Message'].lower(), self)

  @patch("ILCDIRAC.Workflow.Modules.MarlinAnalysis.resolveIFpaths", new=Mock(return_value=S_OK(['1.slcio', '2.slcio'])))
  def test_getinputfiles_complete( self ):
    res = self.marAna.GetInputFiles()
    self.assertTrue(res['OK'])
    print res['Value']

  def assertInMultiple( self, listOfStrings, bigString):
    """Checks if every string in listOfStrings is contained in bigString.
    """
    for string in listOfStrings:
      assertInImproved(string, bigString, self)

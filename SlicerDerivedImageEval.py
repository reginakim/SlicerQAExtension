#! /usr/bin/env python

import os
import sqlite3
import warnings
from __main__ import ctk
from __main__ import qt
from __main__ import slicer
from __main__ import vtk

import module_locator
# import database_helper

globals()['__file__'] = module_locator.module_path()

#
# SlicerDerivedImageEval
#

class SlicerDerivedImageEval:
    def __init__(self, parent):
        parent.title = 'Image Evaluation'
        parent.categories = ['Work in Progress']
        parent.dependencies = []
        parent.contributors = ['Dave Welch (UIowa), Hans Johnson (UIowa)']
        parent.helpText = """Image evaluation module for use in the UIowa PINC lab"""
        parent.acknowledgementText = """ """
        self.parent = parent

#
# qSlicerDerivedImageEvalWidget
#

class SlicerDerivedImageEvalWidget:
    def __init__(self, parent=None):
        # Register the regions and QA values
        self.regions = ['accumben_right', 'accumben_left',
                        'caudate_right', 'caudate_left',
                        'globus_right', 'globus_left',
                        'hippocampus_right', 'hippocampus_left',
                        'putamen_right', 'putamen_left',
                        'thalamus_right', 'thalamus_left']
        self.qaValues = {'good':1, 'bad':0}
        self.currentSession = None
        self.sessionQLabel = None
        self.evalFrame = None
        # Set up the logic
        self.logic = SlicerDerivedImageEvalLogic()
        # Handle the UI display with/without Slicer
        if parent is None:
            self.parent = slicer.qMRMLWidget()
            self.parent.setLayout(qt.QVBoxLayout())
            self.parent.setMRMLScene(slicer.mrmlScene)
            self.layout = self.parent.layout()
            self.setup()
            self.parent.show()
        else:
            self.parent = parent
            self.layout = self.parent.layout()

    def loadUIFile(self):
        """ Load in the Qt Designer file """
        uiloader = qt.QUiLoader()
        qfile = qt.QFile(os.path.join(__file__, 'Resources/UI/evaluationPrototype.ui'))
        qfile.open(qt.QFile.ReadOnly)
        try:
            self.evalFrame = uiloader.load(qfile)
        finally:
            qfile.close()

    def connectRegionButtons(self):
        """ Map the region buttons clicked() signals to the function """
        self.buttonMapper = qt.QSignalMapper()
        self.buttonMapper.connect('mapped(const QString&)', self.selectRegion)
        self.buttonMapper.connect('mapped(const QString&)', self.enableRadios)
        for region in self.regions:
            self.pushButtons[region] = self.evaluationCollapsibleButton.findChild('QPushButton', region)
            self.buttonMapper.setMapping(self.pushButton[region], region)
            self.pushButtons[region].connect('clicked()', self.buttonMapper, 'map()')

    def connectSessionButtons(self):
        self.nextSessionButton = self.evaluationCollapsibleButton.findChild('QPushButton', 'nextSessionButton')
        self.nextSessionButton.connect('clicked()', self.onNextButtonClicked)
        self.previousSessionButton = self.evaluationCollapsibleButton.findChild('QPushButton', 'previousSessionButton')
        self.nextSessionButton.connect('clicked()', self.onNextButtonClicked)

    def connectRadioButtons(self):
        """ Map the radio buttons """
        self.radioMapper = qt.QSignalMapper()
        self.radioMapper.connect('mapped(const QString&)', self.selectValue)
        # Get radios in UI file
        self.radios = self.evaluationCollapsibleButton.findChildren('QRadioButton')
        for button in self.radios:
            self.radioMapper.setMapping(button, button.objectName)
            button.connect('checked()', self.radioMapper, 'map()')
            button.setEnabled(False)
            print button.objectName

    def setup(self):
        self.loadUIFile()
        # Evaluation subsection
        self.evaluationCollapsibleButton = ctk.ctkCollapsibleButton()
        self.evaluationCollapsibleButton.text = 'Evaluation input'
        self.evaluationCollapsibleButton.setLayout(self.evalFrame.findChild('QVBoxLayout'))
        self.layout.addWidget(self.evaluationCollapsibleButton)
        # Connect push buttons
        self.connectSessionButtons()
        self.connectRegionButtons()
        self.connectRadioButtons()
        # Add vertical spacer
        self.layout.addStretch(1)
        # Get data and update label
        self.logic.onGetBatchFilesClicked() # TODO: make a button for this!
        # Get session label button
        self.sessionQLabel = self.evaluationCollapsibleButton.findChild('QLabel', 'sessionBoxedLabel')
        self.sessionQLabel.setText(self.logic.currentSession)
        self.sessionQLabel.update()
        # Set local var as instance attribute
        # self.batchFilesButton = batchFilesButton

    # def onBatchFilesButtonClicked(self):
    #     print "Batch file button clicked..."
    #     fileList = self.logic.batchList

    def constructLabelNodeName(self, buttonName):
        """ Create the names for the volume and label nodes """
        if buttonName.find('left') > -1:
            nodeName = '_'.join([buttonName, 'left', self.sessionLabel.text])
        elif buttonName.find('right') > -1:
            nodeName = '_'.join([buttonName, 'right', self.sessionLabel.text])
        else:
            nodeName = '_'.join([buttonName, self.sessionLabel.text])
        return nodeName

    def constructRadioButtonNames(self, buttonName):
        """ Construct the radio button names, given the region push button name """
        goodName = '_'.join([buttonName, 'good'])
        badName = '_'.join([buttonName, 'bad'])
        return goodName, badName

    def selectRegion(self, buttonName):
        """  """
        nodeName = self.constructLabelNodeName(buttonName)
        labelNode = slicer.util.getNode(nodeName)
        # Set the scene
        compositeNodes = slicer.util.getNodes('vtkMRMLSliceCompositeNode*')
        for compositeNode in compositeNodes.values():
            compositeNode.SetLabelVolumeID(labelNode.GetID())
            compositeNode.SetLabelOpacity(1.0)
        # Set the label outline to ON
        sliceNodes = slicer.util.getNodes('vtkMRMLSliceNode*')
        for sliceNode in sliceNodes.values():
            sliceNode.UseLabelOutlineOn()

    def enableRadios(self, buttonName):
        goodName, badName = self.constructRadioButtonNames(buttonName)
        goodRadio = self.evaluationCollapsibleButton.findChild('QRadioButton', goodName)
        badRadio = self.evaluationCollapsibleButton.findChild('QRadioButton', badName)
        goodRadio.setEnabled(True)
        badRadio.setEnabled(True)

    def selectValue(self, buttonName):
        if buttonName.find('good') > -1:
            print "Value is 1 for %s" % buttonName
        elif buttonName.find('bad') > -1:
            print "Value is 0 for %s" % buttonName
        else:
            raise Exception("Unknown radio button name %s" % buttonName)

    def onNextButtonClicked(self):
        if self.writeReviewToDatabase():
            self.logic.onNextButtonClicked()
            self.sessionLabel.text = self.logic.currentSession
            self.sessionLabel.update()

    def onPreviousButtonClicked(self):
        if self.writeReviewToDatabase():
            self.logic.onPreviousButtonClicked()
            self.sessionLabel.text = self.logic.currentSession
            self.sessionLabel.update()

    def writeReviewToDatabase(self):
        valueDict = {}
        for radio in self.radios:
            if radio.objectName.find('good') > -1 and radio.isChecked():
                value = 1
            else:
                value = 0
            elements = radio.objectName.split('_')
            region = '_'.join(elements[:-1])
            valueDict[region] = value
            self.logic.writeAndUnlockRecord(valueDict)
            # self.cursor.execute("UPDATE derived_images \
            #                      SET status='reviewed' \
            #                      WHERE session=?", (self.sessionLabel.text,))
            # record_id = self.cursor.execute("SELECT record_id \
            #                                  FROM derived_images \
            #                                  WHERE session=?", (self.sessionLabel.text,))
            # self.cursor.execute("UPDATE image_reviews \
            #                      SET ?=? SET user_id=? \
            #                      WHERE record_id=?", (region, value, self.user_id, record_id))
        return True

    def onReload(self, moduleName="SlicerDerivedImageEval"):
        """ ============ DEVELOPMENT TOOL =============
            Generic development reload method for any scripted module.
            ModuleWizard will subsitute correct default moduleName.
        """
        import imp
        import os
        import sys
        import slicer
        widgetName = moduleName + "Widget"
        # reload the source code
        # - set source file path
        # - load the module to the global space
        if not '__file__' in locals():
            __file__ = os.path.join(os.getcwd(), 'SlicerDerivedImageEval.py')
            print "__file__ (2) = %s" % __file__
        # TODO: Find a method to get the __file__ for THIS script, NOT the factory generated one! (see Pieper's below)
        filePath = eval('slicer.modules.%s.path' % moduleName.lower())
        p = os.path.dirname(filePath)
        if not sys.path.__contains__(p):
            sys.path.insert(0, p)
        fp = open(filePath, "r")
        globals()[moduleName] = imp.load_module(moduleName, fp, filePath,
                                                ('.py', 'r', imp.PY_SOURCE))
        fp.close()
        # rebuild the widget
        # - find and hide the existing widget
        # - create a new widget in the existing parent
        parent = slicer.util.findChildren(name='%s Reload' % moduleName)[0].parent()
        for child in parent.children():
            try:
                child.hide()
            except AttributeError:
                pass
        globals()[widgetName.lower()] = eval('globals()["%s"].%s(parent)' %
                                             (moduleName, widgetName))
        globals()[widgetName.lower()].setup()


class SlicerDerivedImageEvalLogic(object):
    """ Logic class to be used 'under the hood' of the evaluator """
    def __init__(self):
        self.user_id = os.environ['USER']
        self.testing = False
        self.database = None
        self.experiment = None
        self.batchList = None
        self.batchSize = 1
        self.batchRows = None
        #  self.testingData()
        self.count = 0 # Starting value
        self.currentSession = None
        self.currentRecordID = None
        # self.onGetBatchFilesClicked() # TESTING

    def onGetBatchFilesClicked(self):
        import os
        self.database = os.path.join(__file__, 'Testing', 'sqlTest.db')
        self._getLockedFileList()

    #========= TODO: move the database code to a helper file =========
    def openDatabase(self):
        self.connection = sqlite3.connect(self.database, isolation_level="EXCLUSIVE")
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()
        self.cursor.arraysize = self.batchSize

    def getBatch(self):
        # Get batch
        self.cursor.execute("SELECT * \
                            FROM derived_images \
                            WHERE status = 'unreviewed'")
        rows = self.cursor.fetchmany()
        if not rows:
            raise warnings.warn("No rows were status == 'unreviewed' were found!")
        return rows

    def lockBatch(self, rows):
        # Lock batch members
        ids = ()
        idString = ""
        for row in rows:
            ids = ids + (row['record_id'],)
            idString += "?,"
        idString = idString[:-1]
        self.cursor.execute("UPDATE derived_images \
                             SET status='locked' \
                             WHERE record_id IN ({0})".format(idString), ids)
        self.cursor.connection.commit()
        # return ids

    def lockAndReadRecords(self):
        self.openDatabase()
        try:
            rows = self.getBatch()
            #ids = self.lockBatch(rows)
            self.lockBatch(rows)
        finally:
            self.connection.close()
        return rows

    def writeAndUnlockRecord(self, valueDict):
        self.openDatabase()
        ID = (self.batchRows[self.count]['record_id'],)
        try:
            for region in valueDict:
                thisTuple = ()
                thisTuple = (region,) + ID + (self.user_id, valueDict[region])
                print thisTuple
                self.cursor.execute("INSERT INTO image_reviews (record_id, user_id, ?)\
                                     VALUES (?, ?, ?)", thisTuple)
            # self.cursor.execute("UPDATE image_reviews \
            #                      SET caudateRight=?, caudateLeft=?, \
            #                      hippocampusRight=?, hippocampusLeft=?, \
            #                      putamenRight=?, putamenLeft=?, \
            #                      thalamusRight=?, thalamusLeft=? \
            #                      WHERE record_id=?", thisTuple)
            self.cursor.execute("UPDATE derived_images \
                                 SET status='reviewed' \
                                 SET user_id=? \
                                 WHERE record_id=? AND status='locked'", (self.user_id,) + ID)
            self.cursor.commit()
        finally:
            self.connection.close()
    # ========= ========= ========= ========= ========= ========= =========

    def _getLockedFileList(self, lockedFileList=None):
        """ If the testing mode is on, lockedFileList ~= None """
        if lockedFileList is None:
            self.batchRows = self.lockAndReadRecords()
            for row in self.batchRows:
                batchDict = {}
                batchDict['session'] = row['session']
                batchDict['T1'] = os.path.join(row['location'], 'TissueClassify', 't1_average_BRAINSABC.nii.gz')
                batchDict['T2'] = os.path.join(row['location'], 'TissueClassify', 't2_average_BRAINSABC.nii.gz')
                batchDict['rightAccumben'] = os.path.join(row['location'], 'BRAINSCut', 'r_Accumben_seg.nii.gz')
                batchDict['leftAccumben'] = os.path.join(row['location'], 'BRAINSCut', 'l_Accumben_seg.nii.gz')
                batchDict['rightCaudate'] = os.path.join(row['location'], 'BRAINSCut', 'r_Caudate_seg.nii.gz')
                batchDict['leftCaudate'] = os.path.join(row['location'], 'BRAINSCut', 'l_Caudate_seg.nii.gz')
                batchDict['rightGlobus'] = os.path.join(row['location'], 'BRAINSCut', 'r_Globus_seg.nii.gz')
                batchDict['leftGlobus'] = os.path.join(row['location'], 'BRAINSCut', 'l_Globus_seg.nii.gz')
                batchDict['rightHippocampus'] = os.path.join(row['location'], 'BRAINSCut', 'r_Hippocampus_seg.nii.gz')
                batchDict['leftHippocampus'] = os.path.join(row['location'], 'BRAINSCut', 'l_Hippocampus_seg.nii.gz')
                batchDict['rightPutamen'] = os.path.join(row['location'], 'BRAINSCut', 'r_Putamen_seg.nii.gz')
                batchDict['leftPutamen'] = os.path.join(row['location'], 'BRAINSCut', 'l_Putamen_seg.nii.gz')
                batchDict['rightThalamus'] = os.path.join(row['location'], 'BRAINSCut', 'r_Thalamus_seg.nii.gz')
                batchDict['leftThalamus'] = os.path.join(row['location'], 'BRAINSCut', 'l_Thalamus_seg.nii.gz')
                self.testingData(batchDict)
            self.currentSession = self.batchRows[0]['session']
            self.loadMRMLNodesToScene()
        else:
            # Testing is on
            self.batchList = lockedFileList

    def testingData(self, batchDict):
        """ Load some default data for development and set up a viewing scenario for it.
        """
        import os
        if not os.environ['USER'] == 'dmwelch':
            return 0
        # TODO: Make a better dialog box here
        # dialogFrame = qt.QFrame()
        # dialogLayout = qt.QVBoxLayout()
        dataDialog = qt.QPushButton();
        dataDialog.setText('Loading files for session %s...' % batchDict['session']);
        # dataDialog.setLayout(dialogLayout)
        dataDialog.show()
        if slicer.util.getNode('T1_Average_%s' % batchDict['session']) is None:
            volumeNode = slicer.util.loadVolume(batchDict['T1'], properties={'name':"T1_Average_%s" % batchDict['session']})
        # if slicer.util.getNode('T2_Average_%s' % batchDict['session']) is None:
        #     volumeNode = slicer.util.loadVolume(batchDict['T2'], properties={'name':"T2_Average_%s" % batchDict['session']})
        if slicer.util.getNode('L_Putamen_%s' % batchDict['session']) is None:
            volumeNode = slicer.util.loadLabelVolume(batchDict['leftPutamen'],
                                                     properties={'name':'L_Putamen_%s' % batchDict['session']})
        # if slicer.util.getNode('R_Putamen_%s' % batchDict['session']) is None:
        #     volumeNode = slicer.util.loadLabelVolume(batchDict['rightPutamen'],
        #                                              properties={'name':'R_Putamen_%s' % batchDict['session']})
        dataDialog.close()

    def loadMRMLNodesToScene(self):
        # Get the image nodes
        t1Average = slicer.util.getNode('T1_Average_%s' % self.currentSession)
        ### t2Average = slicer.util.getNode('T2_Average_%s' % self.currentSession)
        # Set up template scene
        compositeNodes = slicer.util.getNodes('vtkMRMLSliceCompositeNode*')
        for compositeNode in compositeNodes.values():
            try:
                compositeNode.SetBackgroundVolumeID(t1Average.GetID())
                ### compositeNode.SetForegroundVolumeID(t2Average.GetID())
                ### compositeNode.SetForegroundOpacity(0.0)
            except AttributeError:
                raise IOError("Could not find nodes for session %s" % self.currentSession)
        applicationLogic = slicer.app.applicationLogic()
        applicationLogic.FitSliceToAll()

    def onNextButtonClicked(self):
        print "Next button clicked..."
        count = self.count + 1
        if count <= self.batchSize - 1:
            self.count = count
        else:
            self.count = 0
        self.currentSession = self.batchRows[count]['session']
        self.loadMRMLNodesToScene()

    def onPreviousButtonClicked(self):
        print "Previous button clicked..."
        count = self.count - 1
        if count >= 0:
            self.count = count
        else:
            self.count = self.batchSize
        self.currentSession = self.batchRows[count]['session']
        self.loadMRMLNodesToScene()

#! /usr/bin/env python
import os

from __main__ import ctk
from __main__ import qt
import SimpleITK as sitk
import sitkUtils
from __main__ import slicer
from __main__ import vtk

import module_locator

globals()['__file__'] = module_locator.module_path()

class SlicerDerivedImageEval:
    def __init__(self, parent):
        parent.title = 'Image Evaluation'
        parent.categories = ['Work in Progress']
        parent.dependencies = ['Volumes']
        parent.contributors = ['Dave Welch (UIowa), Hans Johnson (UIowa)']
        parent.helpText = """Image evaluation module for use in the UIowa PINC lab"""
        parent.acknowledgementText = """ """
        self.parent = parent


class SlicerDerivedImageEvalWidget:
    def __init__(self, parent=None):
        # Register the regions and QA values
        self.images = ('T2 image', 'T1 image', 'Brain mask' ) #T1 is second so that reviewers see it as background for regions
        self.regions = ('caudate_left', 'caudate_right',
                        'accumben_left', 'accumben_right',
                        'putamen_left', 'putamen_right',
                        'globus_left', 'globus_right',
                        'thalamus_left', 'thalamus_right',
                        'hippocampus_left', 'hippocampus_right')
        self.currentSession = None
        ###        self.sessionQLabel = None
        ###        self.evalFrame = None
        ###        self.pushButtons = {}
        ###        self.radioButtons = {}
        self.reviewButtons = {}
        # Handle the UI display with/without Slicer
        if parent is None:
            self.parent = slicer.qMRMLWidget()
            self.parent.setLayout(qt.QVBoxLayout())
            self.parent.setMRMLScene(slicer.mrmlScene)
            self.layout = self.parent.layout()
            self.logic = SlicerDerivedImageEvalLogic(self)
            self.setup()
            self.parent.show()
        else:
            self.parent = parent
            self.layout = self.parent.layout()
            self.logic = SlicerDerivedImageEvalLogic(self)

    def setup(self):
        # Batch navigation
        batchNavigation = self.loadUIFile('Resources/UI/navigationCollapsibleButton.ui')
        self.layout.addWidget(batchNavigation)
        self.navigationWidget = batchNavigation.findChild("buttonContainerWidget")
        ### TODO: Implement these buttons
        self.batchListWidget = batchNavigation.findChild("listWidget")
        ### self.previousButton = self.navigationWidget.findChild("QPushButton", "previousButton")
        ### self.quitButton = self.navigationWidget.findChild("QPushButton", "quitButton")
        ### self.nextButton = self.navigationWidget.findChild("QPushButton", "nextButton")
        # Evaluation subsection
        imageQA = self.loadUIFile('Resources/UI/imageQACollapsibleButton.ui')
        self.layout.addWidget(imageQA)
        qaLayout = qt.QVBoxLayout(imageQA)
        qaLayout.addWidget(imageQA.findChild("QFrame", "titleFrame"))
        qaLayout.addWidget(imageQA.findChild("QFrame", "tableVLine"))
        ### def reviewButtonFactory(self):
        for image in self.images:
            reviewButtonsWidget = QEvaluationWidget(self.loadUIFile('Resources/UI/reviewButtonsWidget.ui'), image)
            reviewButtonsWidget.setText(image)
            qaLayout.addWidget(reviewButtonsWidget.widget)

        for region in self.regions:
            reviewButtonsWidget = QEvaluationWidget(self.loadUIFile('Resources/UI/reviewButtonsWidget.ui'), region)
            reviewButtonsWidget.setText(region)
            qaLayout.addWidget(reviewButtonsWidget.widget)

        # self.radioButtons = self.evalFrame.findChildren('QRadioButton')
        self.layout.addWidget(imageQA)
        self.evaluationWidget = imageQA
        # resetButton
        self.resetButton = qt.QPushButton()
        self.resetButton.setText('Reset evaluation')
        self.layout.addWidget(self.resetButton)
        ### self.resetButton.connect('clicked(bool)', self.logic.onCancelButtonClicked)
        # batch button
        self.batchButton = qt.QPushButton()
        self.batchButton.setText('Get evaluation batch')
        self.layout.addWidget(self.batchButton)
        ### self.batchButton.connect('clicked(bool)', self.logic.onGetBatchFilesClicked)
        # session label
        # self.sessionQLabel = self.evaluationCollapsibleButton.findChild('QLabel', 'sessionBoxedLabel')
        # Connect push buttons
        ### self.connectSessionButtons()
        ### self.connectRegionButtons()
        ### TESTING ###
        if True:
            self.logic.onGetBatchFilesClicked()
        ### END ###
        # Add vertical spacer
        self.layout.addStretch(1)

    def loadUIFile(self, fileName):
        """ Return the object defined in the Qt Designer file """
        uiloader = qt.QUiLoader()
        qfile = qt.QFile(os.path.join(__file__, fileName))
        qfile.open(qt.QFile.ReadOnly)
        try:
            return uiloader.load(qfile)
        finally:
            qfile.close()

    def connectSessionButtons(self):
        """ Connect the session navigation buttons to their logic """
        self.nextSessionButton = self.evaluationCollapsibleButton.findChild('QPushButton', 'nextButton')
        self.nextSessionButton.connect('clicked()', self.logic.onNextButtonClicked)
        self.previousSessionButton = self.evaluationCollapsibleButton.findChild('QPushButton', 'previousButton')
        self.previousSessionButton.connect('clicked()', self.logic.onPreviousButtonClicked)

    def connectRegionButtons(self):
        """ Map the region buttons clicked() signals to the function """
        self.buttonMapper = qt.QSignalMapper()
        self.buttonMapper.connect('mapped(const QString&)', self.logic.selectRegion)
        self.buttonMapper.connect('mapped(const QString&)', self.enableRadios)
        for region in self.regions:
            self.pushButtons[region] = self.evaluationCollapsibleButton.findChild('QPushButton', region)
            self.buttonMapper.setMapping(self.pushButtons[region], region)
            self.pushButtons[region].connect('clicked()', self.buttonMapper, 'map()')

    def constructRadioButtonNames(self, buttonName):
        """ LOGIC: Construct the radio button names, given the region push button name """
        goodName = '_'.join([buttonName, 'good'])
        badName = '_'.join([buttonName, 'bad'])
        return goodName, badName

    def _findRadioButtons(self, buttonName):
        """ Returns the QRadioButtons for the matching QPushButton """
        goodName, badName = self.constructRadioButtonNames(buttonName)
        goodRadio = self.evaluationCollapsibleButton.findChild('QRadioButton', goodName)
        badRadio = self.evaluationCollapsibleButton.findChild('QRadioButton', badName)
        return goodRadio, badRadio

    def enableRadios(self, buttonName):
        """ Enable the radio buttons that match the given region push button """
        goodRadio, badRadio = self._findRadioButtons(buttonName)
        goodRadio.setEnabled(True)
        badRadio.setEnabled(True)

    def updateSessionQLabel(self):
        self.sessionQLabel.setText(str(self.currentSession))
        self.sessionQLabel.update()

    def resetRadioWidgets(self):
        """ Disable and reset all radio buttons in the widget """
        for button in self.radioButtons:
            button.isChecked(False)
            button.isEnabled(False)

    def resetWidget(self):
        self.resetRadioWidgets()
        self.updateSessionQLabel()

    def exit(self):
        """ When Slicer exits, prompt user if they want to write the last evaluation """
        pass

class SlicerDerivedImageEvalLogic(object):
    """ Logic class to be used 'under the hood' of the evaluator """
    def __init__(self, widget):
        self.widget = widget
        self.regions = self.widget.regions
        self.qaValueMap = {'good':'1', 'bad':'0', 'follow up':'-1'}
        self.user_id = None
        self.database = None
        self.batchList = None
        self.batchSize = 3
        self.batchRows = None
        self.count = 0 # Starting value
        self.maxCount = 0
        self.currentSession = None
        self.sessionFiles = {}
        self.currentRecordID = None
        self.testing = True
        self.setup()

    def setup(self):
        if self.testing:
            from database_helper import sqliteDatabase
            self.user_id = 'ttest'
            self.database = sqliteDatabase(self.user_id, self.batchSize)
        else:
            from database_helper import postgresDatabase
            self.user_id = os.environ['USER']
            self.database = postgresDatabase('opteron.pyschiatry.uiowa.edu', '5432', 'AutoWorkUp', 'autoworkup', 'AW_Up-2012', self.user_id, self.batchSize)
            # TODO: Handle password

    def selectRegion(self, buttonName):
        """ Load the outline of the selected region into the scene """
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

    def constructLabelNodeName(self, buttonName):
        """ Create the names for the volume and label nodes """
        nodeName = '_'.join([self.currentSession, buttonName])
        return nodeName

    def onCancelButtonClicked(self):
        # TODO: Populate this function
        #   onNextButtonClicked WITHOUT the write to database
        print "Cancelled!"

    def writeToDatabase(self, evaluations):
        values = (self.batchRows[self.count]['record_id'], self.user_id)
        values = values + evaluations
        columns = ('record_id', 'reviewer_id') + self.regions
        self.database.writeAndUnlockRecord(columns, values)

    def _getLabelFileNameFromRegion(self, regionName):
        try:
            region, side = regionName.split('_')
            fileName = '_'.join([side[0], region.capitalize(), 'seg.nii.gz'])
        except ValueError:
            region = regionName
            fileName = '_'.join([region, 'seg.nii.gz'])
        return fileName

    def onGetBatchFilesClicked(self):
        """ """
        self.count = 0
        self.batchRows = self.database.lockAndReadRecords()
        self.maxCount = len(self.batchRows)
        self.constructFilePaths()
        self.setCurrentSession()
        self.loadData()
        ### DEBUG
        ### self.widget.resetWidget()

    def setCurrentSession(self):
        self.currentSession = self.sessionFiles['session']
        self.widget.currentSession = self.currentSession

    def constructFilePaths(self):
        row = self.batchRows[self.count]
        sessionFiles = {}
        baseDirectory = os.path.join(str(row['location']),
                                     str(row['_analysis']),
                                     str(row['_project']),
                                     str(row['_subject']),
                                     str(row['_session']))
        sessionFiles['T1'] = os.path.join(baseDirectory, 'TissueClassify', 't1_average_BRAINSABC.nii.gz')
        sessionFiles['T2'] = os.path.join(baseDirectory, 'TissueClassify', 't2_average_BRAINSABC.nii.gz')
        for regionName in self.regions:
            fileName = self._getLabelFileNameFromRegion(regionName)
            sessionFiles[regionName] = os.path.join(baseDirectory, 'BRAINSCut', fileName)
        sessionFiles['session'] = str(row['_session'])
        sessionFiles['record_id'] = str(row['record_id'])
        self.sessionFiles = sessionFiles

    def loadData(self):
        """ Load some default data for development and set up a viewing scenario for it.
        """
        dataDialog = qt.QPushButton();
        dataDialog.setText('Loading files for session %s...' % self.currentSession);
        dataDialog.show()
        t1NodeName = '%s_t1_average' % self.currentSession
        t1VolumeNode = slicer.util.getNode(t1NodeName)
        if t1VolumeNode is None:
            ### t1VolumeNode = slicer.util.loadVolume(self.sessionFiles['T1'], properties={'name':t1NodeName})
            reader = sitk.ImageFileReader()
            print self.sessionFiles['T1']
            reader.SetFileName(self.sessionFiles['T1'])
            t1Image = reader.Execute()
            sitkUtils.PushToSlicer(t1Image, t1NodeName, False)
            if slicer.util.getNode(t1NodeName) is None:
                raise IOError("Could not load session file for T1! File: %s" % self.sessionFiles['T1'])
        t2NodeName = '%s_t2_average' % self.currentSession
        t2VolumeNode = slicer.util.getNode(t2NodeName)
        if t2VolumeNode is None:
            ### t1VolumeNode = slicer.util.loadVolume(self.sessionFiles['T1'], properties={'name':t1NodeName})
            reader = sitk.ImageFileReader()
            print self.sessionFiles['T2']
            reader.SetFileName(self.sessionFiles['T2'])
            t2Image = reader.Execute()
            sitkUtils.PushToSlicer(t2Image, t2NodeName, True)
            if slicer.util.getNode(t2NodeName) is None:
                raise IOError("Could not load session file for T2! File: %s" % self.sessionFiles['T2'])
        ### if slicer.util.getNode('%s_t2_average' % self.currentSession) is None:
        ###     volumeNode = slicer.util.loadVolume(self.sessionFiles['T2'],
        ###                                         properties={'name':"%s_t2_average" % self.currentSession})
        for region in self.regions:
            regionNodeName = '%s_%s' % (self.currentSession, region)
            if slicer.util.getNode(regionNodeName) is None:
                ### slicer.util.loadLabelVolume(self.sessionFiles[region], properties={'name':regionNodeName})
                reader = sitk.ImageFileReader()
                reader.SetFileName(self.sessionFiles[region])
                regionImage = reader.Execute()
                sitkUtils.PushToSlicer(regionImage, regionNodeName, False)
                collection = slicer.mrmlScene.GetNodesByName(regionNodeName)
                regionNode = collection.GetItemAsObject(0).SetAttribute("LabelMap", "1")
        dataDialog.close()

    def loadBackgroundNodeToMRMLScene(self, volumeNode):
        # Set up template scene
        compositeNodes = slicer.util.getNodes('vtkMRMLSliceCompositeNode*')
        for compositeNode in compositeNodes.values():
            try:
                compositeNode.SetBackgroundVolumeID(volumeNode.GetID())
            except AttributeError:
                raise IOError("Could not find nodes for session %s" % self.currentSession)
        applicationLogic = slicer.app.applicationLogic()
        applicationLogic.FitSliceToAll()

    def getEvaluationValues(self):
        """ Get the evaluation values from the widget """
        values = ()
        for region in self.regions:
            goodButton, badButton = self.widget._findRadioButtons(region)
            if goodButton.isChecked():
                values = values + (self.qaValueMap['good'],)
            elif badButton.isChecked():
                values = values + (self.qaValueMap['bad'],)
            else:
                Exception('Session cannot be changed until all regions are evaluated.  Missing region: %s' % region)
        return values

    def onNextButtonClicked(self):
        """ Capture the evaluation values, write them to the database, reset the widgets, then load the next dataset """
        try:
            evaluations = self.getEvaluationValues()
        except:
            return
        columns = ('record_id',) + self.regions
        values = (self.sessionFiles['record_id'], ) + evaluations
        try:
            self.database.writeAndUnlockRecord(columns, values)
        except sqlite3.OperationalError:
            print "Error here"
        count = self.count + 1
        if count <= self.maxCount - 1:
            self.count = count
        else:
            self.count = 0
        self.loadNewSession()
        self.widget.resetWidget()

    def onPreviousButtonClicked(self):
        try:
            evaluations = self.getEvaluationValues()
        except:
            return
        columns = ('record_id', ) + self.regions
        values = (self.sessionFiles['record_id'], ) + evaluations
        self.database.writeAndUnlockRecord(columns, values)
        count = self.count - 1
        if count >= 0:
            self.count = count
        else:
            self.count = self.maxCount - 1
        self.loadNewSession()
        self.widget.resetWidget()

    def loadNewSession(self):
        self.constructFilePaths()
        self.setCurrentSession()
        self.loadData()

class QEvaluationWidget(object):
    def __init__(self, widget, name=None):
        self.widget = widget
        self.name = name

    def name(self):
        return self.name

    def setName(self, name):
        """ Set name value for class """
        self.name = name

    def _formatName(self, text):
        parsed = self.name.split("_")
        if len(parsed) > 1:
            pushText = " ".join([parsed[1].capitalize(), parsed[0]])
        else:
            pushText = parsed[0].capitalize()
        return pushText

    def setText(self, text):
        pushButton = self.widget.findChild("QPushButton")
        pushButton.setText(self._formatName(text))

    def text(self):
        pushButton = self.widget.findChild("QPushButton")
        return pushButton.text

    def getValue(self):
        radios = self.widget.findChildren("QRadioButton")
        for radio in radios:
            if radio.checked:
                return radio ### TODO: Need to get at the identity here!

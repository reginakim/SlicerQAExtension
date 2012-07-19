#! /usr/bin/env python
import os

from __main__ import ctk
from __main__ import qt
#import SimpleITK as sitk
#import sitkUtils
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
        self.images = ('t2_average', 't1_average') #T1 is second so that reviewers see it as background for regions
        self.regions = ('labels_tissue',
                        'caudate_left', 'caudate_right',
                        'accumben_left', 'accumben_right',
                        'putamen_left', 'putamen_right',
                        'globus_left', 'globus_right',
                        'thalamus_left', 'thalamus_right',
                        'hippocampus_left', 'hippocampus_right')
        self.currentSession = None
        ###        self.sessionQLabel = None
        self.imageQAWidget = None
        self.navigationWidget = None
        self.followUpDialog = None
        self.notes = None
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
        self.followUpDialog = self.loadUIFile('Resources/UI/followUpDialog.ui')
        self.clipboard = qt.QApplication.clipboard()
        self.textEditor = self.followUpDialog.findChild("QTextEdit", "textEditor")
        buttonBox = self.followUpDialog.findChild("QDialogButtonBox", "buttonBox")
        # TODO
        buttonBox.connect("accepted()", self.grabNotes)
        buttonBox.connect("rejected()", self.cancelNotes)
        #
        # Batch navigation
        self.navigationWidget = self.loadUIFile('Resources/UI/navigationCollapsibleButton.ui')
        nLayout = qt.QVBoxLayout(self.navigationWidget)
        nLayout.addWidget(self.navigationWidget.findChild("QLabel", "batchLabel"))
        nLayout.addWidget(self.navigationWidget.findChild("QListWidget", "batchList"))
        nLayout.addWidget(self.navigationWidget.findChild("QWidget", "buttonContainerWidget"))
        # Find navigation buttons
        self.previousButton = self.navigationWidget.findChild("QPushButton", "previousButton")
        self.quitButton = self.navigationWidget.findChild("QPushButton", "quitButton")
        self.nextButton = self.navigationWidget.findChild("QPushButton", "nextButton")
        self.connectSessionButtons()
        # Evaluation subsection
        self.imageQAWidget = self.loadUIFile('Resources/UI/imageQACollapsibleButton.ui')
        qaLayout = qt.QVBoxLayout(self.imageQAWidget)
        qaLayout.addWidget(self.imageQAWidget.findChild("QFrame", "titleFrame"))
        qaLayout.addWidget(self.imageQAWidget.findChild("QFrame", "tableVLine"))
        # Create review buttons on the fly
        for image in self.images + self.regions:
            reviewButton = self.reviewButtonFactory(image)
            qaLayout.addWidget(reviewButton)
        self.connectReviewButtons()
        # resetButton
        self.resetButton = qt.QPushButton()
        self.resetButton.setText('Reset evaluation')
        self.resetButton.connect('clicked(bool)', self.resetWidget)
        # batch button
        self.batchButton = qt.QPushButton()
        self.batchButton.setText('Get evaluation batch')
        self.batchButton.connect('clicked(bool)', self.onGetBatchFilesClicked)
        # Add all to layout
        self.layout.addWidget(self.navigationWidget)
        nLayout.addWidget(self.resetButton)
        nLayout.addWidget(self.batchButton)
        self.layout.addWidget(self.imageQAWidget)
        self.layout.addStretch(1)
        ### TESTING ###
        if True:
            self.logic.onGetBatchFilesClicked()
        ### END ###

    def loadUIFile(self, fileName):
        """ Return the object defined in the Qt Designer file """
        uiloader = qt.QUiLoader()
        qfile = qt.QFile(os.path.join(__file__, fileName))
        qfile.open(qt.QFile.ReadOnly)
        try:
            return uiloader.load(qfile)
        finally:
            qfile.close()

    def reviewButtonFactory(self, image):
        widget = self.loadUIFile('Resources/UI/reviewButtonsWidget.ui')
        # Set push button
        pushButton = widget.findChild("QPushButton", "imageButton")
        pushButton.objectName = image
        pushButton.setText(self._formatText(image))
        radioContainer = widget.findChild("QWidget", "radioWidget")
        radioContainer.objectName = image + "_radioWidget"
        # Set radio buttons
        goodButton = widget.findChild("QRadioButton", "goodButton")
        goodButton.objectName = image + "_good"
        badButton = widget.findChild("QRadioButton", "badButton")
        badButton.objectName = image + "_bad"
        followUpButton = widget.findChild("QRadioButton", "followUpButton")
        followUpButton.objectName = image + "_followUp"
        return widget

    def _formatText(self, text):
        parsed = text.split("_")
        if len(parsed) > 1:
            text = " ".join([parsed[1].capitalize(), parsed[0]])
        else:
            text = parsed[0].capitalize()
        return text

    def connectSessionButtons(self):
        """ Connect the session navigation buttons to their logic """
        # self.nextButton.connect('clicked()', self.logic.onNextButtonClicked)
        # self.previousButton.connect('clicked()', self.logic.onPreviousButtonClicked)
        self.quitButton.connect('clicked()', self.exit)

    def connectReviewButtons(self):
        """ Map the region buttons clicked() signals to the function """
        self.buttonMapper = qt.QSignalMapper()
        self.buttonMapper.connect('mapped(const QString&)', self.logic.selectRegion)
        self.buttonMapper.connect('mapped(const QString&)', self.enableRadios)
        for image in self.images + self.regions:
            pushButton = self.imageQAWidget.findChild('QPushButton', image)
            self.buttonMapper.setMapping(pushButton, image)
            pushButton.connect('clicked()', self.buttonMapper, 'map()')

    def enableRadios(self, image):
        """ Enable the radio buttons that match the given region name """
        self.imageQAWidget.findChild("QWidget", image + "_radioWidget").setEnabled(True)
        for suffix in ("_good", "_bad", "_followUp"):
            radio = self.imageQAWidget.findChild("QRadioButton", image + suffix)
            radio.setShortcutEnabled(True)
            radio.setCheckable(True)
            radio.setEnabled(True)

    def disableRadios(self, image):
        """ Disable all radio buttons that DO NOT match the given region name """
        radios = self.imageQAWidget.findChildren("QRadioButton")
        for radio in radios:
            if radio.objectName.find(image) == -1:
                radio.setShortcutEnabled(False)
                radio.setEnabled(False)

    def resetRadioWidgets(self):
        """ Disable and reset all radio buttons in the widget """
        radios = self.imageQAWidget.findChildren("QRadioButton")
        for radio in radios:
            radio.setCheckable(False)
            radio.setEnabled(False)

    def getRadioValues(self):
        values = ()
        needsFollowUp = False
        radios = self.imageQAWidget.findChildren("QRadioButton")
        for image in self.images + self.regions:
            for radio in radios:
                if radio.objectName.find(image) > -1 and radio.checked:
                    if radio.objectName.find("_good") > -1:
                        values = values + ("1",)
                    elif radio.objectName.find("_bad") > -1:
                        values = values + ("0",)
                    elif radio.objectName.find("_followUp") > -1:
                        values = values + ("-1",)
                        needsFollowUp = True
                    else:
                        values = values + ("NULL",)
                        print "Warning: No value for %s" % image
        if needsFollowUp:
            self.followUpDialog.exec_()
            if self.followUpDialog.result() and not self.notes is None:
                values = values + (self.notes,)
            else:
                values = values + ("NULL",)
        else:
            values = values + ("NULL",)
        return values

    def resetWidget(self):
        # self.getRadioValues()
        self.resetRadioWidgets()

    def grabNotes(self):
        self.notes = None
        self.notes = str(self.textEditor.toPlainText())
        # if self.notes = '':
        #     self.followUpDialog.show()
        #     self.textEditor.setText("A comment is required!")
        self.textEditor.clear()

    def cancelNotes(self):
        # TODO:
        pass

    def onGetBatchFilesClicked(self):
        values = self.getRadioValues()
        if len(values) >= len(self.images + self.regions):
            self.logic.writeToDatabase(values)
        else:
            # TODO: Handle this case intelligently
            print "Not enough values for the required columns!"
            raise Exception
        self.resetWidget()
        self.logic.onGetBatchFilesClicked()

    def exit(self):
        """ When Slicer exits, prompt user if they want to write the last evaluation """
        values = self.getRadioValues()
        if len(values) >= len(self.images + self.regions):
            self.logic.writeToDatabase(values)
        else:
            # TODO: Handle this case intelligently
            print "Not enough values for the required columns!"
            raise Exception
        self.logic.exit()

class SlicerDerivedImageEvalLogic(object):
    """ Logic class to be used 'under the hood' of the evaluator """
    def __init__(self, widget):
        self.widget = widget
        self.regions = self.widget.regions
        self.images = self.widget.images
        self.qaValueMap = {'good':'1', 'bad':'0', 'follow up':'-1'}
        self.colorTable = "IPL-BrainAtlas-ColorFile.txt"
        self.colorTableNode = None
        self.user_id = None
        self.database = None
        self.batchList = None
        self.batchSize = 1
        self.batchRows = None
        self.count = 0 # Starting value
        self.maxCount = 0
        self.currentSession = None
        self.currentValues = (None,)*len(self.images + self.regions)
        self.sessionFiles = {}
        self.testing = True
        self.setup()

    def setup(self):
        self.createColorTable()
        # self.createColorRegionMap()
        if self.testing:
            from database_helper import sqliteDatabase
            self.user_id = 'ttest'
            self.database = sqliteDatabase(self.user_id, self.batchSize)
        else:
            from database_helper import postgresDatabase
            self.user_id = os.environ['USER']
            self.database = postgresDatabase('opteron.pyschiatry.uiowa.edu', '5432', 'AutoWorkUp', 'autoworkup', 'AW_Up-2012', self.user_id, self.batchSize)
            # TODO: Handle password

    def createColorTable(self):
        """
        """
        self.colorTableNode = slicer.vtkMRMLColorTableNode()
        self.colorTableNode.SetFileName(os.path.join(__file__, 'Resources', 'ColorFile', self.colorTable))
        self.colorTableNode.SetName(self.colorTable[:-4])
        storage = self.colorTableNode.CreateDefaultStorageNode()
        slicer.mrmlScene.AddNode(storage)
        self.colorTableNode.AddAndObserveStorageNodeID(storage.GetID())
        slicer.mrmlScene.AddNode(self.colorTableNode)
        storage.SetFileName(self.colorTableNode.GetFileName())
        storage.SetReadState(True)
        storage.ReadData(self.colorTableNode, True)

    def createColorRegionMap(self):
        self.colorMap = {}
        for region in self.regions:
            anatomy, side = region.split("_")
            for index in range(self.colorTableNode.GetNumberOfColors()):
                colorName = self.colorTableNode.GetColorName(index)
                if colorName.find(anatomy) > -1:
                    if side == "left" and colorName.find("_L") > -1:
                        self.colorMap[region] = colorName
                        break
                    elif side == "right" and colorName.find("_R") > -1:
                        self.colorMap[region] = colorName
                        break
                    else:
                        self.colorMap[region] = colorName ### BUG: brain mask colors WILL NOT match up with regions
        print self.colorMap

    def addEntryToColorTable(self, buttonName):
        lTable = self.colorTableNode.GetLookupTable()
        colorIndex = self.colorTableNode.GetColorIndexByName(buttonName)#self.colorMap[buttonName])
        color = lTable.GetTableValue(colorIndex)
        self.colorTableNode.AddColor(buttonName, *color)

    def selectRegion(self, buttonName):
        """ Load the outline of the selected region into the scene """
        nodeName = self.constructLabelNodeName(buttonName)
        labelNode = slicer.util.getNode(nodeName)
        if labelNode.GetLabelMap():
            # if buttonName != "labels_tissue":
            #     print buttonName
            #     self.addEntryToColorTable(buttonName)
            # else:
            #     print "Mask found! %s" % buttonName
            #     for region in self.regions[1:]:
            #         self.selectRegion(region)
            ########################################
            #     lTable = self.colorTableNode.GetLookupTable()
            #     colorIndex = self.colorTableNode.GetColorIndexByName(self.colorMap[buttonName])
            #     color = lTable.GetTableValue(colorIndex)
            #     labelNode.GetDisplayNode().SetColor(color[0:3])
            # else:
            labelNode.GetDisplayNode().SetAndObserveColorNodeID(self.colorTableNode.GetID())
            #
            compositeNodes = slicer.util.getNodes('vtkMRMLSliceCompositeNode*')
            for compositeNode in compositeNodes.values():
                compositeNode.SetLabelVolumeID(labelNode.GetID())
                compositeNode.SetLabelOpacity(1.0)
            # Set the label outline to ON
            sliceNodes = slicer.util.getNodes('vtkMRMLSliceNode*')
            for sliceNode in sliceNodes.values():
                sliceNode.UseLabelOutlineOn()
        else:
             self.loadBackgroundNodeToMRMLScene(labelNode)

    def constructLabelNodeName(self, buttonName):
        """ Create the names for the volume and label nodes """
        nodeName = '_'.join([self.currentSession, buttonName])
        return nodeName

    def onCancelButtonClicked(self):
        # TODO: Populate this function
        #   onNextButtonClicked WITHOUT the write to database
        print "Cancelled!"

    def writeToDatabase(self, evaluations):
        recordID = str(self.batchRows[self.count]['record_id'])
        values = (recordID,) + evaluations
        try:
            self.database.writeAndUnlockRecord(values)
        except:
            # TODO: Prompt user with popup
            print "Error writing to database!"
            raise

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
            if regionName == 'labels_tissue':
                sessionFiles['labels_tissue'] = os.path.join(baseDirectory, 'TissueClassify', 'brain_label_seg.nii.gz')
            else:
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
        volumeLogic = slicer.modules.volumes.logic()
        t1NodeName = '%s_t1_average' % self.currentSession
        t1VolumeNode = slicer.util.getNode(t1NodeName)
        if t1VolumeNode is None:
            volumeLogic.AddArchetypeScalarVolume(self.sessionFiles['T1'], t1NodeName, 0)
            if slicer.util.getNode(t1NodeName) is None:
                raise IOError("Could not load session file for T1! File: %s" % self.sessionFiles['T1'])
            t1VolumeNode = slicer.util.getNode(t1NodeName)
            t1VolumeNode.CreateDefaultDisplayNodes()
            t1VolumeNode.GetDisplayNode().AutoWindowLevelOn()
        t2NodeName = '%s_t2_average' % self.currentSession
        t2VolumeNode = slicer.util.getNode(t2NodeName)
        if t2VolumeNode is None:
            volumeLogic.AddArchetypeScalarVolume(self.sessionFiles['T2'], t2NodeName, 0)
            if slicer.util.getNode(t2NodeName) is None:
                raise IOError("Could not load session file for T2! File: %s" % self.sessionFiles['T2'])
            t2VolumeNode = slicer.util.getNode(t2NodeName)
            t2VolumeNode.CreateDefaultDisplayNodes()
            t2VolumeNode.GetDisplayNode().AutoWindowLevelOn()
        for region in self.regions:
            regionNodeName = '%s_%s' % (self.currentSession, region)
            regionNode = slicer.util.getNode(regionNodeName)
            if regionNode is None:
                volumeLogic.AddArchetypeScalarVolume(self.sessionFiles[region], regionNodeName, 1)
                if slicer.util.getNode(regionNodeName) is None:
                    raise IOError("Could not load session file for region %s! File: %s" % (region, self.sessionFiles[region]))
                regionNode = slicer.util.getNode(regionNodeName)
                displayNode = slicer.vtkMRMLLabelMapVolumeDisplayNode()
                slicer.mrmlScene.AddNode(displayNode)
                regionNode.SetAndObserveNthDisplayNodeID(0, displayNode.GetID())
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

    def exit(self):
        # if 'follow up' in currentValues.values():
        #     followUpList = []
        #     for key in currentValues.keys():
        #         if currentValues[key] == self.qaValueMap['follow up']:
        #             followUpList.append(key)
        # Print list in dialog
        # dialog = self.widget.followUpDialog
        # dialog.
        pass

#! /usr/bin/env python

import os
import sqlite3
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
        self.currentSession = None
        self.logic = SlicerDerivedImageEvalLogic()

    def setup(self):
        ### START DEVELOPMENT TOOL ###
        # Layout within the summary collapsible button
        self.reloadButton = qt.QPushButton("Reload")
        self.reloadButton.toolTip = "Reload this module."
        self.reloadButton.name = "SlicerDerivedImageEval Reload"
        self.layout.addWidget(self.reloadButton)
        self.reloadButton.connect('clicked()', self.onReload)
        ###        END TOOL        ###
        # Load UI file
        uiloader = qt.QUiLoader()
        qfile = qt.QFile(os.path.join(__file__, 'Resources/UI/evaluationPrototype.ui'))
        qfile.open(qt.QFile.ReadOnly)
        evalFrame = uiloader.load(qfile)
        qfile.close()
        # Evaluation subsection
        self.evaluationCollapsibleButton = ctk.ctkCollapsibleButton()
        self.evaluationCollapsibleButton.text = 'Evaluation input'
        self.evaluationCollapsibleButton.setLayout(evalFrame.findChild('QVBoxLayout'))
        self.layout.addWidget(self.evaluationCollapsibleButton)
        # Get buttons in UI file
        self.buttons = {}
        pushButtons = self.evaluationCollapsibleButton.findChildren('QPushButton')
        for button in pushButtons:
            self.buttons[button.objectName] = button
            if button.objectName in ['caudateLeftPushButton', 'caudateRightPushButton',
                                     'hippocampusLeftPushButton', 'hippocampusRightPushButton',
                                     'putamenLeftPushButton', 'putamenRightPushButton',
                                     'thalamusLeftPushButton', 'thalamusRightPushButton']:
                self.buttons[button.objectName].connect('clicked()', self.onRegionButtonClicked)
        self.buttons['nextButton'].connect('clicked()', self.onNextButtonClicked)
        self.buttons['previousButton'].connect('clicked()', self.onPreviousButtonClicked)
        # Get session label button
        self.sessionLabel = None
        labels = self.evaluationCollapsibleButton.findChildren('QLabel')
        for label in labels:
            if label.text == '####':
                self.sessionLabel = label
                break
        # Get radios in UI file
        self.radios = {}
        radioButtons = self.evaluationCollapsibleButton.findChildren('QRadioButton')
        for button in radioButtons:
            button.setEnabled(False)
            self.radios[button.objectName] = button
            self.radios[button.objectName].connect('clicked()', self.onRegionButtonClicked)
        # Add vertical spacer
        self.layout.addStretch(1)
        # Set local var as instance attribute
        # self.batchFilesButton = batchFilesButton

    def onBatchFilesButtonClicked(self):
        print "Batch file button clicked..."
        fileList = self.logic.batchList

    def onRegionButtonClicked(self):
        if self.buttons['putamenLeftPushButton'].isClicked():
            labelNode = slicer.util.getNode('L_Putamen_%s' % self.sessionLabel.text)
            self.radios['putamenLeftGoodButton'].setEnabled(True)
            self.radios['putamenLeftBadButton'].setEnabled(True)
        elif self.buttons['putamenRightPushButton'].isClicked():
            labelNode = slicer.util.getNode('R_Putamen_%s' % self.sessionLabel.text)
            self.radios['putamenRightGoodButton'].setEnabled(True)
            self.radios['putamenRightBadButton'].setEnabled(True)
        elif self.buttons['caudateRightPushButton'].isClicked():
            labelNode = slicer.util.getNode('R_Caudate_%s' % self.sessionLabel.text)
            self.radios['caudateRightGoodButton'].setEnabled(True)
            self.radios['caudateRightBadButton'].setEnabled(True)
        # Set the scene
        compositeNodes = slicer.util.getNodes('vtkMRMLSliceCompositeNode*')
        for compositeNode in compositeNodes.values():
            compositeNode.SetLabelVolumeID(labelNode.GetID())
            compositeNode.SetLabelOpacity(1.0)
        sliceNodes = slicer.util.getNodes('vtkMRMLSliceNode*')
        for sliceNode in sliceNodes.values():
            sliceNode.UseLabelOutlineOn()

    def onNextButtonClicked(self):
        if self.writeReviewToDatabase():
            self.currentSession = self.logic.onNextButtonClicked()
            self.sessionLabel.text = self.currentSession
            self.sessionLabel.update()

    def onPreviousButtonClicked(self):
        if self.writeReviewToDatabase():
            self.currentSession = self.logic.onPreviousButtonClicked()
            self.sessionLabel.text = self.currentSession
            self.sessionLabel.update()

    def writeReviewToDatabase(self):
        keys = self.radios.keys()
        keys.sort()
        for key in keys:
            goodKey = key.replace('Bad', 'Good'); keys.remove(goodKey)
            badKey = key.replace('Good', 'Bad'); keys.remove(badKey)
            if not (self.radios[goodKey].isChecked() or self.radios[badKey].isChecked()):
                return False
            else:
                if self.radios[goodKey].isChecked():
                    # Write out 'True' to correct column
                    print "%s is True" % goodKey
                else:
                    print "%s is True" % badKey
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
        self.testing = False
        self.database = None
        self.experiment = None
        self.batchList = None
        self.batchSize = 5
        self.batchRows = None
        #  self.testingData()
        self.onGetBatchFilesClicked() # TESTING
        self.count = 0 # Starting value

    def onGetBatchFilesClicked(self):
        import os
        # TODO: import sqlite3
        batchList = []
        if self.testing:
            batchFile = os.path.join(__file__, 'Testing', 'database.csv')
            t1AverageSuffix = 'TissueClassify/t1_average_BRAINSABC.nii.gz'
            t2AverageSuffix = 'TissueClassify/t2_average_BRAINSABC.nii.gz'
            leftPutamenSuffix = 'BRAINSCut/l_Putamen_seg.nii.gz'
            fid = open(batchFile, 'r')
            try:
                entries = fid.readlines()
            except:
                raise
            finally:
                fid.close()
            count = 0
            for entry in entries:
                base, subject, session = entry.split(', ')
                session = session.strip()
                batchList.append({})
                batchList[count]['subject'] = subject
                batchList[count]['session'] = session
                batchList[count]['T1'] = __file__ + os.path.join(base, subject, session, t1AverageSuffix)
                batchList[count]['T2'] = __file__ + os.path.join(base, subject, session, t2AverageSuffix)
                batchList[count]['leftPutamen'] = __file__ + os.path.join(base, subject, session, leftPutamenSuffix)
                count += 1
            self._getLockedFileList(batchList)
        else:
            self.database = os.path.join(__file__, 'Testing', 'sqlTest.db')
            self._getLockedFileList()

    #========= TODO: move the database code to a helper file =========
    def openDatabase(self):
        self.connection = sqlite3.connect(self.database, isolation_level="IMMEDIATE")
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()
        self.cursor.arraysize = self.batchSize

    def getBatchIDs(self):
        # Get batch
        self.cursor.execute("SELECT id \
                            FROM derived_images \
                            WHERE status = 'needs review'")
        ids = self.cursor.fetchmany()
        if not ids:
            # TODO: This shouldn't be an exception - should halt gracefully
            self.connection.close()
            raise Exception("No rows were status == 'needs review' were found!")
        return ids

    def lockBatchRows(self, ids):
        # Lock batch members
        for ID in ids:
            self.cursor.execute("UPDATE derived_images \
                                 SET status='locked' \
                                 WHERE record_id=?", ID)
        self.cursor.connection.commit()

    def readBatchInformation(self, ids):
        batch = []
        for ID in ids:
            self.cursor.execute("SELECT id, analysis, project, subject, session \
                                 FROM derived_images \
                                 WHERE record_id=? AND status='locked'", ID)
            batch.append(self.cursor.fetchone())
        return batch

    def lockAndReadRecords(self):
        self.openDatabase()
        try:
            ids = self.getBatchIDs()
            self.lockBatchRows(ids)
            self.batchRows = self.readBatchInformation(ids)
        except Exception, e:
            raise e
        finally:
            self.connection.close()

    def writeAndUnlockRecord(self, values, ID):
        self.openDatabase()
        try:
            self.cursor.execute("UPDATE reviews \
                                 SET caudateRight=?, caudateLeft=?, \
                                 hippocampusRight=?, hippocampusLeft=?, \
                                 putamenRight=?, putamenLeft=?, \
                                 thalamusRight=?, thalamusLeft=? \
                                 WHERE record_id=?", values + ID)
            self.cursor.execute("UPDATE derived_images \
                                 SET status='reviewed' \
                                 WHERE record_id=? AND status='locked'", ID)
            self.cursor.commit()
        finally:
            self.connection.close()
    # ========= ========= ========= ========= ========= ========= =========

    def _getLockedFileList(self, lockedFileList=None):
        """ If the testing mode is on, lockedFileList ~= None """
        if lockedFileList is None:
            self.lockAndReadRecords()
            for item in self.batchList:
                batchDict = {}
                batchDict['session'] = item['session']
                batchDict['T1'] = os.path.join(item['location'], 'TissueClassify', 't1_average_BRAINSABC.nii.gz')
                batchDict['T2'] = os.path.join(item['location'], 'TissueClassify', 't2_average_BRAINSABC.nii.gz')
                batchDict['rightAccumben'] = os.path.join(item['location'], 'BRAINSCut', 'r_Accumben_seg.nii.gz')
                batchDict['leftAccumben'] = os.path.join(item['location'], 'BRAINSCut', 'l_Accumben_seg.nii.gz')
                batchDict['rightCaudate'] = os.path.join(item['location'], 'BRAINSCut', 'r_Caudate_seg.nii.gz')
                batchDict['leftCaudate'] = os.path.join(item['location'], 'BRAINSCut', 'l_Caudate_seg.nii.gz')
                batchDict['rightGlobus'] = os.path.join(item['location'], 'BRAINSCut', 'r_Globus_seg.nii.gz')
                batchDict['leftGlobus'] = os.path.join(item['location'], 'BRAINSCut', 'l_Globus_seg.nii.gz')
                batchDict['rightHippocampus'] = os.path.join(item['location'], 'BRAINSCut', 'r_Hippocampus_seg.nii.gz')
                batchDict['leftHippocampus'] = os.path.join(item['location'], 'BRAINSCut', 'l_Hippocampus_seg.nii.gz')
                batchDict['rightPutamen'] = os.path.join(item['location'], 'BRAINSCut', 'r_Putamen_seg.nii.gz')
                batchDict['leftPutamen'] = os.path.join(item['location'], 'BRAINSCut', 'l_Putamen_seg.nii.gz')
                batchDict['rightThalamus'] = os.path.join(item['location'], 'BRAINSCut', 'r_Thalamus_seg.nii.gz')
                batchDict['leftThalamus'] = os.path.join(item['location'], 'BRAINSCut', 'l_Thalamus_seg.nii.gz')
                self.testingData(batchDict)
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
            print 'T1_Average_%s' % batchDict['session']
            print '====== is here -------'
            print batchDict['T1']
            volumeNode = slicer.util.loadVolume(batchDict['T1'], properties={'name':"T1_Average_%s" % batchDict['session']})
        if slicer.util.getNode('T2_Average_%s' % batchDict['session']) is None:
            volumeNode = slicer.util.loadVolume(batchDict['T2'], properties={'name':"T2_Average_%s" % batchDict['session']})
        if slicer.util.getNode('L_Putamen_%s' % batchDict['session']) is None:
            volumeNode = slicer.util.loadLabelVolume(batchDict['leftPutamen'],
                                                     properties={'name':'L_Putamen_%s' % batchDict['session']})
        if slicer.util.getNode('R_Putamen_%s' % batchDict['session']) is None:
            volumeNode = slicer.util.loadLabelVolume(batchDict['rightPutamen'],
                                                     properties={'name':'R_Putamen_%s' % batchDict['session']})
        dataDialog.close()
        # Get the image nodes
        t1Average = slicer.util.getNode('T1_Average_%s' % batchDict['session'])
        t2Average = slicer.util.getNode('T2_Average_%s' % batchDict['session'])
        # leftPutamen = slicer.util.getNode('L_Putamen_%s' % batchDict['session'])
        # brainsLabel = slicer.util.getNode('BRAINS_label')
        # Set up template scene
        compositeNodes = slicer.util.getNodes('vtkMRMLSliceCompositeNode*')
        for compositeNode in compositeNodes.values():
            try:
                compositeNode.SetBackgroundVolumeID(t1Average.GetID())
                compositeNode.SetForegroundVolumeID(t2Average.GetID())
                compositeNode.SetForegroundOpacity(0.0)
            except AttributeError:
                raise IOError("Could not find files/nodes for session %s" % batchDict['session'])
        applicationLogic = slicer.app.applicationLogic()
        applicationLogic.FitSliceToAll()
        return batchDict['session']

    def onNextButtonClicked(self):
        print "Next button clicked..."
        count = self.count + 1
        if count <= self.batchSize:
            self.count = count
        else:
            self.count = 0
        self.currentSession = self.testingData(self.batchList[self.count])

    def onPreviousButtonClicked(self):
        print "Previous button clicked..."
        count = self.count - 1
        if count >= 0:
            self.count = count
        else:
            self.count = self.batchSize
        self.currentSession = self.testingData(self.batchList[self.count])

class MRMLSceneTemplate(object):
    """ Create a MRMLScene Template for each scan session """
    def __init__(self):
        self.template = None

    def getTemplate(self, sessionDirectory):
        pass

    def _createMRMLSceneTemplate(self):
        self.scene = slicer.vtkMRMLScene()
        # TODO: Set/verify layout with LayoutManager
        self.template.correctedT1 = slicer.vtkMRMLScalarVolumeNode()
        self.template.correctedT2 = slicer.vtkMRMLScalarVolumeNode()
        self.template.posterior.air = slicer.vtkMRMLScalarVolumeNode()
        # self.template.posterior.bgm = slicer.vtkMRMLScalarVolumeNode()
        # ...
        self.scene.StartState(slicer.vtkMRMLScene().BatchProcessState)
        self.scene.AddNodeNoModify(self.template.correctedT1)
        self.scene.AddNodeNoModify(self.template.correctedT2)
        self.scene.AddNodeNoModify(self.template.posterior.air)
        # TODO: Remove old images
        # TODO: Add nodes to slice views
        # TODO: Set view characteristics of volumes in slice views
        self.scene.EndState(slicer.vtkMRMLScene().BatchProcessState)

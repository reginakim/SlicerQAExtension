import os
from __main__ import ctk
from __main__ import qt
from __main__ import slicer
from __main__ import vtk

if not '__file__' in locals():
    __file__ = os.path.join(os.getcwd(), 'SlicerDerivedImageEval.py')
    print "__file__ = %s" % __file__

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
        # Evaluation subsection
        self.evaluationCollapsibleButton = ctk.ctkCollapsibleButton()
        self.evaluationCollapsibleButton.text = 'Evaluation input'
        # Load UI file
        uiloader = qt.QUiLoader()
        qfile = qt.QFile('/Users/dmwelch/Development/src/extensions/SlicerDerivedImageEval/Resources/UI/evaluationPrototype.ui')
        qfile.open(qt.QFile.ReadOnly)
        evalFrame = uiloader.load(qfile)
        qfile.close()
        self.evaluationCollapsibleButton.setLayout(evalFrame.findChild('QVBoxLayout'))
        self.layout.addWidget(self.evaluationCollapsibleButton)
        # Get buttons in UI file
        self.buttons = {}
        pushButtons = self.evaluationCollapsibleButton.findChildren('QPushButton')
        for button in pushButtons:
            self.buttons[button.objectName] = button
        self.putamenLeft = self.buttons['putamenLeftButton']
        self.nextButton = self.buttons['nextButton']
        self.nextButton.connect('clicked()', self.logic.onNextButtonClicked)
        self.previousButton = self.buttons['previousButton']
        self.previousButton.connect('clicked()', self.logic.onPreviousButtonClicked)
        # Get radios in UI file
        self.radios = {}
        radioButtons = self.evaluationCollapsibleButton.findChildren('QRadioButton')
        for button in radioButtons:
            self.radios[button.objectName] = button
        self.putamenLeftGoodButton = self.radios['putamenLeftGoodButton']
        self.putamenLeftBadButton = self.radios['putamenLeftBadButton']
        self.putamenLeft.connect('clicked()', self.onRegionButtonClicked)

        # Add vertical spacer
        self.layout.addStretch(1)

        # Set local var as instance attribute
        # self.batchFilesButton = batchFilesButton

    def onBatchFilesButtonClicked(self):
        fileList = self.logic.batchList


    def onRegionButtonClicked(self):
        if self.putamenLeft.text == 'Putamen, Left':
            labelNode = slicer.util.getNode('L_Putamen')
            compositeNodes = slicer.util.getNodes('vtkMRMLSliceCompositeNode*')
            for compositeNode in compositeNodes.values():
                compositeNode.SetLabelVolumeID(labelNode.GetID())
                compositeNode.SetLabelOpacity(1.0)
            sliceNodes = slicer.util.getNodes('vtkMRMLSliceNode*')
            for sliceNode in sliceNodes.values():
                sliceNode.UseLabelOutlineOn()
            good = self.putamenLeftGoodButton
            good.setEnabled(True)
            bad = self.putamenLeftBadButton
            bad.setEnabled(True)

    def onReload(self, moduleName="SlicerDerivedImageEval"):
        """ Generic development reload method for any scripted module.
            ModuleWizard will subsitute correct default moduleName.
            DEVELOPMENT TOOL
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
        self.database = None
        self.experiment = None
        self.batchList = None
        self.batchSize = 21
        self.testingData()
        self.onGetBatchFilesClicked() # TESTING
        self.count = 0

    def onGetBatchFilesClicked(self):
        import os
        # TODO: import sqlite3
        batchList = []
        if True:  # Testing is on
            batchFile = '/Users/dmwelch/Development/src/extensions/SlicerDerivedImageEval/Testing/database.csv'
            t1AverageSuffix = '/TissueClassify/t1_average_BRAINSABC.nii.gz'
            t2AverageSuffix = '/TissueClassify/t2_average_BRAINSABC.nii.gz'
            leftPutamenSuffix = '/BRAINSCut/l_Putamen_seg.nii.gz'
            fid = open(batchFile, 'r')
            try:
                entries = fid.readlines()
            except:
                raise
            finally:
                fid.close()
            batchList = []
            count = 0
            for entry in entries:
                base, subject, session = entry.split(',')
                batchList.append({})
                # print count, base, subject, session
                # print batchList
                batchList[count]['subject'] = subject
                batchList[count]['session'] = session
                batchList[count]['T1'] = os.path.join(base, subject, session, t1AverageSuffix)
                batchList[count]['T2'] = os.path.join(base, subject, session, t1AverageSuffix)
                batchList[count]['leftPutamen'] = os.path.join(base, subject, session, leftPutamenSuffix)
                count += 1
            self._getLockedFileList(batchList)

    def _getLockedFileList(self, lockedFileList=None):
        """ If the testing mode is on, lockedFileList ~= None """
        if lockedFileList is None:
            import imp
            try:
                import sqlite3
            except ImportError:
                fp, pathname, description = imp.find_module('sqlite3')
                try:
                    return imp.load_module('sqlite3', fp, pathname, description)
                finally:
                    # Since we may exit via an exception, close fp explicitly.
                    if fp:
                        fp.close()
            # Get file list from SQL and lock entries from others
            pass
        else:
            # Testing is on
            self.batchList = lockedFileList

    def testingData(self, batchDict=None):
        """ Load some default data for development and set up a viewing scenario for it.
        """
        import os
        if not os.environ['USER'] == 'dmwelch':
            return 0
        # TODO: Make a better dialog box here
        dialogFrame = qt.QFrame()
        dialogLayout = qt.QVBoxLayout()
        dataDialog = qt.QLabel();
        dataDialog.setText('Loading files...');
        dataDialog.setLayout(dialogLayout)
        dataDialog.show()
        if not slicer.util.getNodes('T1_Average*'):
            import os
            fileName = os.environ['HOME'] + '/Development/src/extensions/SlicerDerivedImageEval/Testing/Data/Experiment/0131/89205/TissueClassify/t1_average_BRAINSABC.nii.gz'
            volumeNode = slicer.util.loadVolume(fileName, properties={'name':"T1_Average"})
        elif not batchDict is None:
            fileName = batchDict['T1']
            volumeNode = slicer.util.loadVolume(fileName, properties={'name':"T1_Average"})
        if not slicer.util.getNodes('T2_Average*'):
            import os
            fileName = os.environ['HOME'] + '/Development/src/extensions/SlicerDerivedImageEval/Testing/Data/Experiment/0131/89205/TissueClassify/t2_average_BRAINSABC.nii.gz'
            volumeNode = slicer.util.loadVolume(fileName, properties={'name':"T2_Average"})
        elif not batchDict is None:
            fileName = batchDict['T2']
            volumeNode = slicer.util.loadVolume(fileName, properties={'name':"T2_Average"})
        # if not slicer.util.getNodes('BRAINS_label*'):
        #     import os
        #     fileName = os.environ['HOME'] + '/Development/src/extensions/SlicerDerivedImageEval/Testing/Data/Experiment/0131/89205/TissueClassify/brain_label_seg.nii.gz'
        #     # print "This is the label image: %s" % fileName
        #     volumeNode = slicer.util.loadLabelVolume(fileName, properties={'name':"BRAINS_label"})
        if not slicer.util.getNodes('L_Putamen*'):
            import os
            fileName = os.environ['HOME'] + '/Development/src/extensions/SlicerDerivedImageEval/Testing/Data/Experiment/0131/89205/BRAINSCut/l_Putamen_seg.nii.gz'
            volumeNode = slicer.util.loadLabelVolume(fileName, properties={'name':"L_Putamen"})
        elif not batchDict is None:
            fileName = batchDict['leftPutamen']
            volumeNode = slicer.util.loadVolume(fileName, properties={'name':"L_Putamen"})
        dataDialog.close()
        # Get the image nodes
        t1Average = slicer.util.getNode('T1_Average')
        t2Average = slicer.util.getNode('T2_Average')
        # brainsLabel = slicer.util.getNode('BRAINS_label')
        leftPutamen = slicer.util.getNode('L_Putamen')
        # Set up template scene
        compositeNodes = slicer.util.getNodes('vtkMRMLSliceCompositeNode*')
        for compositeNode in compositeNodes.values():
            compositeNode.SetBackgroundVolumeID(t1Average.GetID())
            compositeNode.SetForegroundVolumeID(t2Average.GetID())
            compositeNode.SetForegroundOpacity(0.0)
        applicationLogic = slicer.app.applicationLogic()
        applicationLogic.FitSliceToAll()

    def onNextButtonClicked(self):
        count = self.count + 1
        if count > self.batchSize:
            self.count = count
        else:
            self.count = 0
        self.currentSession = self.batchFileList[count]['session']
        self.testingData(self.batchFileList[count]) # BUG: Reloads files when flipping over to zero

    def onPreviousButtonClicked(self):
        count = self.count - 1
        if count < 0:
            self.count = count
        else:
            self.count = self.batchSize
        self.currentSession = self.batchFileList[count]['session']
        self.testingData(self.batchFileList[count]) # BUG: Reloads files when flipping over to zero

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

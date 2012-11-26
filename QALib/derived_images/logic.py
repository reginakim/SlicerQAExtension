import re
import os
import warnings
warn = warnings.warn

from __main__ import ctk
from __main__ import qt
from __main__ import slicer
from __main__ import vtk

from . import __slicer_module__, postgresDatabase

try:
    import ConfigParser as cParser
    # import logging
    # import logging.handlers
except ImportError:
    print "External modules not found!"
    raise ImportError


class DerivedImageQALogic(object):
    """ Logic class to be used 'under the hood' of the evaluator """
    def __init__(self, widget, test=False):
        self.widget = widget
        self.regions = self.widget.regions
        self.images = self.widget.images
        self.qaValueMap = {'good':'1', 'bad':'0', 'follow up':'-1'}
        self.colorTable = "IPL-BrainAtlas-ColorFile.txt"
        self.colorTableNode = None
        self.user_id = None
        self.database = None
        self.batchSize = 1
        self.batchRows = None
        self.count = 0 # Starting value
        self.maxCount = 0
        self.currentSession = None
        self.currentValues = (None,)*len(self.images + self.regions)
        self.sessionFiles = {}
        self.testing = test
        self.setup()

    def setup(self):
        self.createColorTable()
        config = cParser.SafeConfigParser()
        if self.testing:
            configFile = os.path.join(__slicer_module__, 'test.cfg')
            self.user_id = 'user1'
        else:
            configFile = os.path.join(__slicer_module__, 'autoworkup.cfg')
            self.user_id = os.environ['USER']
        if not os.path.exists(configFile):
            raise IOError("File {0} not found!".format(configFile))
        config.read(configFile)
        host = config.get('Postgres', 'Host')
        port = config.getint('Postgres', 'Port')
        database = config.get('Postgres', 'Database')
        db_user = config.get('Postgres', 'User')
        password = config.get('Postgres', 'Password') ### TODO: Use secure password handling (see RunSynchronization.py in phdxnat project)
        #        import hashlib as md5
        #        md5Password = md5.new(password)
        self.database = postgresDatabase(host, port, db_user, database, password,
                                         self.user_id, self.batchSize)

    def createColorTable(self):
        """
        """
        self.colorTableNode = slicer.vtkMRMLColorTableNode()
        self.colorTableNode.SetFileName(os.path.join(__slicer_module__, 'Resources', 'ColorFile', self.colorTable))
        self.colorTableNode.SetName(self.colorTable[:-4])
        storage = self.colorTableNode.CreateDefaultStorageNode()
        slicer.mrmlScene.AddNode(storage)
        self.colorTableNode.AddAndObserveStorageNodeID(storage.GetID())
        slicer.mrmlScene.AddNode(self.colorTableNode)
        storage.SetFileName(self.colorTableNode.GetFileName())
        storage.SetReadState(True)
        storage.ReadData(self.colorTableNode, True)

    def addEntryToColorTable(self, buttonName):
        lTable = self.colorTableNode.GetLookupTable()
        colorIndex = self.colorTableNode.GetColorIndexByName(buttonName)
        color = lTable.GetTableValue(colorIndex)
        self.colorTableNode.AddColor(buttonName, *color)

    def selectRegion(self, buttonName):
        """ Load the outline of the selected region into the scene
        """
        nodeName = self.constructLabelNodeName(buttonName)
        labelNode = slicer.util.getNode(nodeName)
        if labelNode.GetLabelMap():
            labelNode.GetDisplayNode().SetAndObserveColorNodeID(self.colorTableNode.GetID())
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
        if self.testing:
            recordID = str(self.batchRows[self.count]['record_id'])
        else:
            recordID = self.batchRows[self.count][0]
        values = (recordID,) + evaluations
        try:
            if self.testing:
                self.database.writeAndUnlockRecord(values)
            else:
                self.database.writeReview(values)
                self.database.unlockRecord('R', recordID)
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

    def setCurrentSession(self):
        self.currentSession = self.sessionFiles['session']
        self.widget.currentSession = self.currentSession

    def constructFilePaths(self):
        row = self.batchRows[self.count]
        sessionFiles = {}
        # Due to a poor choice in our database creation, the 'location' column is the 6th, NOT the 2nd
        baseDirectory = os.path.join(row[5], row[1], row[2], row[3], row[4])
        sessionFiles['session'] = row[4]
        sessionFiles['record_id'] = row[0]
        tissueDirectory = os.path.join(baseDirectory, 'TissueClassify', 'BABC') # New directory structure 2012-11-26
        if not os.exist.(tissueDirectory):
            tissueDirectory = os.path.join(baseDirectory, 'TissueClassify') # Old directory structure (pre- 2012-11-26)
        sessionFiles['t1_average'] = os.path.join(tissueDirectory, 't1_average_BRAINSABC.nii.gz')
        sessionFiles['t2_average'] = os.path.join(tissueDirectory, 't2_average_BRAINSABC.nii.gz')
        for regionName in self.regions:
            if regionName == 'labels_tissue':
                sessionFiles['labels_tissue'] = os.path.join(tissueDirectory, 'brain_label_seg.nii.gz')
            else:
                fileName = self._getLabelFileNameFromRegion(regionName)
                sessionFiles[regionName] = os.path.join(baseDirectory, 'Segmentations', fileName)
                if not os.path.exists(sessionFiles[regionName]):
                    sessionFiles[regionName] = os.path.join(baseDirectory, 'Segmentations', fileName.lower())
                    if not os.path.exists(sessionFiles[regionName]):
                        sessionFiles[regionName] = os.path.join(baseDirectory, 'BRAINSCut', fileName)
                        if not os.path.exists(sessionFiles[regionName]):
                            sessionFiles[regionName] = os.path.join(baseDirectory, 'BRAINSCut', fileName.lower())
                            if not os.path.exists(sessionFiles[regionName]):
                                warn("No output files were found at %s in /Segmentations or /BRAINSCut for region %s. Skipping..." %  (baseDirectory, regionName))
        self.sessionFiles = sessionFiles
        # Verify that the files exist
        for key in self.images + self.regions:
            if not os.path.exists(self.sessionFiles[key]):
                print "File not found: %s\nSkipping session..." % self.sessionFiles[key]
                # raise IOError("File not found!\nFile: %s" % self.sessionFiles[key])
                self.database.unlockRecord('M', self.sessionFiles['record_id'])
                self.onGetBatchFilesClicked()
                # TODO: Generalize for a batch size > 1
                # for count in range(self.maxCount - self.count):
                #     print "This is the count: %d" % count

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
            volumeLogic.AddArchetypeScalarVolume(self.sessionFiles['t1_average'], t1NodeName, 0)
            if slicer.util.getNode(t1NodeName) is None:
                raise IOError("Could not load session file for T1! File: %s" % self.sessionFiles['t1_average'])
            t1VolumeNode = slicer.util.getNode(t1NodeName)
            t1VolumeNode.CreateDefaultDisplayNodes()
            t1VolumeNode.GetDisplayNode().AutoWindowLevelOn()
        t2NodeName = '%s_t2_average' % self.currentSession
        t2VolumeNode = slicer.util.getNode(t2NodeName)
        if t2VolumeNode is None:
            volumeLogic.AddArchetypeScalarVolume(self.sessionFiles['t2_average'], t2NodeName, 0)
            if slicer.util.getNode(t2NodeName) is None:
                raise IOError("Could not load session file for T2! File: %s" % self.sessionFiles['t2_average'])
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
            self.writeToDatabase(values)
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
        self.writeToDatabase(values)
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
        self.database.unlockRecord('U')

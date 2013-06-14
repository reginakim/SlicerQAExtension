try:
    import logging
    import logging.handlers
    import os
    import ConfigParser as cParser
    from . import __slicer_module__, postgresDatabase

    from __main__ import ctk
    from __main__ import qt
    from __main__ import slicer
    from __main__ import vtk
except ImportError:
    print "External modules not found!"
    # raise ImportError


class DerivedImageQALogic(object):
    """ Logic class to be used 'under the hood' of the evaluator """
    def __init__(self, widget, test=True):
        self.widget = widget
        self.logging = self.widget.logging
        self.regions = self.widget.regions
        self.images = self.widget.images
        self.qaValueMap = {'good':'1', 'bad':'0', 'follow up':'-1'}
        self.colorTable = "IPL-BrainAtlas-ColorFile.txt"
        self.colorTableNode = None
        self.user_id = None
        self.database = None
        self.config = None
        self.batchSize = 1
        self.batchRows = None
        self.count = 0 # Starting value
        self.maxCount = 0
        self.currentSession = None
        self.currentValues = (None,)*len(self.images + self.regions)
        self.sessionFiles = {}
        self.testing = test
        if self.testing:
            self.logging.info("TESTING is ON")
        self.setup()

    def setup(self):
        self.logging.debug("call")
        # self.createColorTable()
        config = cParser.SafeConfigParser()
        self.config = cParser.SafeConfigParser()
        logicConfig = os.path.join(__slicer_module__, 'derived_images.cfg')
        if self.testing:
            databaseConfig = os.path.join(__slicer_module__, 'testdatabase.cfg')
            self.logging.info("TESTING: Setting database configuration to %s", databaseConfig)
            self.user_id = 'test'
            self.logging.info("TESTING: Setting database user to %s", self.user_id)
        else:
            databaseConfig = os.path.join(__slicer_module__, 'autoworkup.cfg')
            self.logging.info("Setting database configuration to %s", databaseConfig)
            self.user_id = os.environ['USER']
            self.logging.info("logic.py: Setting database user to %s", self.user_id)
        for configFile in [databaseConfig, logicConfig]:
            if not os.path.exists(configFile):
                raise IOError("File {0} not found!".format(configFile))
        config.read(databaseConfig)
        host = config.get('Postgres', 'Host')
        port = config.getint('Postgres', 'Port')
        database = config.get('Postgres', 'Database')
        db_user = config.get('Postgres', 'User')
        if self.testing:
            password = 'test'
        else:
            import keyring
            password = keyring.get_password()
        self.database = postgresDatabase(host, port, db_user, database, password,
                                         self.user_id, self.batchSize, logging=self.logging,
                                         dataTable=config.get('Postgres', 'DataTable'), 
                                         reviewTable=config.get('Postgres', 'ReviewTable'))
        self.config.read(logicConfig)
        self.logging.info("logic.py: Reading logic configuration from %s", logicConfig)


    def selectRegion(self, buttonName):
        """ Load the outline of the selected region into the scene
        """
        self.logging.debug("call")
        nodeName = self.constructLabelNodeName(buttonName)
        if nodeName == '':
            return -1
        labelNode = slicer.util.getNode(nodeName)
        if labelNode.GetLabelMap():
            #labelNode.GetDisplayNode().SetAndObserveColorNodeID(self.colorTableNode.GetID())
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
        self.logging.debug("call")
        if not self.currentSession is None:
            nodeName = '_'.join([self.currentSession, buttonName])
            return nodeName
        return ''

    def onCancelButtonClicked(self):
        self.logging.debug("call")
        # TODO: Populate this function
        #   onNextButtonClicked WITHOUT the write to database
        self.logging.info("Cancel button clicked!")

    def writeToDatabase(self, evaluations):
        self.logging.debug("call")
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
            self.logging.error("Error writing to database for record %d", recordID)
            raise

    def _getLabelFileNameFromRegion(self, regionName):
        self.logging.debug("call")
        try:
            region, side = regionName.split('_')
            fileName = '_'.join([side[0], region.capitalize(), 'seg.nii.gz'])
        except ValueError:
            region = regionName
            fileName = '_'.join([region, 'seg.nii.gz'])
        return fileName

    def onGetBatchFilesClicked(self):
        """ """
        self.logging.debug("call")
        self.count = 0
        self.batchRows = self.database.lockAndReadRecords()
        self.maxCount = len(self.batchRows)
        self.constructFilePaths()
        self.setCurrentSession()
        self.loadData()


    def setCurrentSession(self):
        self.logging.debug("call")
        self.currentSession = self.sessionFiles['session']
        self.widget.currentSession = self.currentSession

    def constructFilePaths(self):
        """
        >>> import DerivedImagesQA as diqa
        External modules not found!
        /Volumes/scratch/welchdm/src/Slicer-extensions/SlicerQAExtension
        External modules not found!
        >>> test = diqa.DerivedImageQAWidget(None, True)
        Testing logic is ON
        >>> test.logic.count = 0 ### HACK
        >>> test.logic.batchRows = [['rid','exp', 'site', 'sbj', 'ses', 'loc']] ### HACK
        >>> test.logic.constructFilePaths()
        Test: loc/exp/site/sbj/ses/TissueClassify/t1_average_BRAINSABC.nii.gz
        File not found for file: t2_average
        Skipping session...
        Test: loc/exp/site/sbj/ses/TissueClassify/t1_average_BRAINSABC.nii.gz
        File not found for file: t1_average
        Skipping session...
        Test: loc/exp/site/sbj/ses/TissueClassify/fixed_brainlabels_seg.nii.gz
        File not found for file: labels_tissue
        Skipping session...
        Test: loc/exp/site/sbj/ses/DenoisedRFSegmentations/l_caudate_seg.nii.gz
        File not found for file: caudate_left
        Skipping session...
        Test: loc/exp/site/sbj/ses/DenoisedRFSegmentations/r_caudate_seg.nii.gz
        File not found for file: caudate_right
        Skipping session...
        Test: loc/exp/site/sbj/ses/DenoisedRFSegmentations/l_accumben_seg.nii.gz
        File not found for file: accumben_left
        Skipping session...
        Test: loc/exp/site/sbj/ses/DenoisedRFSegmentations/r_accumben_seg.nii.gz
        File not found for file: accumben_right
        Skipping session...
        Test: loc/exp/site/sbj/ses/DenoisedRFSegmentations/l_putamen_seg.nii.gz
        File not found for file: putamen_left
        Skipping session...
        Test: loc/exp/site/sbj/ses/DenoisedRFSegmentations/r_putamen_seg.nii.gz
        File not found for file: putamen_right
        Skipping session...
        Test: loc/exp/site/sbj/ses/DenoisedRFSegmentations/l_globus_seg.nii.gz
        File not found for file: globus_left
        Skipping session...
        Test: loc/exp/site/sbj/ses/DenoisedRFSegmentations/r_globus_seg.nii.gz
        File not found for file: globus_right
        Skipping session...
        Test: loc/exp/site/sbj/ses/DenoisedRFSegmentations/l_thalamus_seg.nii.gz
        File not found for file: thalamus_left
        Skipping session...
        Test: loc/exp/site/sbj/ses/DenoisedRFSegmentations/r_thalamus_seg.nii.gz
        File not found for file: thalamus_right
        Skipping session...
        Test: loc/exp/site/sbj/ses/DenoisedRFSegmentations/l_hippocampus_seg.nii.gz
        File not found for file: hippocampus_left
        Skipping session...
        Test: loc/exp/site/sbj/ses/DenoisedRFSegmentations/r_hippocampus_seg.nii.gz
        File not found for file: hippocampus_right
        Skipping session...
        """
        self.logging.debug("call")
        row = self.batchRows[self.count]
        sessionFiles = {}
        # Due to a poor choice in our database creation, the 'location' column is the 6th, NOT the 2nd

        sessionFiles['session'] = row[2]
        sessionFiles['record_id'] = row[0]

        baseDirectory = os.path.join(row[3], row[1], sessionFiles['session']) 
        self.logging.debug( "THIS IS BASEDIRECTORY:::" + baseDirectory )
        for image in self.images + self.regions:
            sessionFiles[image] = None
            imageDirs = eval(self.config.get(image, 'directories'))
            imageFiles = eval(self.config.get(image, 'filenames'))
            for _dir in imageDirs:
                for _file in imageFiles:
                    temp = os.path.join(baseDirectory, _dir, _file)
                    if os.path.exists(temp):
                        sessionFiles[image] = temp
                        break ; break
                    elif self.testing:
                        self.logging.debug("TESTING: \nimage: %s\nfullPath: %s", image, temp)
                    else:
                        self.logging.debug("File not found: %s", temp)
            if sessionFiles[image] is None:
                self.logging.info("Skipping session %s", sessionFiles['session'])
                # raise IOError("File not found!\nFile: %s" % sessionFiles[image])
                if not self.testing:
                    self.database.unlockRecord('M', sessionFiles['record_id'])
                    self.logging.debug("image = %s", image)
                break
        if None in sessionFiles.values():
            self.logging.debug("'None' value in sessionFiles - recursive call initiated")
            self.onGetBatchFilesClicked()
            # TODO: Generalize for a batch size > 1
            # for count in range(self.maxCount - self.count):
            #     self.logging.debug("logic.py:This is the count: %d" % count
        else:
            self.sessionFiles = sessionFiles


    def loadData(self):
        """ Load some default data for development and set up a viewing scenario for it.
        """
        self.logging.debug("call")
        dataDialog = qt.QPushButton();
        dataDialog.setText('Loading files for session %s...' % self.currentSession);
        dataDialog.show()
        volumeLogic = slicer.modules.volumes.logic()
        t1NodeName = '%s_t1_average' % self.currentSession
        t1VolumeNode = slicer.util.getNode(t1NodeName)
        if t1VolumeNode is None:
            self.logging.debug("%s = %s", 't1_average', self.sessionFiles['t1_average'])
            try:
                volumeLogic.AddArchetypeScalarVolume(self.sessionFiles['t1_average'], t1NodeName, 0, None)
            except TypeError:
                volumeLogic.AddArchetypeScalarVolume(self.sessionFiles['t1_average'], t1NodeName, 0)
            if slicer.util.getNode(t1NodeName) is None:
                self.logging.error("Could not load session file for T1: %s", self.sessionFiles['t1_average'])
            t1VolumeNode = slicer.util.getNode(t1NodeName)
            t1VolumeNode.CreateDefaultDisplayNodes()
            t1VolumeNode.GetDisplayNode().AutoWindowLevelOn()
        t2NodeName = '%s_t2_average' % self.currentSession
        t2VolumeNode = slicer.util.getNode(t2NodeName)
        if t2VolumeNode is None:
            pass
            #self.logging.debug("%s = %s", 't2_average', self.sessionFiles['t2_average'])
            #try:
            #    volumeLogic.AddArchetypeScalarVolume(self.sessionFiles['t2_average'], t2NodeName, 0, None)
            #except TypeError:
            #    volumeLogic.AddArchetypeScalarVolume(self.sessionFiles['t2_average'], t2NodeName, 0)
            #if slicer.util.getNode(t2NodeName) is None:
            #    self.logging.error("Could not load session file for T2: %s", self.sessionFiles['t2_average'])
            #t2VolumeNode = slicer.util.getNode(t2NodeName)
            #t2VolumeNode.CreateDefaultDisplayNodes()
            #t2VolumeNode.GetDisplayNode().AutoWindowLevelOn()
        for region in self.regions:
            regionNodeName = '%s_%s' % (self.currentSession, region)
            regionNode = slicer.util.getNode(regionNodeName)
            if regionNode is None:
                self.logging.debug("%s = %s", region, self.sessionFiles[region])
                try:
                    volumeLogic.AddArchetypeScalarVolume(self.sessionFiles[region], regionNodeName, 1, None)
                except TypeError:
                    volumeLogic.AddArchetypeScalarVolume(self.sessionFiles[region], regionNodeName, 1)
                if slicer.util.getNode(regionNodeName) is None:
                    self.logging.error("Could not load session file for region %s! File: %s", region, self.sessionFiles[region])
                regionNode = slicer.util.getNode(regionNodeName)
                displayNode = slicer.vtkMRMLLabelMapVolumeDisplayNode()
                slicer.mrmlScene.AddNode(displayNode)
                regionNode.SetAndObserveNthDisplayNodeID(0, displayNode.GetID())
        dataDialog.close()

    def loadBackgroundNodeToMRMLScene(self, volumeNode):
        # Set up template scene
        self.logging.debug("call")
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
        self.logging.debug("call")
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
        self.logging.debug("call")
        try:
            evaluations = self.getEvaluationValues()
        except:
            return
        columns = ('record_id',) + self.regions
        values = (self.sessionFiles['record_id'], ) + evaluations
        try:
            self.writeToDatabase(values)
        except sqlite3.OperationalError:
            self.logging.error("SQL Error")
        count = self.count + 1
        if count <= self.maxCount - 1:
            self.count = count
        else:
            self.count = 0
        self.loadNewSession()
        self.widget.resetWidget()

    def onPreviousButtonClicked(self):
        self.logging.debug("call")
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
        self.logging.debug("call")
        self.constructFilePaths()
        self.setCurrentSession()
        self.loadData()

    def exit(self):
        self.logging.debug("call")
        self.database.unlockRecord('U')

# if __name__ == '__main__':
#     import doctest
#     doctest.testmod()

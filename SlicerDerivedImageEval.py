#! /usr/bin/env python
import os

from __main__ import ctk
from __main__ import qt
from __main__ import slicer
from __main__ import vtk

import module_locator
import logic

globals()['__file__'] = module_locator.module_path()

### TODO: Add logging
# try:
#     import logging
#     import logging.handlers
# except ImportError:
#     print "External modules not found!"
#     raise ImportError

class SlicerDerivedImageEval:
    def __init__(self, parent):
        parent.title = 'DWI Image Evaluation'
        parent.categories = ['Work in Progress']
        parent.dependencies = ['Volumes']
        parent.contributors = ['Dave Welch (UIowa), Hans Johnson (UIowa)']
        parent.helpText = """Image evaluation module for use in the UIowa PINC lab"""
        parent.acknowledgementText = """ """
        self.parent = parent


class SlicerDerivedImageEvalWidget:
    def __init__(self, parent=None):
        self.images = ('DWI',)
        self.artifacts = ('airTissue', 'cropping', 'dropOut', 'interleave', 'missingData')
        self.lobes = ('frontal', 'occipital', 'parietal', 'temporal')
        self.currentSession = None
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
            self.logic = logic.SlicerDerivedImageEvalLogic(self)
            self.setup()
            self.parent.show()
        else:
            self.parent = parent
            self.layout = self.parent.layout()
            self.logic = logic.SlicerDerivedImageEvalLogic(self, test=False)

    def setup(self):
        self.followUpDialog = self.loadUIFile('Resources/UI/followUpDialog.ui')
        self.clipboard = qt.QApplication.clipboard()
        self.textEditor = self.followUpDialog.findChild("QTextEdit", "textEditor")
        buttonBox = self.followUpDialog.findChild("QDialogButtonBox", "buttonBox")
        buttonBox.connect("accepted()", self.grabNotes)
        buttonBox.connect("rejected()", self.cancelNotes)
        # Evaluation subsection
        self.imageQAWidget = self.loadUIFile('Resources/UI/imageQACollapsibleButton.ui')
        qaLayout = qt.QVBoxLayout(self.imageQAWidget)
        qaLayout.addWidget(self.imageQAWidget.findChild("QFrame", "titleFrame"))
        qaLayout.addWidget(self.imageQAWidget.findChild("QFrame", "tableVLine"))
        # Create review buttons on the fly
        for image in self.images:
            reviewButton = self.reviewButtonFactory(image)
            qaLayout.addWidget(reviewButton)
        # batch button
        self.nextButton = qt.QPushButton()
        self.nextButton.setText('Get next DWI')
#        self.nextButton.connect('clicked(bool)', self.onGetBatchFilesClicked)
        self.dwiArtifactWidget = self.loadUIFile('Resources/UI/dwiArtifactWidget.ui')
        qaLayout.addWidget(self.dwiArtifactWidget)
        qaLayout.addWidget(self.nextButton)
        self.dwiWidget = slicer.modulewidget.qSlicerDiffusionWeightedVolumeDisplayWidget()
        qaLayout.addWidget(self.dwiWidget)
        # Add all to layout
        self.layout.addWidget(self.dwiWidget)
        self.layout.addWidget(self.imageQAWidget)
        self.layout.addStretch(1)
        self.enableRadios(self.images[0])
        self.logic.onGetBatchFilesClicked()

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
        # TODO: Convert push button to label
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
            text = " ".join([parsed[1], parsed[0]])
        else:
            text = parsed[0]
        return text

    def connectSessionButtons(self):
        """ Connect the session navigation buttons to their logic """
        # TODO: Connect buttons
        ### self.nextButton.connect('clicked()', self.logic.onNextButtonClicked)
        ### self.previousButton.connect('clicked()', self.logic.onPreviousButtonClicked)
        self.quitButton.connect('clicked()', self.exit)

    def enableRadios(self, image):
        """ Enable the radio buttons that match the given region name """
        self.imageQAWidget.findChild("QWidget", image + "_radioWidget").setEnabled(True)
        for suffix in ("_good", "_bad", "_followUp"):
            radio = self.imageQAWidget.findChild("QRadioButton", image + suffix)
            radio.setShortcutEnabled(True)
            radio.setCheckable(True)
            radio.setEnabled(True)

    def resetRadioWidgets(self):
        """ Disable and reset all radio buttons in the widget """
        radios = self.imageQAWidget.findChildren("QRadioButton")
        for radio in radios:
            radio.setCheckable(False)
        checkboxess = self.dwiArtifactWidget.findChildren("QCheckBox")
        for checkbox in checkboxes:
            checkbox.isChecked(False)

    def getRadioValues(self):
        values = ()
        needsFollowUp = False
        radios = self.imageQAWidget.findChildren("QRadioButton")
        for image in self.images:
            for radio in radios:
                if radio.objectName.find(image) > -1 and radio.checked:
                    if radio.objectName.find("_good") > -1:
                        values = values + (1,)
                    elif radio.objectName.find("_bad") > -1:
                        values = values + (0,)
                    elif radio.objectName.find("_followUp") > -1:
                        values = values + (-1,)
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

    def getCheckboxValues(self):
        values = ()
        needsFollowUp = False
        checkboxes = self.dwiArtifactWidget.findChildren('QCheckBox')
        for artifact in self.artifacts:
            for lobe in self.lobes:
                for cBox in checkboxes:
                    if cBox.objectName == artifact + '_' + lobe:
                        if cBox.checked:
                            values = values + ('t',)
                        else:
                            values = values + ('f',)
        return values

    def resetWidget(self):
        self.resetRadioWidgets()

    def grabNotes(self):
        self.notes = None
        self.notes = str(self.textEditor.toPlainText())
        # TODO: Format notes
        ### if self.notes = '':
        ###     self.followUpDialog.show()
        ###     self.textEditor.setText("A comment is required!")
        self.textEditor.clear()

    def cancelNotes(self):
        # TODO:
        pass

    def onGetBatchFilesClicked(self):
        values = self.getCheckboxValues() + self.getRadioValues()
        if len(values) >= len(self.images) + 4*4: ### HACK
            self.logic.writeToDatabase(values)
            self.resetWidget()
            self.logic.onGetBatchFilesClicked()
        else:
            # TODO: Handle this case intelligently
            print "Not enough values for the required columns!"


    def exit(self):
        """ When Slicer exits, prompt user if they want to write the last evaluation """
        values = self.getRadioValues()
        if len(values) >= len(self.images) + 4*4: ### HACK
            # TODO: Write a confirmation dialog popup
            pass ### HACK ###
#            self.logic.writeToDatabase(values)
        elif len(values) == 0:
            pass ### HACK ###
#            self.logic.exit()
        else:
            # TODO: write a prompt window
            print "Not enough values for the required columns!"
#            self.logic.exit()
            # TODO: clear scene

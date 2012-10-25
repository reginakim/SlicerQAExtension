#! /usr/bin/env python
import os

from __main__ import ctk
from __main__ import qt
from __main__ import slicer
from __main__ import vtk

from QALib.dwi_preprocess import *
from QALib.dwi_preprocess import __slicer_module__

### TODO: Add logging
# try:
#     import logging
#     import logging.handlers
# except ImportError:
#     print "External modules not found!"
#     raise ImportError

class DWIPreprocessingQA:
    def __init__(self, parent):
        parent.title = 'DWI Preprocessing'
        parent.categories = ['Quality Assurance']
        parent.dependencies = ['Volumes']
        parent.contributors = ['Dave Welch (UIowa)']
        parent.helpText = """DWI image evaluation module for use in the UIowa PINC lab"""
        parent.acknowledgementText = """ """
        self.parent = parent


class DWIPreprocessingQAWidget:
    def __init__(self, parent=None):
        self.images = ('DWI',)
        self.artifacts = ('susceptibility', 'cropping', 'dropOut', 'interlace', 'missingData', 'miscComments')
        self.lobes = ('frontal', 'temporal', 'parietal', 'occipital', 'cerebellum')
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
            self.logic = DWIPreprocessingQALogic(self)
            self.setup()
            self.parent.show()
        else:
            self.parent = parent
            self.layout = self.parent.layout()
            self.logic = DWIPreprocessingQALogic(self)

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
        self.nextButton.connect('clicked(bool)', self.onGetBatchFilesClicked)
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
        qfile = qt.QFile(os.path.join(__slicer_module__, fileName))
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
            radio.setChecked(False)
        checkboxes = self.dwiArtifactWidget.findChildren("QCheckBox")
        for checkbox in checkboxes:
            checkbox.setChecked(False)

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
        for artifact in self.artifacts:
            if artifact in ['missingData', 'miscComment']:
                objectName = artifact + 'LineEdit'
                lineEdit = self.dwiArtifactWidget.findChild('QLineEdit', objectName)
                notes = lineEdit.text
                if notes is None:
                    notes = 'Null'
                values = values + (lineEdit.text,)
            elif artifact in ['interlace']:
                objectName = artifact + '_true'
                checkBox = self.dwiArtifactWidget.findChild('QCheckBox', objectName)
                if checkBox.checked:
                    values = values + (True,)
                else:
                    values = values + (False,)
            else:
                for lobe in self.lobes:
                    objectName = artifact + '_' + lobe
                    checkBox = self.dwiArtifactWidget.findChild('QCheckBox', objectName)
                    if checkBox is None:
                        values = values # + ('NULL',)
                    elif checkBox.checked:
                        values = values + (True,)
                    else:
                        values = values + (False,)
        return values

    def resetWidget(self):
        self.resetRadioWidgets()
        ### TODO: self.resetDWIwidget()

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


    def getValues(self):
        radioValues = self.getRadioValues()
        if 0 in radioValues or -1 in radioValues:
            print 'We need DWI evaluation input!'
        else:
            print 'We do not need DWI review'
        values = self.getCheckboxValues() + radioValues
        return values

    def checkValues(self):
        values = self.getValues()
        if len(values) >= len(self.images) + ((len(self.artifacts) - 2) * len(self.lobes)) + 1:
            print values ### HACK
            self.logic.writeToDatabase(values)
            self.resetWidget()
            return (0, values)
        elif len(values) == 0:
            print "No values at all!"
            return (-1, values)
        else:
            # TODO: Handle this case intelligently
            print "Not enough values for the required columns!"
            print values
        return (-2, values)

    def onGetBatchFilesClicked(self):
        (code, values) = self.checkValues()
        if code == 0:
            self.logic.writeToDatabase(values)
            self.logic.onGetBatchFilesClicked()
        else:
            pass

    def exit(self):
        """ When Slicer exits, prompt user if they want to write the last evaluation """
        (code, values) = self.checkValues()
        if code == 0:
            # TODO: Write a confirmation dialog popup
            self.logic.writeToDatabase(values)
            self.logic.exit()
            # self.logic.onGetBatchFilesClicked()
        elif code == -1:
            self.logic.exit()
        else:
            # TODO: write a prompt window
            self.logic.exit()
            # TODO: clear scene

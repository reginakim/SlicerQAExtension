#! /usr/bin/env python
import os

from __main__ import ctk
from __main__ import qt
from __main__ import slicer
from __main__ import vtk

import module_locator
import dwi_logic

globals()['__file__'] = module_locator.module_path()

### TODO: Add logging
# try:
#     import logging
#     import logging.handlers
# except ImportError:
#     print "External modules not found!"
#     raise ImportError

class DWIPreprocessingQA:
    def __init__(self, parent):
        parent.title = 'DWI Raw Inspection'
        parent.categories = ['Quality Assurance']
        parent.dependencies = ['Volumes']
        parent.contributors = ['Dave Welch (UIowa)']
        parent.helpText = """DWI raw image evaluation module for use in the UIowa PINC lab"""
        parent.acknowledgementText = """ """
        self.parent = parent


class DWIPreprocessingQAWidget:
    def __init__(self, parent=None):
        self.images = ('DWI',)
        self.htmlFileName = ('dwi_raw_1', 'dwi_raw_2',
                             'dwi_raw_3', 'dwi_raw_4')
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
            self.logic = dwi_raw_logic.DWIRawQALogic(self)
            self.setup()
            self.parent.show()
        else:
            self.parent = parent
            self.layout = self.parent.layout()
            self.logic = dwi_raw_logic.DWIRawQALogic(self)

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
        for question in self.htmlFileName:
            reviewButton = self.reviewButtonFactory(question)
            qaLayout.addWidget(reviewButton)
        # batch button
        self.nextButton = qt.QPushButton()
        self.nextButton.setText('Get next raw DWI')
        self.nextButton.connect('clicked(bool)', self.onGetBatchFilesClicked)
        qaLayout.addWidget(self.nextButton)
        self.dwiWidget = slicer.modulewidget.qSlicerDiffusionWeightedVolumeDisplayWidget()
        qaLayout.addWidget(self.dwiWidget)
        # Add all to layout
        self.layout.addWidget(self.dwiWidget)
        self.layout.addStretch(1)
        self.enableRadios(self.htmlFileName[0])
        ### HACK ###
        ### self.logic.onGetBatchFilesClicked()

    def loadUIFile(self, fileName):
        """ Return the object defined in the Qt Designer file """
        uiloader = qt.QUiLoader()
        qfile = qt.QFile(os.path.join(__file__, fileName))
        qfile.open(qt.QFile.ReadOnly)
        try:
            return uiloader.load(qfile)
        finally:
            qfile.close()

    def reviewButtonFactory(self, question):
        widget = self.loadUIFile('Resources/UI/dwiRawQuestionWidget.ui')
        # Set push button
        # TODO: Remove all pushButton references
        questionLabel= widget.findChild("QLabel", "questionTextLabel")
        questionLabel.objectName = question
        questionLabel.setText(self._readHTML(question))
        # TODO: Convert push button to label
        radioContainer = widget.findChild("QWidget", "radioWidget")
        radioContainer.objectName = question + "_radioWidget"
        # Set radio buttons
        yesButton = widget.findChild("QRadioButton", "yesButton")
        yesButton.objectName = question + "_yes"
        noButton = widget.findChild("QRadioButton", "noButton")
        noButton.objectName = question + "_no"
        return widget

    def _readHTML(self, question):
        fullPath = os.path.join(__file__, 'Resources/HTML', question + '.html')
        fID = open(fullPath)
        try:
            text = fID.read()
        finally:
            fID.close()
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
        for suffix in ("_yes", "_no"):
            radio = self.imageQAWidget.findChild("QRadioButton", image + suffix)
            radio.setShortcutEnabled(True)
            radio.setCheckable(True)
            radio.setEnabled(True)

    def resetRadioWidgets(self):
        """ Disable and reset all radio buttons in the widget """
        radios = self.imageQAWidget.findChildren("QRadioButton")
        for radio in radios:
            radio.setChecked(False)

    def getRadioValues(self):
        values = ()
        needsFollowUp = False
        radios = self.imageQAWidget.findChildren("QRadioButton")
        for question in self.htmlFileName:
            for radio in radios:
                if radio.objectName.find(question) > -1 and radio.checked:
                    if radio.objectName.find("_yes") > -1:
                        values = values + (1,)
                    elif radio.objectName.find("_no") > -1:
                        values = values + (0,)
                    else:
                        values = values + ("NULL",)
                        print "Warning: No value for %s" % question
        else:
            values = values + ("NULL",)
        return values

    def resetWidget(self):
        self.resetRadioWidgets()
        ### TODO: self.resetDWIwidget()

    def getValues(self):
        values = self.getRadioValues()
        return values

    def checkValues(self):
        values = self.getValues()
        if len(values) >= len(self.htmlFileName):
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

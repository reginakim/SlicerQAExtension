import qt, ctk

class testMe(object):
    def __init__(self):
        self.widget = qt.QWidget()
        self.widget.setLayout(qt.QVBoxLayout())

        uiloader = qt.QUiLoader()
        qfile = qt.QFile('/Users/dmwelch/Development/src/extensions/SlicerDerivedImageEval/Resources/UI/simple.ui')
        qfile.open(qt.QFile.ReadOnly)
        self.simple = uiloader.load(qfile)
        self.widget.layout().addWidget(self.simple)
        qfile.close()

        self.widget.show()

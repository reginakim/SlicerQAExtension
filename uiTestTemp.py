import qt, ctk

class testMe(object):
    def __init__(self):
        uiloader = qt.QUiLoader()
        qfile = qt.QFile('/Users/dmwelch/Development/src/extensions/SlicerDerivedImageEval/Resources/UI/qMRMLSlicerEvaluatorWidget/qMRMLSlicerEvaluatorWidget.ui')
        try:
            qfile.open(qt.QFile.ReadOnly)
            self.simple = uiloader.load(qfile)
        except:
            raise
        finally:
            qfile.close()

    def runFileWidget(self):
        return self.simple

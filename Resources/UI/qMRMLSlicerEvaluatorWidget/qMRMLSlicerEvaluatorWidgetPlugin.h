// Add this to the Libs/qMRMLWidgets/Plugins directory

#ifndef __qMRMLSlicerEvaluatorWidgetPlugin_h
#define __qMRMLSlicerEvaluatorWidgetPlugin_h

#include "qMRMLWidgetsAbstractPlugin.h"

class QMRML_WIDGETS_PLUGIN_EXPORT qMRMLSlicerEvaluatorWidgetPlugin : public QObject,
                                public qMRMLWidgetsAbstractPlugin
{
  Q_OBJECT
  Q_PROPERTY(buttonSelect button_selected
             READ isButtonSelected
             WRITE selectButton
             RESET resetButton)
  Q_BOOL(buttonSelected)

public:
  qMRMLSlicerEvaluatorWidgetPlugin(QObject *_parent = 0);

  QWidget *createWidget(QWidget *_parent);
  QString domXml() const;
  QString includeFile() const;
  bool isContainer() const;
  QString name() const;

  bool buttonSelect() const;
  void selectButton(buttonSelect button_selected);
  buttonSelect isButtonSelected() const;

};

#endif


// Add this to the Libs/qMRMLWidgets/Plugins directory

#ifndef __qMRMLSlicerEvaluatorWidgetPlugin_h
#define __qMRMLSlicerEvaluatorWidgetPlugin_h

#include "qMRMLWidgetsAbstractPlugin.h"

class QMRML_WIDGETS_PLUGIN_EXPORT qMRMLSlicerEvaluatorWidgetPlugin : public QObject,
                                public qMRMLWidgetsAbstractPlugin
{
  Q_OBJECT

public:
  qMRMLSlicerEvaluatorWidgetPlugin(QObject *_parent = 0);

  QWidget *createWidget(QWidget *_parent);
  QString domXml() const;
  QString includeFile() const;
  bool isContainer() const;
  QString name() const;

};

#endif


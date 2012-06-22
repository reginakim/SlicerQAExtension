// Add this to the Libs/qMRMLWidgets/Plugins directory

#include "qMRMLSlicerEvaluatorWidgetPlugin.h"
#include "qMRMLSlicerEvaluatorWidget.h"

//------------------------------------------------------------------------------
qMRMLSlicerEvaluatorWidgetPlugin::qMRMLSlicerEvaluatorWidgetPlugin(QObject *_parent)
        : QObject(_parent)
{

}

//------------------------------------------------------------------------------
QWidget *qMRMLSlicerEvaluatorWidgetPlugin::createWidget(QWidget *_parent)
{
  qMRMLSlicerEvaluatorWidget* _widget = new qMRMLSlicerEvaluatorWidget(_parent);
  return _widget;
}

//------------------------------------------------------------------------------
QString qMRMLSlicerEvaluatorWidgetPlugin::domXml() const
{
  // You can customize how the widget is instantiated in Designer here
  // Read in domxml file here and return the string...
  return "<widget class=\"qMRMLSlicerEvaluatorWidget\" \
          name=\"MRMLSlicerEvaluatorWidget\">\n"
          "</widget>\n";
}

//------------------------------------------------------------------------------
QString qMRMLSlicerEvaluatorWidgetPlugin::includeFile() const
{
  return "qMRMLSlicerEvaluatorWidget.h";
}

//------------------------------------------------------------------------------
bool qMRMLSlicerEvaluatorWidgetPlugin::isContainer() const
{
  // If you're method is a container, change this to true
  return false;
}

//------------------------------------------------------------------------------
QString qMRMLSlicerEvaluatorWidgetPlugin::name() const
{
  return "qMRMLSlicerEvaluatorWidget";
}


#-----------------------------------------------------------------------------
set(KIT_UNITTEST_SCRIPTS
  databaseTest.py
  )

SlicerMacroConfigureGenericPythonModuleTests("${EXTENSION_NAME}" KIT_UNITTEST_SCRIPTS)

#-----------------------------------------------------------------------------
foreach(script_name ${KIT_UNITTEST_SCRIPTS})
  slicer_add_python_unittest(
    SCRIPT ${script_name}
    SLICER_ARGS --no-main-window ${CMAKE_BINARY_DIR}/${Slicer_QTSCRIPTEDMODULES_LIB_DIR}
    TESTNAME_PREFIX nomainwindow_
    --additional-module-paths ${CMAKE_BINARY_DIR}/
    )
endforeach()


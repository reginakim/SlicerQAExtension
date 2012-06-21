import os
from ..SlicerDerivedImageEval import SlicerDerivedImageEvalLogic as Logic

testDataDirectory = ['Experiment/0131/89205/TissueClassify/0131_89205_T1-30_4_corrected.nii.gz',
                     'Experiment/0131/89205/TissueClassify/0131_89205_T2-30_25_corrected.nii.gz',
                     'Experiment/0131/89205/TissueClassify/POSTERIOR_AIR.nii.gz',
                     'Experiment/0131/89205/TissueClassify/POSTERIOR_BGM.nii.gz',
                     'Experiment/0131/89205/TissueClassify/POSTERIOR_CRBLGM.nii.gz',
                     'Experiment/0131/89205/TissueClassify/POSTERIOR_CRBLWM.nii.gz',
                     'Experiment/0131/89205/TissueClassify/POSTERIOR_CSF.nii.gz',
                     'Experiment/0131/89205/TissueClassify/POSTERIOR_NOTCSF.nii.gz',
                     'Experiment/0131/89205/TissueClassify/POSTERIOR_NOTGM.nii.gz',
                     'Experiment/0131/89205/TissueClassify/POSTERIOR_NOTVB.nii.gz',
                     'Experiment/0131/89205/TissueClassify/POSTERIOR_NOTWM.nii.gz',
                     'Experiment/0131/89205/TissueClassify/POSTERIOR_SURFGM.nii.gz',
                     'Experiment/0131/89205/TissueClassify/POSTERIOR_VB.nii.gz',
                     'Experiment/0131/89205/TissueClassify/POSTERIOR_WM.nii.gz',
                     'Experiment/0131/89205/TissueClassify/brain_label_seg.nii.gz',
                     'Experiment/0131/89205/TissueClassify/t1_average_BRAINSABC.nii.gz',
                     'Experiment/0131/89205/TissueClassify/t2_average_BRAINSABC.nii.gz',
                     'Experiment/0131/89205/TissueClassify/template_t1_to_BCD_ACPC_warped.nii.gz',
                     'Experiment/0131/89205/TissueClassify/template_t2_to_BCD_ACPC_warped.nii.gz',
                     'Experiment/0131/89205/TissueClassify/thresholded_labels.nii.gz',
                     'Experiment/0131/89205/TissueClassify/volume_label_seg.nii.gz']

testingDirectory = 'Development/src/extensions/SlicerDerivedImageEval/Testing'
home = os.environ['HOME']
fullPathList = [(os.path.join(home, testingDirectory, item) for item in testDataDirectory)]

testLogic = Logic()
testLogic._getLockedFileList(fullPathList)

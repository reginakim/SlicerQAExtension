#!/usr/bin/env python
import ConfigParser as cp

def writeFile():
    config = cp.RawConfigParser()
    images = ['t1_average', 't2_average', 'labels_tissue',
              'caudate_left', 'caudate_right',
              'accumben_left', 'accumben_right',
              'putamen_left', 'putamen_right',
              'globus_left', 'globus_right',
              'thalamus_left', 'thalamus_right',
              'hippocampus_left', 'hippocampus_right']
    dirs = [['TissueClassify']] * 3 + [['DenoisedRFSegmentations']] * (len(images)-3)
    fnames = [['t1_average_BRAINSABC.nii.gz'],
              ['t1_average_BRAINSABC.nii.gz'],
              ['fixed_brainlabels_seg.nii.gz']]
    for label in images[3:]:
        region, side = label.split('_')
        fnames.append(['{SIDE}_{REGION}_seg.nii.gz'.format(SIDE=side[0].lower(),
                                                           REGION=region.lower())])

    config.add_section('Logic')
    config.set('Logic', 'files', images)

    for index in range(len(images)):
        section = images[index]
        fname = fnames[index]
        _dir = dirs[index]
        config.add_section(section)
        config.set(section, 'directories', _dir)
        config.set(section, 'filenames', fname)

    with open('derived_images.cfg', 'w') as configFile:
        config.write(configFile)

if __name__ == '__main__':
    writeFile()

import re

def getGradients(dwiFileName):
    """
    >>> dwiFileName = '/paulsen/MRx/PHD_024/0132/43991/ANONRAW/0132_43991_DWI-31_6.nrrd'
    >>> outlist = getGradients(dwiFileName)
    >>> print '\\n'.join(item for item in outlist)
    0000:=0   0   0
    0001:=-0.20 -0.52 -0.82
    0002:=-0.19 0.52 0.83
    0003:=-0.40 0.17 0.89
    0004:=-0.40 -0.73 -0.54
    0005:=-0.20 -0.94 -0.26
    0006:=-0.85 -0.51 -0.05
    0007:=-0.73 -0.51 -0.44
    0008:=-0.40 -0.17 -0.89
    0009:=-0.73 -0.17 -0.65
    0010:=-0.65 -0.73 0.20
    0011:=-0.32 -0.94 0.10
    0012:=-0.32 -0.52 0.79
    0013:=-0.64 -0.52 0.55
    0014:=-0.97 -0.17 0.10
    0015:=-0.85 -0.17 0.48
    0016:=0.00 -0.73 0.68
    0017:=-0.00 0.94 -0.33
    0018:=-0.65 0.51 -0.54
    0019:=-0.32 0.52 -0.78
    0020:=-0.19 -0.17 0.96
    0021:=-0.20 0.17 -0.96
    0022:=-0.65 0.73 -0.20
    0023:=-0.32 0.94 -0.09
    0024:=-0.19 0.94 0.27
    0025:=-0.40 0.73 0.54
    0026:=-0.73 0.17 0.65
    0027:=-0.72 0.51 0.44
    0028:=-0.85 0.51 0.06
    0029:=-0.85 0.17 -0.48
    0030:=-0.97 0.17 -0.09
    """
    fID = open(dwiFileName)
    gradientStringList = []
    try:
        for line in fID:
            if "DWMRI_gradient_" in line:
                strip_version = line.replace("DWMRI_gradient_", "")
                clean_version = re.sub(r' *(?P<truncstring>[-]*0\.[0-9][0-9])[0-9]*',
                                       '\g<truncstring> ',
                                       strip_version)
                clean_version = clean_version.strip(' \n')
                gradientStringList.append(clean_version)
    finally:
        fID.close
    return gradientStringList


if __name__ == "__main__":
    import doctest
    doctest.testmod()

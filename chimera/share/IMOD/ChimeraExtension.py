# -----------------------------------------------------------------------------
# Register IMOD file reader, for display segmentation mesh surfaces.
#
def open_cb(path):
    import IMOD
    try:
        mlist = IMOD.read_imod_segmentation(path, mesh = True, contours = False)
    except (SyntaxError, TypeError), e:
        from chimera import replyobj
        replyobj.error(str(e))
        return []
    return mlist

import chimera
fi = chimera.fileInfo
fi.register('IMOD segmentation', open_cb, ['.imod', '.mod'], ['imod'],
            canDecompress = False, category = fi.GENERIC3D)

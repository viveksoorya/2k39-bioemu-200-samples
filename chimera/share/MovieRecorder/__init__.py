## Movie recorder module

EXIT_ERROR = "ERROR"
EXIT_CANCEL = "CANCEL"
EXIT_SUCCESS = "SUCCESS"

DEFAULT_PATTERN = "chimovie_%s-*"
from OpenSave import tildeExpand
DEFAULT_OUTFILE = tildeExpand("~/Desktop/movie.mp4")

RESET_CLEAR = 'clear'
RESET_KEEP = 'keep'
RESET_NONE = 'none'

director = None

class MovieError(Exception):
    pass

## ----------------- gui interface ----------------------

def showMRDialog():
    import chimera
    import RecorderGUI
    chimera.dialogs.display(RecorderGUI.MovieRecorderGUI.name)

## ------------------ command line interface -------------------

class BaseRecorderGUI:
    def __init__(self):
        pass
    def _notifyFrameCount(self, count):
        pass
    def _notifyMovieTime(self, t):
        pass
    def _notifyRecorderReset(self):
        pass
    def _notifyStatus(self, msg):
        pass
    def _notifyThreadStatus(self, msg):
        pass
    def _notifyError(self, err):
        pass
    def _notifyInfo(self, info):
        pass
    def _notifyEncodingComplete(self, exit_status):
        pass
    def _notifyGfxSize(self, size):
        pass
    def _notifyRecordingStart(self):
        pass
    def _notifyRecordingStop(self):
        pass
    def _notifyEncodingStart(self):
        pass

class CmdLineGUI(BaseRecorderGUI):

    def _notifyStatus(self, msg):
        from chimera import replyobj
        replyobj.status(msg)

    def _notifyThreadStatus(self, msg):
        self._notifyStatus(msg)

    def _notifyError(self, err):
        from chimera import replyobj
        replyobj.error(err)
        self._notifyStatus(err)

    def _notifyInfo(self, info):
        from chimera import replyobj
        replyobj.info(info)

    def _notifyGfxSize(self, size):
        self. _notifyStatus("Chimera graphics window is now %s pixels" % size)

cmdLineUI = None

def getDirector(setCmdLineUI = False):

    global director
    if director is None:
        import Director
        director = Director.Director()

    if setCmdLineUI:
        global cmdLineUI
        if cmdLineUI is None:
            cmdLineUI = CmdLineGUI()
            director.registerUI(cmdLineUI)

    return director

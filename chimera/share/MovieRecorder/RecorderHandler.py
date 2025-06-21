import chimera

import glob, os

from MovieRecorder import DEFAULT_PATTERN
from utils import getRandomChars

class RecorderError(Exception):
    pass

class RecorderHandler:

    def __init__(self, director, img_fmt=None, img_dir=None, input_pattern=None,
                 size=None, supersample=0, raytrace=False, limit = None):

        if not img_fmt:
            self.img_fmt = "PNG"
        else:
            self.img_fmt = img_fmt.upper()

        if not img_dir:
            import tempfile
            self.img_dir = tempfile.gettempdir()
        else:
            from OpenSave import tildeExpand
            self.img_dir = tildeExpand(img_dir)
            
        if not input_pattern:
            self.input_pattern = DEFAULT_PATTERN % getRandomChars()
        else:
            if not input_pattern.count("*")==1:
                raise RecorderError, "Image pattern must have one and only one '*'"
            self.input_pattern = input_pattern

        self.size = size
        if size and supersample == 0:
            supersample = 1
        self.supersample = supersample
        self.raytrace = raytrace
        self.limit = limit

        self.director = director

        self.newFrameHandle = None

        self.frame_count     = -1

        self.postprocess_action = None
        self.postprocess_frames = 0

        #self.chimera_winsize = (None,None)
        self.RECORDING = False
        self.task = None

    def start(self):        
        self.newFrameHandle = chimera.triggers.addHandler('post-frame', self.captureImage, None)
        self.RECORDING = True
        from chimera.tasks import Task
        self.task = Task("record movie", self.cancelCB)

    def postprocess(self, action, frames):
        if self.frame_count < 0:
            # Need an initial image to do a crossfade.
            self.captureImage()
        self.postprocess_action = action
        self.postprocess_frames = frames

    def cancelCB(self):
        # If user cancels inside of captureImage/saveImage, this callback
        # is never invoked because of the exception thrown in saveImage
        # happens before this function is called.  So we 
        self.director.stopRecording()
        self.director._informStatus("movie recording aborted by user")

    def stop(self):
        chimera.triggers.deleteHandler('post-frame', self.newFrameHandle)
        self.RECORDING = False
        self.task.finished()
        self.task = None

    def reset(self):
        self.frame_count = -1
        self.img_dir = None
        self.img_fmt = None
        self.input_pattern = None
        
    def isRecording(self):
        return self.RECORDING

    def clearFrames(self):
        src_img_pattern = os.path.join(self.img_dir,
                                       self.input_pattern \
                                       + ".%s" % self.img_fmt.lower()
                                       )
        
        src_img_paths = glob.glob(src_img_pattern)

        for s in src_img_paths:
            try:
                os.remove(s)
            except:
                chimera.replyobj.error("Error removing file %s" % s)


    def getFrameCount(self):
        return self.frame_count

    def getInputPattern(self):
        return self.input_pattern

    def getImgFormat(self):
        return self.img_fmt

    def getImgDir(self):
        return self.img_dir

    def getStatusInfo(self):
        status_str  =  "-----Movie status------------------------------\n "
        status_str  += " %s\n" % (["Stopped","Recording"][self.isRecording()])
        status_str  += "  %s frames (in '%s' format) saved to directory '%s' using pattern '%s' .\n" % \
                       (self.getFrameCount(), self.getImgFormat(),self.getImgDir(), self.getInputPattern())
        status_str  += "  Est. movie length is %ss.\n" % (self.getFrameCount()/24)
        status_str  += "------------------------------------------------\n"
        return status_str
                

    def captureImage(self, trigger=None, closure=None, data=None):

        f = self.frame_count + 1 + self.postprocess_frames
        if not self.limit is None and f >= self.limit:
            self.stop()
            return

        self.frame_count += 1 + self.postprocess_frames
        self.director._informFrameCount(self.frame_count)
        if self.frame_count%10 == 0:
            self.director._informStatus("Capturing frame #%d " % self.frame_count)

        save_path = self.image_path(self.frame_count)

        width, height = (None,None) if self.size is None else self.size
        
        from chimera.printer import saveImage
        from chimera import NonChimeraError
        try:
            saveImage(save_path,
                      format = self.img_fmt,
                      width = width,
                      height = height,
                      supersample = self.supersample,
                      raytrace = self.raytrace,
                      raytraceWait = True,
                      raytracePreview = False,
                      hideDialogs = False,
                      raiseWindow = False,
                      statusMessages = False,
                      task = self.task
                      )
        except NonChimeraError, s:
            # Raytracing aborted.
            self.director.stopRecording()
            self.director._informStatus(str(s))
            self.frame_count -= 1
            self.postprocess_frames = 0
            self.director._informFrameCount(self.frame_count)
        except:
            self.director.stopRecording()
            self.director._informStatus("Error capturing frame. Resetting recorder.")
            self.director.resetRecorder(clearFrames=True)
            raise

        if self.postprocess_frames > 0:
            if self.postprocess_action == 'crossfade':
                self.save_crossfade_images()
            elif self.postprocess_action == 'duplicate':
                self.save_duplicate_images()

    def image_path(self, frame):

        savepat = self.input_pattern.replace('*','%05d')
        basename = savepat % frame
        suffix = '.%s' % self.img_fmt.lower()
        save_filename = basename + suffix
        save_path = os.path.join(self.img_dir, save_filename)
        return save_path

    def save_crossfade_images(self):

        frames = self.postprocess_frames
        self.postprocess_frames = 0
        save_path1 = self.image_path(self.frame_count - frames - 1)
        save_path2 = self.image_path(self.frame_count)
        from PIL import Image
        image1 = Image.open(save_path1)
        image2 = Image.open(save_path2)
        for f in range(frames):
            imagef = Image.blend(image1, image2, float(f)/(frames-1))
            # TODO: Add save image options as in printer.saveImage()
            pathf = self.image_path(self.frame_count - frames + f)
            imagef.save(pathf, self.img_fmt)
            self.director._informStatus("Cross-fade frame %d " % (f+1))

    def save_duplicate_images(self):

        frames = self.postprocess_frames
        self.postprocess_frames = 0
        save_path = self.image_path(self.frame_count - frames - 1)
        from PIL import Image
        image = Image.open(save_path)
        for f in range(frames):
            pathf = self.image_path(self.frame_count - frames + f)
            image.save(pathf, self.img_fmt)
            self.director._informStatus("Duplicate frame %d " % (f+1))

# ProgressBarDialog megawidget written by Morten Fagerland

import Tkinter
import Pmw

class ProgressBarDialog(Pmw.Dialog):
    """ A dialog with a progress bar
    """
    
    def __init__(self, parent = None, **kw):

        # Define the megawidget options
        INITOPT = Pmw.INITOPT
        CONFIG = self._configBar
        optiondefs = (
            ('barfill',             'blue2',                CONFIG),
            ('baroutline',          'blue2',                CONFIG),
            ('baroutlinewidth',     1,                      CONFIG),
            ('barstipple',          None,                   CONFIG),
            ('borderx',             10,                     INITOPT),
            ('bordery',             10,                     INITOPT),
            ('labelmargin',         0,                      INITOPT),
            ('labelpos',            None,                   INITOPT),
            ('textfill',            ['black', 'white'],     None),

            ('bar_borderwidth',     2,                      INITOPT),
            ('bar_height',          18,                     INITOPT),
            ('bar_relief',          'sunken',               INITOPT),
            ('bar_width',           200,                    INITOPT),
        )
        self.defineoptions(kw, optiondefs)

        # Initialise the base class (after defining the options)
        Pmw.Dialog.__init__(self, parent)

        # Create the components.
        interior = self.interior()

        self.createlabel(interior)

        self._bar = self.createcomponent('bar', (), None,
                Tkinter.Canvas, interior)

        # Create the actual bar as a canvas rectangle
        # and the progress text as a canvas text
        self._bar.create_rectangle(0,0, 0,0, tags = 'bar')
        self._bar.create_text(0,0, tags = 'text')

        # Resize the canvas rectangle if the bar is resized
        self._bar.bind('<Configure>', self._resizeBar)

        # Position components
        interior.grid_rowconfigure(0, minsize = self['bordery'])
        interior.grid_rowconfigure(4, minsize = self['bordery'])
        interior.grid_columnconfigure(0, minsize = self['borderx'])
        interior.grid_columnconfigure(4, minsize = self['borderx'])
        self._bar.grid(row = 2, column = 2, sticky = 'news')
        
        # Allow the progress bar to expand in both directions
        interior.grid_columnconfigure(2, weight = 1)
        interior.grid_rowconfigure(2, weight = 1)

        # Keep the last progress value (used when the canvas has been resized)
        self._lastProgressValue = 0

        # Check keywords and initialise options
        self.initialiseoptions()

	# If parent is visible, place progress bar directly over its center
	if parent.winfo_ismapped():
		w = self.winfo_reqwidth()
		h = self.winfo_reqheight()
		mx = parent.winfo_rootx()
		my = parent.winfo_rooty()
		mw = parent.winfo_width()
		mh = parent.winfo_height()
		x = mx + (mw - w) / 2
		y = my + (mh - h) / 2
		self.geometry("%+d%+d" % (x, y))

    def updatebarlength(self, progress):
        self._lastProgressValue = progress
        width = self._bar.winfo_width() - 5
        height = self._bar.winfo_height() - 5

        # Update bar
        self._bar.coords('bar', 4,4, progress*width,height)

        # Update progress text (if halfway: change color)
        if progress <= .5:
            fill = self['textfill'][0]
        else:
            fill = self['textfill'][1]
        text = str(int(progress*100))+'%'
        self._bar.coords('text', 4 + width/2, 2 + height/2)
        self._bar.itemconfigure('text', text = text, fill = fill)

        self._bar.update()

    def _resizeBar(self, event):
        self.updatebarlength(self._lastProgressValue)

    def _configBar(self):
        self._bar.itemconfigure('bar',
                fill = self['barfill'],
                outline = self['baroutline'],
                stipple = self['barstipple'],
                width = self['baroutlinewidth'])

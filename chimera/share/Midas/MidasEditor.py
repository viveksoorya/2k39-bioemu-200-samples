#import urllib2, webbrowser
from MidasDocViewer import MidasDocViewer
import Midas
import Pmw
import Tkinter

class MidasEditor():

    def __init__(self, parent, group=True):
        # Create a ScrolledText widget for Midas commands
        self.parent = parent
        #
        # A collapsible group container
        #
        self.group = Pmw.Group(self.parent,
                tag_pyclass=Tkinter.Button,
                tag_text='Command Editor')
        if group:
            self.group.pack(side=Tkinter.TOP,
                padx=4, pady=4, fill=Tkinter.BOTH, expand=1)
            self.group.configure(tag_command=self.groupVisible)
            self.groupTag = self.group.component('tag')
            parent = self.group.interior()
        #
        # Midas commands and documentation viewer
        #
        self.midasCommands = self.getMidasModuleCommands()
        self.midasDocViewer = MidasDocViewer()
        self.midasDocViewer.Close()
        #
        # Enable components for Midas command auto-completion
        #
        self.midasCompleteListBox = Pmw.ScrolledListBox(
            parent,
            items=sorted(self.midasCommands.keys()),
            labelpos='nw',
            label_text='Command Completions:',
            listbox_height=3,
            selectioncommand=self.autoInsertCommand,
            dblclickcommand=self.showMidasDoc,
            #usehullsize=1,
            #hull_width=100,
            #hull_height=100,
        )
        self.midasCompleteListBox.pack(side=Tkinter.TOP,
            padx=4, pady=4, fill=Tkinter.BOTH, expand=0)
        #
        # Add the editor
        #
        self.midasFont = Pmw.logicalfont('Fixed', size=10)
        self.midasScrolledText = Pmw.ScrolledText(
            parent,
            # borderframe = 1,
            hscrollmode='dynamic',
            vscrollmode='dynamic',
            labelpos='n',
            label_text='Commands',
            #columnheader=1,
            #rowheader=1,
            #rowcolumnheader=1,
            usehullsize=1,
            hull_width=400,
            hull_height=200,
            text_wrap='none',
            text_font=self.midasFont,
            #Header_font=fixedFont,
            #Header_foreground='blue',
            #rowheader_width=3,
            #rowcolumnheader_width=3,
            text_padx=2,
            text_pady=2,
            #Header_padx=4,
            #rowheader_pady=4,
        )
        self.midasScrolledText.pack(side=Tkinter.BOTTOM,
            padx=4, pady=4, fill=Tkinter.BOTH, expand=1)
        self.midasText = self.midasScrolledText.component('text')
        self.midasText.bind('<KeyRelease>', self.autoComplete)
        #self.midasCompleteMenu = None

    def autoComplete(self, e):
        'Callback for midasText <KeyRelease> to update Midas command list'
        midasCommands = sorted(self.midasCommands.keys())
        self.midasCompleteListBox.setlist(midasCommands)
        midasEntries = self.getMidasEntries()
        lastEntry = midasEntries[-1].strip()
        if lastEntry:
            matchCommands = self.matchMidasCommands(lastEntry)
            if matchCommands:
                self.midasCompleteListBox.setlist(matchCommands)
                #self.autoCompleteMenu(matchCommands)
                #self.autoCompleteMenu_show(e)

    def autoInsertCommand(self):
        'Add completed command to self.midasText'
        command = self.midasCompleteListBox.getvalue()[0]
        if command:
            #
            # TODO: get the replacement to be word specific, so
            # each line can have multiple commands separated by ';' as
            # specified in Midas syntax
            #
            #index1 = self.midasText.index('insert - 1 chars wordstart')
            #index2 = self.midasText.index('insert wordend')
            index1 = self.midasText.index('insert linestart')
            index2 = self.midasText.index('insert lineend')
            self.midasText.delete(index1, index2)
            self.midasText.insert(Tkinter.INSERT, command)

    def getMidasModuleCommands(self):
        '''Extract command information from the Midas module.
        - parses Midas.midas_text.cmdList and entries are excluded
          if doFunc.func_name == 'Unimplemented'
        - returns a dict[cmdName] = [doFunc, unFunc, changeDisplay]
        '''
        midasCommands = {}
        for cmd, func, funcNeg, disp in Midas.midas_text.cmdList:
            if func.func_name != 'Unimplemented':
                midasCommands[cmd] = [func, funcNeg, disp]
        return midasCommands

    def getMidasEntries(self):
        self.midasScrolledText.update_idletasks()
        midasEntries = self.midasScrolledText.getvalue()
        midasLines = midasEntries.splitlines()
        midasCommandEntries = []
        for midasLine in midasLines:
            midasCommandEntries += midasLine.split(';')
        return midasCommandEntries

    def getMidasDoc(self, command):
        midasGuide = 'http://www.cgl.ucsf.edu/chimera/docs/UsersGuide/midas/'
        midasURL = '%s%s.html' % (midasGuide, command)
        try:
            midasDoc = urllib2.urlopen(midasURL).read()
        except:
            midasDoc = '<html><body><p>'
            midasDoc += '<p>help not available</p>'
            midasDoc += '</body></html>'
        return midasURL, midasDoc

    def showMidasDoc(self):
        'Display midas command documentation (html)'
        command = self.midasCompleteListBox.getvalue()[0]
        self.midasDocViewer.showMidasDoc(command)
        #midasURL, midasDoc = self.getMidasDoc(command)
        #webbrowser.open(midasURL, new=0)

    def matchMidasCommands(self, command):
        'Identify the midas commands that start with "command"'
        possibleCommands = []
        midasCommands = sorted(self.midasCommands.keys())
        for cmd in midasCommands:
            if cmd.startswith(command.strip()):
                possibleCommands.append(cmd)
        return possibleCommands

    def groupVisible(self):
        'Display or hide the Midas commands group'
        #self.groupGetSize()
        #w1 = self.groupWidth
        #h1 = self.groupHeight
        self.group.toggle()
        if self.group.showing:
            expand = True
        else:
            expand = False
        self.group.pack(expand=expand)
        #self.groupGetSize()
        #w2 = self.groupWidth
        #h2 = self.groupHeight
        #wdelta = w2 - w1
        #hdelta = h2 - h1
        #self.groupSetParentSize(wdelta, hdelta)

    def groupGetSize(self):
        self.group.update_idletasks()
        self.groupWidth = self.group.winfo_width()
        self.groupHeight = self.group.winfo_height()

    def groupGetParentSize(self):
        self.parent.update_idletasks()
        self.parentWidth = self.parent.winfo_width()
        self.parentHeight = self.parent.winfo_height()

    def groupSetParentSize(self, widthDelta, heightDelta):
        self.groupGetParentSize()
        #print self.groupWidth, self.groupHeight
        #print widthDelta, heightDelta
        self.parent.config(width=self.parentWidth - widthDelta)
        self.parent.config(height=self.parentHeight - heightDelta)

    '''
    def autoCompleteMenu(self, commands):
        'Create a callback menu for command completions'
        if self.midasCompleteMenu:
            self.midasCompleteMenu.destroy()
        self.midasCompleteMenu = Tkinter.Menu(self.parent, tearoff=0)
        popup = self.midasCompleteMenu
        popup.bind('<Leave>', self.autoCompleteMenu_hide)
        popup.add_command(label='Cancel')   # no callback, do nothing
        for cmd in commands:
            cb = (lambda:self.autoInsertCommand(cmd))
            popup.add_command(label=cmd, command=cb)

    def autoCompleteMenu_hide(self, e):
        # e.widget is the popup created in self.button_menu()
        popup = e.widget
        popup.unpost()

    def autoCompleteMenu_show(self, e):
        if self.midasCompleteMenu is None:
            return
        popup = self.midasCompleteMenu
        #self.midasText.window_create(Tkinter.INSERT, window=popup)
        # Get current cursor position
        self.midasText.update_idletasks()
        textPositionX = self.midasText.winfo_rootx()
        textPositionY = self.midasText.winfo_rooty()
        charPosition = self.midasText.bbox(Tkinter.INSERT) # (x,y,width,height)
        padding = 2
        popupX = textPositionX + charPosition[0] + padding
        popupY = textPositionY + charPosition[1] + charPosition[3] + padding
        popup.post(popupX, popupY)

    '''


import re
import urllib2

import Midas
from chimera.baseDialog import ModelessDialog

class MidasDocViewer(ModelessDialog):
    #name = 'Midas Documentation'
    title = 'Midas Command Documentation'
    buttons = ('Close')
    default = 'Close'
    provideStatus = False
    def fillInUI(self, parent):
        from chimera.HtmlText import HtmlText
        import Tkinter
        import Pmw
        #
        # Create a selection of Midas commands
        #
        self.midasCommands = self.getMidasModuleCommands()
        self.commandListBox = Pmw.ScrolledListBox(
            parent,
            items=sorted(self.midasCommands.keys()),
            labelpos='nw',
            label_text='Midas Commands:',
            listbox_height=8,
            selectioncommand=self.showMidasDoc,
            #dblclickcommand=self.autoInsertCommand,
            #usehullsize=1,
            #hull_width=100,
            #hull_height=100,
            )
        self.commandListBox.grid(row=0, column=0, sticky='nsew', pady=5)
        #
        # Create a display for the HTML documentation
        #
        self.infoText = Pmw.ScrolledText(parent,
            text_pyclass=HtmlText,
            text_relief='sunken',
            text_wrap='word',
            text_width=80,
            text_height=40,
            )
        self.infoText.settext('')
        self.infoText.configure(text_state='disabled',
            hscrollmode='dynamic',
            vscrollmode='dynamic',
            text_background=parent.cget('background')
            )
        self.infoText.grid(row=1, column=0, sticky='nsew', pady=5)
        parent.rowconfigure(1, weight=1)
        parent.columnconfigure(0, weight=1)

    def getMidasDoc(self, command):
        midasGuide = 'http://www.cgl.ucsf.edu/chimera/docs/UsersGuide/midas/'
        midasURL = '%s%s.html' % (midasGuide, command)
        try:
            # some pages have redirects in the meta data, e.g.:
            # <meta http-equiv="Refresh" content="0;URL='hbonds.html'">
            for line in urllib2.urlopen(midasURL).readlines():
                if line.find('meta') >= 0:
                    refresh = re.findall("Refresh", line)
                    html = re.findall("'.*\.html'", line)
                    url = re.findall("URL", line)
                    if refresh and url and html:
                        page = html[0].strip("'")
                        midasURL = '%s%s' % (midasGuide, page)
            midasDoc = urllib2.urlopen(midasURL).read()
        except:
            midasDoc = '<html><body><p>'
            midasDoc += '<p>help not available</p>'
            midasDoc += '</body></html>'
        return midasURL, midasDoc

    def showMidasDoc(self, command=None):
        'Display midas command documentation (html)'
        if command is None:
            command = self.commandListBox.getvalue()[0]
        if command:
            midasURL, midasDoc = self.getMidasDoc(command)
            #import webbrowser
            #webbrowser.open(midasURL)
            self.infoText.settext(midasDoc)
            self.enter()

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


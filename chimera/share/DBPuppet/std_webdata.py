# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: std_webdata.py 39320 2013-11-26 21:14:45Z conrad $

import chimera
import sys, os
import DBPuppet
from DBPuppet import NO_AUTH, NO_URL, CANCEL_FETCH
import chimera.replyobj

import xml.sax


#########################################################
# This file is the 'action handler' module for the standard
# Chimera web data format. This format can accomodate the downloading
# and opening of URLs containing Chimera-supported file formats,
# opening PDB ids, and executing arbitrary Midas commands
#
# Chimera will search for and load this module dynamically, in
# response to finding a .chimerax file with
#    ChimeraPuppet type="std_webdata"
# and then will call the 'handle_file' method defined below
#########################################################


class std_webdata:

    def __init__(self):
        pass

    def handle_file(self, file_loc):
        """this function is called from DBPuppet::__init__.py.
        file_loc is either an open file handle, or a string specifying
        the location of the file.
        """

        if isinstance(file_loc, basestring):
            f = open(file_loc, 'r')
            ## parse the XML
            handler = self.parse_file_sax(f)
        elif isinstance(file_loc, file):
            ## parse the XML
            handler = self.parse_file_sax(file_loc)


        ## this will map name:location
        dloaded_files = {}

        for name,format,url,noprefs in handler.getWebFiles():
            ## name is the what the file should be called, when
            ## saved locally, and url is its URL.

            ## save the URL to a file locally, and store this path in loc
            try:
                loc = DBPuppet.getURL(url, name)

            except NO_AUTH:
                self.cleanUpDloaded(dloaded_files.values())
                raise chimera.UserError,"Invalid credentials to access url '%s'" % url

            except NO_URL, what:
                self.cleanUpDloaded(dloaded_files.values())
                raise chimera.UserError, "Couldn't find url '%s': %s" % (url,what)

            except CANCEL_FETCH:
                self.cleanUpDloaded(dloaded_files.values())
                return

            if format=='html':
                DBPuppet.stripHTML(loc)
            ## add this to the list of downloaded files
            dloaded_files[name] = (loc, noprefs)

        ## open the downloaded files, PDB ids, and midas commands in Chimera
        self.open_in_chimera(dloaded_files, handler.getPDBs(), \
                             handler.getAllCmds() )



    def cleanUpDloaded(self, dload):
        if isinstance(dload, basestring):
            try:
                os.remove(dload)
            except OSError:
                pass
        elif isinstance(dload, list):
            for d in dload:
                try:
                    os.remove(d)
                except OSError:
                    pass

    def warnIfNeeded(self, web_files, all_cmds):

        need_to_warn = False

        #PYTHON_FILE = "<b>Python file(s)</b> (could contain <i>Python code</i> or a <i>Chimera session</i>)"

        ## keep track of dangerous files
        ext_map = {}
        ext_count = {}
        for t in chimera.fileInfo.types():
            if not chimera.fileInfo.dangerous(t):
                continue
            ext_count[t] = 0
            for p in chimera.fileInfo.prefixes(t):
                ext_map[p] = t
            for e in chimera.fileInfo.extensions(t):
                ext_map[e] = t

        from DBPuppet import dangerous
        for name,info in web_files.items():
            loc,noprefs = info
            ext = dangerous(loc)
            if ext:
                need_to_warn = True
                try:
                    file_type = ext_map[ext]
                    ext_count[file_type] += 1
                except KeyError:
                    pass

        ## NOW look at the code in the file
        py_code  = [a[1] for a in all_cmds if a[0] == 'PC']
        mid_cmds = [a[1] for a in all_cmds if a[0] == 'MC']
        if (py_code or mid_cmds):
            need_to_warn = True

        if not need_to_warn:
            return True

        gen_txt = "The file you have opened contains potentionally " \
                "unsafe code that will be executed in Chimera:\n"

        types = ext_count.keys()
        types.sort()
	from cgi import escape
        for t in types:
            gen_txt += "<p><b><u>" + escape(t) + "</u></b>:"
            added = False
            if ext_count[t] > 0:
                gen_txt += "<br>  <font color=\"red\">This file will open " \
                        "%d additional files containing %s.</font>\n" % \
                        (ext_count[t], escape(t))
                added = True
            if t == "Python" and py_code:
                gen_txt += "<pre>  " + "<br>  ".join([ escape(x) for x in py_code]) + "</pre>\n"
                added = True
            if t == "Chimera commands" and mid_cmds:
                gen_txt += "<pre>  " + "<br>  ".join([ escape(x) for x in mid_cmds]) + "</pre>\n"
                added = True
            if not added:
                gen_txt += "  <i>absent</i>\n"

        res = self.warnUser(gen_txt)
        return res


    def warnUser(self, warn_text):

        from DBPuppet import needToWarn
        if not needToWarn():
            return True

        from DBPuppet import WarnUserDialog
        warning_dlg = WarnUserDialog(warn_text)
        res = warning_dlg.run(chimera.tkgui.app)

        if res == 'yes':
            return True
        else:
            return False


    def open_in_chimera(self, web_files, pdb_ids, all_cmds):
        """'web_files' is a list of files that were dloaded from web, 'pdb_ids' is
        a list of pdb ids, 'mid_cmds' is a list of midas commands
        """

        import chimera

        res = self.warnIfNeeded(web_files, all_cmds)
        if not res:
            self.cleanUpDloaded([v[0] for v in web_files.values()])
            return

        for name,info in web_files.items():
            loc, noprefs = info
            #print "OPENING (web) ", loc
            try:
                chimera.openModels.open("%s" % os.path.abspath(loc), identifyAs=name, noprefs=noprefs )
            finally:
                self.cleanUpDloaded(os.path.abspath(loc))


        for p,noprefs in pdb_ids:
            #print "OPENING (pdb) ", p
            try:
                chimera.openModels.open("%s" % p, type="PDB", noprefs=noprefs)
            except IOError, what:
                raise chimera.UserError("Error while opening model with PDB id '%s': %s" %
                                        (p,what)
                                        )

        cmd_globals = { 'chimera': chimera }
        for a in all_cmds:
            if a[0] == 'MC':
                try:
                    DBPuppet.doMidasCommand(a[1])
                except:
                    chimera.replyobj.error("Error while executing command: \"%s\":\n %s\n" % (a[1], sys.exc_value) )
            elif a[0] == 'PC':
                p = a[1].strip()
                try:
                    exec p in cmd_globals

                except SystemExit:
                    raise

                except chimera.ChimeraSystemExit, v:
                    chimera.triggers.activateTrigger(chimera.APPQUIT, None)
                    raise chimera.ChimeraSystemExit, v

                except:
                    chimera.replyobj.error("Error while executing python code:\n\n"
                                           "--------start code--------\n"
                                           "%s\n"
                                           "--------end code--------\n\n"
                                           % p
                                           )
                    import traceback
                    traceback.print_exc()


    def parse_file_sax(self, infile):
        """expects an open file as 'infile'
        this function takes care of closing the handle
        """

        ## instantiate the xml handler defined below
        handler = StdXMLHandler()

        ## make a parser
        parser  = xml.sax.make_parser()

        ## couple the handler with the parser
        parser.setContentHandler(handler)

        ## parse the file
        try:
            parser.parse(infile)
        except xml.sax.SAXParseException, what:
            infile.close()
            raise chimera.UserError, what
        else:
            infile.close()
            return handler



class StdXMLHandler(xml.sax.handler.ContentHandler):
    """ This class represents the 'handler' for .chimerax files of
    type 'std_webdata' """


    def __init__(self):
        ## to be populated with tuples of (name, url) for files taken from web
        self.web_files     = []

        ## if parser is currently in 'web_files' tag
        self.in_web_files = False
        ## if parser is currently in 'file' tag
        self.in_file      = False

        self.pdb_ids   = []
        self.in_pdb_files = False
        self.in_pdb       = False

        self.all_cmds  = []
        self.mid_cmds  = []
        self.py_cmds   = []

        ## how many elts are in mid_cmds list
        self.mid_cmd_count = 0
        self.py_cmd_count  = 0

        self.in_commands = False
        self.in_mid_cmd  = False
        self.in_py_cmd   = False


    def startElement(self, name, attrs):
        """this function is called when the parser encounters a tag.
        'name' is the name of this tag
        """

        if name == 'web_files':
            self.in_web_files = True
        elif name == 'file':
            ## encountered a file to be downloaded from web
            self.in_file = True
            ## this gets the attributes stored within the tag
            filename = attrs.getValue("name")
            filefmt  = attrs.getValue("format")
            fileloc  = attrs.getValue("loc")
            filenoprefs = eval(attrs.get("noprefs", "True").capitalize())
            self.web_files.append( (filename, filefmt, fileloc, filenoprefs) )
        elif name == 'pdb_files':
            self.in_pdb_files = True
        elif name == 'pdb':
            ## encountered a pdb id
            self.in_pdb = True
            pdb_id = attrs.getValue("id")
            noprefs = eval(attrs.get("noprefs", "True").capitalize())
            self.pdb_ids.append((pdb_id, noprefs))
        elif name == 'commands':
            self.in_commands = True
        elif name == 'mid_cmd':
            ## encountered a midas command
            self.in_mid_cmd = True
            ## append a blank string to the mid_cmds list for now
            ## will be updated as the parser encounters the characters
            ## contained in this tag
            self.mid_cmds.append('')
        elif name == 'py_cmd':
            self.in_py_cmd = True
            self.py_cmds.append('')


    def endElement(self, name):
        if name == 'web_files':
            self.in_web_files = False
        elif name == 'file':
            self.in_file = False
        elif name == 'pdb_files':
            self.in_pdb_files = False
        elif name == 'pdb':
            self.in_pdb = False
        elif name == 'commands':
            self.in_commands = False
        elif name == 'mid_cmd':
            self.in_mid_cmd = False
            self.all_cmds.append( ('MC', self.mid_cmds[self.mid_cmd_count]) )
            self.mid_cmd_count += 1
        elif name == 'py_cmd':
            self.in_py_cmd = False
            self.all_cmds.append( ('PC', self.py_cmds[self.py_cmd_count]) )
            self.py_cmd_count += 1

    def characters(self, data):
        if self.in_mid_cmd:
            ## encountered midas command characters
            ## add them to the correct item in the mid_cmds list
            self.mid_cmds[self.mid_cmd_count] += data
        elif self.in_py_cmd:
            self.py_cmds[self.py_cmd_count] += data

    def getWebFiles(self):
        return self.web_files

    def getPDBs(self):
        return self.pdb_ids

    def getMidCmds(self):
        return self.mid_cmds

    def getPyCmds(self):
        return self.py_cmds

    def getAllCmds(self):
        return self.all_cmds

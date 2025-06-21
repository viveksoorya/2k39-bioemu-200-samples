# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: send_to_chimera.py 39749 2014-04-30 17:46:15Z gregc $

import sys
import filelock

_web_path = None

def _initializeWebPath():
    global _web_path
    import os, tempfile
    try:
        # try USER first because cygwin rewrites USERNAME to user's full name
        username = os.environ["USER"]
    except KeyError:
        # Windows
        try:
            username = os.environ["USERNAME"]
        except KeyError:
            # presumably Windows 98
            username = "everyone"

    web_file = "chimera_webinfo-%s" % username
    _web_path = os.path.join(tempfile.gettempdir(), web_file)
    try:
        lock = getWebFileLock()
        with lock:
            pass
    except (OSError, IOError) as e:
        _web_path = "error: %s.lock: %s" % (_web_path, e)

def getWebFileLock():
    if _web_path is None:
        _initializeWebPath()
    if _web_path.startswith("error:"):
        return None
    return filelock.FileLock(_web_path)

def getWebFile(mode='r', create=False):
    if _web_path is None:
        _initializeWebPath()
    if _web_path.startswith("error:"):
        return None

    import os
    if not os.path.exists(_web_path) and not create:
        return None

    try:
        f = open(_web_path, mode)
    except IOError, what:
        #if what.errno == 13: ##don't have permission to open key file
        #  print "Not Authorized", \
        #  	"You are not authorized to send information to Chimera!"
        return None

    return f

def determineKeys(keyfile):
    key_string = keyfile.readline()
    if not key_string or (len(key_string.split()) != 3):
        #print "couldn't find well-formed key, exiting..."
        return ''
    else:
        return key_string.strip()

def determinePortNumbers(keyfile):
    port_entries = keyfile.readlines()

    if len(port_entries) <= 1:
        #print "no available ports in webinfo file, exiting..."
        return []

    ## get just port entries, not keys
    available_ports = port_entries[1:]
    available_ports = [p.split(",")[0] for p in available_ports]
    available_ports = [int(p) for p in available_ports]
    available_ports.reverse()

    return available_ports

def generate_input_file(path):
    import input_code

    import tempfile
    (file, loc) = tempfile.mkstemp()
    f = open(loc, 'w')

    #mod_path = "\\\\".join(path.split("\\"))

    f.write(input_code.parse_code % (path, path) + "\n")
    f.close()

    return loc

def verify_connection(socket_f, keys):
    ##establish that it is indeed chimera that you are talking to.
    verify = socket_f.readline()

    if not verify.strip()=="CHIMERA":
        #print "not talking to Chimera!!, got %s instead!" % verify
        #socket_f.close()
        #del socket_f
        return False

    ## read the 'keys' from the file. This is an authentication mechanism.
    ## if this was coming from a different computer or different user than
    ## chimerea was running on, you would be unable to open up the keyfile
    ## (because we made it user-only r/w)
    #print "sendalling KEYS: *%s*" % keys

    ## send the key over. If it is the wrong key, chimera will break
    ## the socket connection
    socket_f.write("%s\n" % keys)
    socket_f.flush()

    key_ok = socket_f.readline()
    #print "got **%s** for key_ok" % key_ok
    if key_ok.strip() == "OK":
        #print "KEY OK"
        return True
    elif key_ok.strip() == "NO":
        #print "oops. sent bad key"
        #socket_f.close()
        return False


def send(path):
    socket_f = get_chimera_socket()
    if socket_f is None:
        start_chimera()
        import time
        for i in range(20):
            socket_f = get_chimera_socket()
            if socket_f is not None:
                break
            time.sleep(3)
        else:
            return 'NO CHIMERA FOUND'

    socket_f.write("%s\n" % path)
    socket_f.flush()

    ## don't do anything with this response, but will eventually..
    open_res = socket_f.readline()

    ## close the connection
    socket_f.close()
    return 'SENT'


def get_chimera_socket():
    lock = getWebFileLock()
    if lock is None:
        return
    with lock:
        keyfile = getWebFile('r')
        if not keyfile:
            return None
        with keyfile:
            keys = determineKeys(keyfile)
            if not keys:
                return None
            keyfile.seek(0)
            ports = determinePortNumbers(keyfile)
            keyfile.close()

    s = None
    for p in ports:
        s = socket_to_chimera(p)
        if s:
            break
    else:
        #print "None of the sockets worked...."
        return None

    # Make sure we're really talking to chimera
    socket_f = s.makefile(mode='rw')
    if not verify_connection(socket_f, keys):
        socket_f.close()
        return None
    return socket_f


def socket_to_chimera(port):
    ## using Python sockets here..
    import socket
    ## use an internet socket, streaming transport
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        s.connect(('localhost', port))
    except socket.error:
        s.close()
        s = None
    return s


def start_chimera():
    import os, subprocess
    prog = os.path.join(os.path.dirname(sys.executable), "chimera")
    return subprocess.Popen([prog]).pid


## Start here....
if __name__ == '__main__':
    argc = len(sys.argv)
    if argc != 2:
        syntax()

    ## 'path' is the path to an XML file (presumably downloaded from clicking in a link in a browser)
    path = sys.argv[1]
    send(path)

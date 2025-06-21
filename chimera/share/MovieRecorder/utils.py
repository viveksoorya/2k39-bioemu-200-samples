import os
import string
import random

def getTruncPath(path):
    path_elts = path.split(os.path.sep)
    ## because save path is absolute, the first elt will be ''
    if not path_elts[0]:
        path_elts = path_elts[1:]
    if len(path_elts) <= 4:
        return path
    else:
        first_two = os.path.join(*path_elts[0:2])
        #print "first_two is ", first_two
        last_two = os.path.join(*path_elts[-2:])
        #print "last_two is ", last_two 
        return os.path.sep + os.path.join(first_two, "...", last_two)
    ## don't need the last 
    #path_elts = path_elts[:-1]

def getRandomChars():
    alphanum = string.ascii_letters + string.digits
    return ''.join(random.choice(alphanum) for x in range(4))


import os
from chimera import runCommand # as rc #use 'rc' as shorthand for runCommand
from chimera import replyobj # for emitting status messages
from chimera import dialogs
# change to folder with data files
os.chdir("/home/uni/bioemu-sampling/2k39-bioemu-200-samples/PDBs/visualization-1200-odd-atoms/")

import chimera.dialogs as dialogs
print(dir(dialogs))

import chimera.dialogs as dialogs

print("Open dialogs:")
for d in dialogs._allDialogs:
    print("Dialog name:", d.name)

# gather the names of .pdb files in the folder
file_names = [fn for fn in os.listdir(".") if fn.endswith(".pdb")]

# loop through the files, opening, processing, and closing each in turn
for fn in file_names:
    replyobj.status("Processing " + fn) # show what file we're working on
    runCommand("open " + fn)
    runCommand("ramachandran") # 
	
    # save image to a file that ends in .png rather than .pdb
    plot_dialog = None
    for d in dialogs.activeDialogs():
        if 'Ramachandran' in d.name:
            plot_dialog = d
            break
        try:
            title = None
            if hasattr(d, 'ui') and hasattr(d.ui, 'windowTitle'):
                title = d.ui.windowTitle()
            if title and ('Ramachandran' in title or 'Phi' in title or 'Backbone' in title):
                plot_dialog = d
                break
        except Exception as e:
        # ignore errors in accessing window title
            pass
    if plot_dialog:
        png_name = "ramachandran-plot-of-" + fn[:-3] + "png"
        plot_dialog.ui.saveImage(png_name)
    else:
        print("Ramachandra plot dialog not found")
    runCommand("close all")
# uncommenting the line below will cause Chimera to exit when the script is done
#rc("stop now")
# note that indentation is significant in Python; the fact that
# the above command is exdented means that it is executed after
# the loop completes, whereas the indented commands that 
# preceded it are executed as part of the loop.


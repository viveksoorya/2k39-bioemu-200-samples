from __future__ import print_function


class SafeSave:
    """Replace file with a new version safely.  Returns a writable file object.

    :param filename: name of file to be created or replaced
    :param mode: mode to open new file, defaults to "w" and must be
       overridden if the new file content is binary
    :param retry_interval: number of seconds to wait before retrying
       remove or rename operations
    :param kw: other keyword arguments for open function

    Returns a file object to a temporary file that should be filled
    with new data.  If the file does not exist, 'filename' is used
    as the temporary file name; if the file already exists, the
    'filename' with ".tmp" appended is used.

    The intended use of this class is:

        with SafeSave(file_name) as f:
            write_data(file=f)
    
    If no exception is raised while writing data, the original
    file is removed and the temporary file is renamed to the original
    name.  Both removal and rename are retried once after waiting
    for 'retry_interval' seconds, to allow for transient effects
    such as virus scanners holding the original or new files open.

    If an exception is raised, on closing the file object, the
    temporary file is removed, again with retry after 'retry_interval'
    if the first removal attempt fails.  The exception is untouched
    and the caller is expected to handle it.
    """

    def __init__(self, filename, mode="w", retry_interval=10, open_func=open, **kw):
        # import sys
        # print("ReplaceFile", filename, file=sys.__stderr__, flush=True)
        import os.path
        self.filename = filename
        self.mode = mode
        self.retry_interval = retry_interval
        self.open_func = open_func
        self.open_kw = kw
        self.tmpname = None
        self.file = None

    def __enter__(self):
        # import sys
        # print("enter", file=sys.__stderr__, flush=True)
        import os.path
        if os.path.exists(self.filename):
            # preserve suffix (e.g. '.gz')
            dir_name, fname = os.path.split(self.filename)
            self.tmpname = os.path.join(dir_name, "tmp_" + fname)
        else:
            self.tmpname = self.filename
        self.file = self.open_func(self.tmpname, self.mode, **self.open_kw)
        return self.file

    def __exit__(self, exc_type, exc_value, exc_traceback):
        # import sys
        # print("exit", exc_type, file=sys.__stderr__, flush=True)
        if self.file:
            self.file.close()
            self.file = None
        if exc_type is None:
            # No errors writing out the file
            self._replace_file()
        else:
            # Error writing file, delete temporary
            self._remove_temp()
        # Propagate any exception
        return None

    def _replace_file(self):
        # import sys
        if self.filename == self.tmpname:
            # If original file did not exist, we just wrote it
            # print("done", self.filename,
            #       file=sys.__stderr__, flush=True)
            return
        import os, os.path, time
        try:
            # print("remove", self.filename, "1",
            #       file=sys.__stderr__, flush=True)
            os.remove(self.filename)
        except OSError:
            pass
        if os.path.exists(self.filename):
            # print("remove", self.filename, "2",
            #       file=sys.__stderr__, flush=True)
            time.sleep(self.retry_interval)
            os.remove(self.filename)
        try:
            # print("rename", self.tmpname, self.filename, "1",
            #       file=sys.__stderr__, flush=True)
            os.rename(self.tmpname, self.filename)
        except OSError:
            # print("rename", self.tmpname, self.filename, "2",
            #       file=sys.__stderr__, flush=True)
            time.sleep(self.retry_interval)
            os.rename(self.tmpname, self.filename)

    def _remove_temp(self):
        # import sys
        import os
        try:
            # print("clean", self.tmpname, "1", file=sys.__stderr__, flush=True)
            os.remove(self.tmpname)
        except OSError:
            pass
        if os.path.exists(self.tmpname):
            # print("clean", self.tmpname, "2", file=sys.__stderr__, flush=True)
            time.sleep(self.retry_interval)
            os.remove(self.tmpname)


if __name__ == "__main__":
    import time
    try:
        with SafeSave("xyzzy") as f:
            print(time.ctime(), file=f)
            raise ValueError("oops")
    except ValueError as e:
        print("caught ValueError", e)

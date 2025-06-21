import chimera

#
# Functions below are for starting a thread which can request for
# functions to be executed in the main thread in checkForChanges.
#
# runThread:
# 	Execute the user function "threadFunc" in a thread with
#	first argument of a Queue instance.  Optional arguments
#	are passed to "threadFunc" as additional arguments.
#	"threadFunc" may request callable objects to be executed
#	in the main thread (where Tk fuctions may be called) by
#	placing them onto the given queue.  The main thread checks
#	the queue during checkForChanges.  To exit, the thread
#	should place the Queue instance itself on the queue.
#
threadEndHandler = None
threadQueueMap = {}
def runThread(threadFunc, *args, **kw):
	global threadQueueMap, threadEndHandler
	from Queue import Queue
	from threading import Thread
	q = Queue()
	h = chimera.triggers.addHandler("check for changes", _checkThread, q)
	daemon = kw.pop("daemon", None)
	t = Thread(target=threadFunc, args=(q,) + args, kwargs=kw)
	if daemon is not None:
		t.daemon = daemon
	threadQueueMap[q] = (h, t)
	if threadEndHandler is None:
		threadEndHandler = chimera.triggers.addHandler(
					chimera.APPQUIT, _endThread, None)
	t.start()
	return t

def _checkThread(trigger, q, ignore):
	global threadQueueMap
	from Queue import Empty
	from chimera import ChimeraSystemExit
	while True:
		try:
			callable = q.get(False)
		except Empty:
			break
		if callable is q:
			handler, thread = threadQueueMap.pop(q)
			chimera.triggers.deleteHandler(
					"check for changes", handler)
			break
		try:
			callable()
		except ChimeraSystemExit:
			raise
		except:
			from chimera import replyobj
			replyobj.reportException("thread callback")

def _endThread(trigger, closure, ignore):
	global threadEndHandler
	threadEndHandler = None
        hlist = [handler for handler, thread in threadQueueMap.values()]
        threadQueueMap.clear()
	for handler in hlist:
		chimera.triggers.deleteHandler("check for changes", handler)
		# No way to kill thread yet


# withdrawing checkpointing from image saving, but leaving (commented out)
# code around in case we want to resusitate [chimera/printer.py would
# need crashRecoveryName defined again also]

## delay check until Chimera fully started (ala MacCrashReporter)
#def recoveryCheck(*args):
#	from CheckpointRecovery import recover
#	recover()
#	from chimera.triggerSet import ONESHOT
#	return ONESHOT
#from chimera import triggers
#triggers.addHandler('check for changes', recoveryCheck, None)

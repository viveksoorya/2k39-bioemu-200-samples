from shared import getParams, citation, baseDescription, \
					citeName, cisTrans, citePubmedID

displayName = "Richardson (common-atom)"
description = baseDescription

_independentCache = {}
def independentRotamerParams(resName):
	return getParams(resName, resName, _independentCache, "common.zip")

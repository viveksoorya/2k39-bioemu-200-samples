# --- UCSF Chimera Copyright ---
# Copyright (c) 2000-2009 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: copyright 26655 2009-01-07 22:02:30Z gregc $

class BaseDASError(RuntimeError):
	def __init__(self, *args):
		RuntimeError.__init__(self, self.dasErrMsg % args)

class UnknownDASError(BaseDASError):
	dasErrMsg = "Unknown DAS server error for %s, chain %s"

class NoDASResponseError(BaseDASError):
	dasErrMsg = "No DAS server status (X-DAS-Status) in reply for %s, chain %s"

from collections import defaultdict
dasErrors = defaultdict(UnknownDASError)

class BadDASCommandError(BaseDASError):
	dasErrMsg = "Bad DAS command for %s, chain %s"
dasErrors[400] = BadDASCommandError

class BadDASDataSourceError(BaseDASError):
	dasErrMsg = "Bad DAS data source for %s, chain %s"
dasErrors[401] = BadDASDataSourceError

class BadDASCommandArgsError(BaseDASError):
	dasErrMsg = "Bad DAS command arguments for %s, chain %s"
dasErrors[402] = BadDASCommandArgsError

class BadDASRefObjError(BaseDASError):
	dasErrMsg = "Bad DAS reference object for %s, chain %s"
dasErrors[403] = BadDASRefObjError

class BadDASStylesheetError(BaseDASError):
	dasErrMsg = "Bad DAS stylesheet for %s, chain %s"
dasErrors[404] = BadDASStylesheetError

class BadDASCoordinateError(BaseDASError):
	dasErrMsg = "Sequence coordinate out of bounds for %s, chain %s"
dasErrors[405] = BadDASCoordinateError

class UnknownDASServerError(BaseDASError):
	dasErrMsg = "Unknown DAS server error for %s, chain %s"
dasErrors[500] = UnknownDASServerError

class UnimplementedDASServerFeatureError(BaseDASError):
	dasErrMsg = "Unimplemented DAS server feature for %s, chain %s"
dasErrors[501] = UnimplementedDASServerFeatureError

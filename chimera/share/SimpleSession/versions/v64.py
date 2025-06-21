# --- UCSF Chimera Copyright ---
# Copyright (c) 2000 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  This notice must be embedded in or
# attached to all copies, including partial copies, of the
# software or any revisions or derivations thereof.
# --- UCSF Chimera Copyright ---
#
# $Id: v38.py,v 1.1 2008-11-11 01:04:35 goddard Exp $

from v63 import *

import globals # so that various version files can easily access same variables
import chimera

def restorePseudoBondGroups(pbInfo):
	# work around 1.5.3 hack where v52 imported v50 directly
	if 'display' not in pbInfo:
		import v50
		return v50.restorePseudoBondGroups(pbInfo)
	from SimpleSession import registerAttribute
	from chimera.misc import getPseudoBondGroup
	mgr = chimera.PseudoBondMgr.mgr()
	sm = globals.sessionMap
	groups = []
	for category, id, color, display, showStubBonds, lineWidth, stickScale, \
	lineType, bondInfo in zip(
				pbInfo['category'],
				pbInfo['id'],
				expandSummary(pbInfo['color']),
				expandSummary(pbInfo['display']),
				expandSummary(pbInfo['showStubBonds']),
				expandSummary(pbInfo['lineWidth']),
				expandSummary(pbInfo['stickScale']),
				expandSummary(pbInfo['lineType']),
				pbInfo['bondInfo']
				):
		g = getPseudoBondGroup(category, id)
		groups.append(g)
		g.color = getColor(color)
		g.display = display
		g.showStubBonds = showStubBonds
		g.lineWidth = lineWidth
		g.stickScale = stickScale
		g.lineType = lineType
		for atoms, drawMode, display, halfbond, label, color, \
		labelColor, labelOffset in zip(
					bondInfo['atoms'],
					expandSummary(bondInfo['drawMode']),
					expandSummary(bondInfo['display']),
					expandSummary(bondInfo['halfbond']),
					expandSummary(bondInfo['label']),
					expandSummary(bondInfo['color']),
					expandSummary(bondInfo['labelColor']),
					expandSummary(bondInfo['labelOffset'])
					):
			a1, a2 = [idLookup(a) for a in atoms]
			pb = g.newPseudoBond(a1, a2)
			pb.drawMode = drawMode
			pb.display = display
			pb.halfbond = halfbond
			pb.label = label
			pb.color = getColor(color)
			pb.labelColor = getColor(labelColor)
			if labelOffset is not None:
				pb.labelOffset = labelOffset
			sm[len(sm)] = pb
	if pbInfo['optional']:
		for attrName, info in pbInfo['optional'].items():
			hashable, sequential, sv = info
			registerAttribute(chimera.PseudoBondGroup, attrName,
							hashable=hashable)
			if sequential:
				vals = expandSequentialSummary(sv)
			else:
				vals = expandSummary(sv, hashable=hashable)
			for g, val in zip(groups, vals):
				if val is not None:
					setattr(g, attrName, val)
	for g in groups:
		sm[len(sm)] = g

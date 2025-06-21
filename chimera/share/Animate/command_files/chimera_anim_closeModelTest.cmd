close session

open 1gcn
focus
scene 1gcn save

open 1gix
focus
scene 1gcn+1gix save

pause end

# Explore how closing a model will
# impact the saved scene states, e.g.
# remove 1gix and update second scene
close #1
scene 1gcn+1gix restore # this should still work
scene 1gcn+1gix save 	# this will "update" the scene


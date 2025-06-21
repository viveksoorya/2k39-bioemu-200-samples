close session
open 1gcn
display
~ribbon
chain @ca
# save the scene state (which will exclude all
# hidden models with model.id > 0)
scene 1gcn-chain save
# now remove the chain trace and this 
# should not invalidate the scene state
display

close session
open 1gix
scene 1gix save
scene 1gix reset

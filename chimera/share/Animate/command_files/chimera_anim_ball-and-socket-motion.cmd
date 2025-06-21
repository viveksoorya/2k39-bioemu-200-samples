#                                                    ECMeng Aug 2010
#                                                    Chimera v1.5
# thioredoxin reductase "ball and socket" movement upon binding NADPH
#   1tdeA (complex with FAD) 
#   1f6mA (complex with FAD and NADP+ analog) ...1 residue is different
#
windowsize 480 480
open 1tde
open 1f6m
del #1:.b-h
del #1 & #1:.a z>5
del solvent | H | :2500.het
mm #0 #1
preset apply int 1
modelcol purple #0; modelcol gold #1
rep stick; show ligand; col byhet ligand; ~disp #1:fad; setattr m stickScale 2
preset apply pub 1
turn z 120; focus; scale 1.25; move y -4; move x 3.5; wait
turn x -15; wait
turn z 10; wait
cofr #1:3aa@c5d
2dlab create title text 'Ball-and-Socket Motion' size 34 xpos .11 ypos .93 color black
2dlab create fad text 'FAD (in both)' size 20 xpos .02 ypos .59 color .63,.12,.94
2dlab create nadp text 'NADP\u207a analog' size 20 xpos .02 ypos .54 color .86,.65,.12
2dlab create enzyme text 'thioredoxin reductase' size 20 xpos .02 ypos .03 color black
2dlab create struct1 text 1tde size 20 xpos .68 ypos .03 color .63,.12,.94
2dlab create struct2 text 1f6m size 20 xpos .79 ypos .03 color .86,.65,.12
#
#  rotate superimposed structures
#
movie record supersample 3
wait 10
roll y 2 180; wait
wait 10
movie stop
#
#  create morph
#
morph start #0 frames 25
morph interpolate #1 frames 25
morph movie
savepos p1
modelcol cornflower blue #2; ~ribbon #0,1; ~disp #1:3aa
#
#  play morph 0 -> 1 -> 0 -> 1
#
movie record supersample 3
2dlab create morphlab text morphing... size 24 style bold color cornflower blue xpos .05 ypos .75 visibility hide
2dlab change morphlab visibility show frames 20; wait
coordset #2 1,26,1; wait 26
disp #1:3aa; wait 40
~disp #1:3aa; wait
coordset #2 25,1,-1; wait 25
wait 20
coordset #2 1,26,1; wait 26
disp #1:3aa; wait 20
2dlab change morphlab visibility hide frames 20
wait 20
movie stop
movie encode output ~/Desktop/trmovie.mov

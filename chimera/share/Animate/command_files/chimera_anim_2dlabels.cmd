close session

# 2dlabels change name [ text label-contents ] [ color label-color ]
# [ size font-size ] [ style font-style ] [ typeface font-typeface ]
# [ xpos x-position ] [ ypos y-position ]
# [ visibility hide | show [ frames N ]]

2dlabels create label1 text 'label1' xpos 0.1 ypos 0.9
2dlabels create label2 text 'label2' xpos 0.4 ypos 0.5
2dlabels create label3 text 'label3' xpos 0.7 ypos 0.1
wait
scene sc1 save

2dlabels change label1 visibility hide frames 10
2dlabels change label2 visibility hide frames 10
2dlabels change label3 visibility hide frames 10
wait
scene sc2 save

2dlabels change label1 text 'label1_test'
2dlabels change label1 xpos 0.7 ypos 0.9
2dlabels change label1 color 'red'
2dlabels change label1 size 18
2dlabels change label1 style 'bold'
2dlabels change label1 typeface 'sans serif'
wait
2dlabels change label2 text 'label2_test'
2dlabels change label2 xpos 0.4 ypos 0.5
2dlabels change label2 color 'green'
2dlabels change label2 size 24
2dlabels change label2 style 'bold'
2dlabels change label2 typeface 'fixed'
wait
2dlabels change label3 text 'label3_test'
2dlabels change label3 xpos 0.1 ypos 0.1
2dlabels change label3 color 'blue'
2dlabels change label3 size 42
2dlabels change label3 style 'italic'
2dlabels change label3 typeface 'serif'
wait
2dlabels change label1 visibility show frames 10
2dlabels change label2 visibility show frames 10
2dlabels change label3 visibility show frames 10
wait
scene sc3 save

kfadd sc1
kfadd sc2
kfadd sc3

kfshow sc1
kfmovie loop
kfmovie play

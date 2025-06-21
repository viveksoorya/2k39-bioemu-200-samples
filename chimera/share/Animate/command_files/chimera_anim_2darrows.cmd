close session

# --- Arrows ---

# 2dlabels acreate name start x1,y1  end x2,y2 [ color arrow-color ]
# [ weight weight ] [ head blocky | solid | pointy | pointer ]
# [ visibility hide | show ] 

# 2dlabels achange name [ color arrow-color ] [ weight weight ]
# [ head blocky | solid | pointy | pointer ]
# [ visibility hide | show [ frames N ]]

2dlabels acreate arrow1 start 0.1,0.85 end 0.2,0.85 head pointy weight 0.5
2dlabels acreate arrow2 start 0.1,0.80 end 0.4,0.80 head pointy weight 0.5
wait
scene sc1 save

2dlabels achange arrow1 visibility hide
2dlabels achange arrow2 visibility hide
wait
scene sc2 save

2dlabels achange arrow1 visibility show
2dlabels achange arrow1 color 'red'
2dlabels achange arrow1 head blocky
2dlabels achange arrow2 weight 0.7
#2dlabels achange arrow1 start 0.1,0.10 end 0.2,0.10
2dlabels achange arrow2 visibility show
2dlabels achange arrow2 color 'yellow'
2dlabels achange arrow2 head solid
2dlabels achange arrow2 weight 0.3
#2dlabels achange arrow2 start 0.1,0.05 end 0.2,0.05
wait
scene sc3 save

2dlabels achange arrow1 color 'green'
2dlabels achange arrow2 color 'blue'
2dlabels achange arrow2 head pointer
wait
scene sc4 save

kfadd sc1
kfadd sc2
kfadd sc3
kfadd sc2
kfadd sc4
kfadd sc2

kfshow sc1
#kfmovie loop
#kfmovie play

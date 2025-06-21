# -----------------------------------------------------------------------------
#
def play(*args):
    import Play as P
    P.play_command(*args)
def reverse_play(*args):
    import Play as P
    P.unplay_command(*args)

# -----------------------------------------------------------------------------
# Register play command.
#
from Midas.midas_text import addCommand
addCommand('play', play, reverse_play, help = ('play.html', 'Play'))

def zone_cmd(cmdname, args):
    import Zone
    Zone.zone_command(cmdname, args)
    
import Midas.midas_text
Midas.midas_text.addCommand('zonesel', zone_cmd, help = True)

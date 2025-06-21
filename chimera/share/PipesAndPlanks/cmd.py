# Add Chimera pipes and planks command "pp".

def pp_cmd(cmd_name, args):
    from Midas import midas_text
    midas_text.doExtensionFunc(pp, args, specInfo = [('modelSpec', 'mols', 'molecules')])

def unpp_cmd(cmd_name, args):
    from Midas import midas_text
    midas_text.doExtensionFunc(unpp, args, specInfo = [('modelSpec', 'mols', 'molecules')])

def pp(mols,
       helixColor = None,
       helixEdgeColor = None,
       helixArrow = True,
       helixFixedRadius = True,
       helixRadius = 1.25,
       helixSplit = False,
       helixSplitRatio = 2.5,
       strandColor = None,
       strandEdgeColor = None,
       strandArrow = True,
       strandFixedWidth = True,
       strandWidth = 2.5,
       strandFixedThickness = True,
       strandThickness = 1.0,
       strandSplit = False,
       strandSplitRatio = 2.5,
       displayCoils = True,
       coilColor = None,
       coilEdgeColor = None,
       coilSubdivision = 10,
       coilWidth = 0.25,
       coilThickness = 0.25):

    unpp(mols)

    from PipesAndPlanks.base import makePandP
    for mol in mols:
        makePandP(mol,
                  helixColor,
                  helixEdgeColor,
                  helixArrow,
                  helixFixedRadius,
                  helixRadius,
                  helixSplit,
                  helixSplitRatio,
                  strandColor,
                  strandEdgeColor,
                  strandArrow,
                  strandFixedWidth,
                  strandWidth,
                  strandFixedThickness,
                  strandThickness,
                  strandSplit,
                  strandSplitRatio,
                  displayCoils,
                  coilColor,
                  coilEdgeColor,
                  coilSubdivision,
                  coilWidth,
                  coilThickness)
        mol.display = False

def unpp(mols):
    from chimera import openModels as om
    for mol in mols:
        pmlist = [p for p in om.list(id = mol.id, subid = mol.subid)
                    if p.name.endswith('Pipes and Planks')]
        if pmlist:
            om.close(pmlist)
            mol.display = True

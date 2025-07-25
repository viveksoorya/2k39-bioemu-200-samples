from openmm import *
from openmm.app import *
from sys import stdout

# first you need your biomolecule to simulate
pdb = PDBFile("topology-1200-odd-atoms.pdb")

# then you need the forcefields
forcefield = ForceField("amber19-all.xml", "amber19/tip3pfb.xml")

# then you make a system with the forcefields and the given topology
system = forcefield.createSystem(pdb.topology, nonbondedMethod=PME, nonbondedCutoff=1*nanometer, constraints=HBonds)

# once you have a system, you have solved the static part
# now dynamics: we start with the integrator for motion

LangevinMiddleIntegrator(300*kelvin, 1/picosecond, 0.004*picoseconds)   # what is the friction coefficient, the second parameter

# now that we have the static image and the integrator, we can get the simulation by putting these two together
simulation = Simulation(pdb.topology, system, integrator)

# now that we have set the object of simulation, we can manipulate the simulation 
simulation.context.setPositions(pdb.positions)

# since we have the system up and running now, lets start doing something
simulation.minimizeEnergy()

# now as this goes, it would be nice to have the program report us periodically; we achieve this using reporters from the std file of sys module: the state data reporter reports periodically, while the DCDReporter catches all the structures in the specified file path every 1000 steps
simulation.reporters.append(DCDReporter('output-structures.dcd', 1000)) 
simulation.reporters.append(StateDataReporter(stdout, 1000)) 

# now that we have configured the final parts of our simulation, we can now run it
simulation.step(10000)

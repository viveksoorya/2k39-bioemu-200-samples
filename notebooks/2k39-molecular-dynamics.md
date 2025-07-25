known steps:
fix parameters
solvate
equilibrate
run production

simulate the equilibration
simulate the production

unknown steps:

unknown imports
	there are a bunch of open mm imports: openmm, openmm.app, openmm.unit
	numpy is imported
	mdtraj and from sys stdout is imported

unknown functions:
	PDBFILE() for recall
	LangevinIntegrator()
	Modeller()
		
	Simulation() 
		-- simulation object
		-- contains data about the simulation itself and not particularly the system
	ForceField()
	CustomExternalForce()
	CustomCVForce()
	these functions above created objects	

Process:
The Simulation() function takes four parameters: Platform to run the simulation on, the system ie modell

"""
Author: Shreya Chidambaram
"""

from openmm.app import *
from openmm import *
from openmm.unit import *
import numpy as np
from sys import stdout
import mdtraj as md

# === Load the protein ===
pdb = PDBFile('2LUM_fixed.pdb')
forcefield = ForceField('amber14-all.xml', 'amber14/tip3pfb.xml')

# === Solvate and neutralize ===
modeller = Modeller(pdb.topology, pdb.positions)
modeller.addSolvent(forcefield, padding=1.0*nanometers, ionicStrength=0.15*molar, neutralize=True)

# === Print ion counts ===
na_atoms = [atom for atom in modeller.topology.atoms() if atom.name == 'Na+']
cl_atoms = [atom for atom in modeller.topology.atoms() if atom.name == 'Cl-']
print(f"✅ Ions added: Na+ = {len(na_atoms)}, Cl- = {len(cl_atoms)}")

# === Create system for equilibration ===
equil_system = forcefield.createSystem(modeller.topology, nonbondedMethod=PME,
                                       nonbondedCutoff=1.0*nanometers, constraints=HBonds)

# === Simulation parameters ===
temperature = 300*kelvin
friction = 1/picosecond
timestep = 1*femtosecond
platform = Platform.getPlatformByName('CPU')

# === Equilibration ===
print("🧊 Minimizing and equilibrating...")
equil_integrator = LangevinIntegrator(temperature, friction, timestep)
equil_sim = Simulation(modeller.topology, equil_system, equil_integrator, platform)
equil_sim.context.setPositions(modeller.positions)
equil_sim.minimizeEnergy()
equil_sim.context.setVelocitiesToTemperature(temperature)
equil_sim.step(10000)

# Save equilibrated state
equil_state = equil_sim.context.getState(getPositions=True, getVelocities=True)

# Save solvated structure
PDBFile.writeFile(modeller.topology, modeller.positions, open('2LUM_solvated_ions.pdb', 'w'))

# === Create new system for production with aMD boost ===
boost_system = forcefield.createSystem(modeller.topology, nonbondedMethod=PME,
                                       nonbondedCutoff=1.0*nanometers, constraints=HBonds)

# === Boost parameters ===
E = 100 * kilojoule_per_mole
alpha = 25 * kilojoule_per_mole

# === Add boost via CustomCVForce ===
# Step 1: Create dummy force
dummy = CustomExternalForce("0")
for i in range(boost_system.getNumParticles()):
    dummy.addParticle(i, [])

# Step 2: Create boost CV force and add dummy to it
boost = CustomCVForce("step(E - V)*(E - V)^2 / (alpha + E - V)")
boost.addGlobalParameter("E", E)
boost.addGlobalParameter("alpha", alpha)
boost.addCollectiveVariable("V", dummy)  # Must happen BEFORE boost is added to the system

# Step 3: Add the boost force to the system
boost_system.addForce(boost)

# === Production simulation ===
print("🚀 Starting single-boost aMD production run...")
prod_integrator = LangevinIntegrator(temperature, friction, timestep)
simulation = Simulation(modeller.topology, boost_system, prod_integrator, platform)
simulation.context.setState(equil_state)

# === Reporters ===
simulation.reporters.append(DCDReporter('2lum_single_amd.dcd', 5000))
simulation.reporters.append(StateDataReporter(stdout, 5000, step=True, potentialEnergy=True,
    temperature=True, progress=True, speed=True, remainingTime=True, totalSteps=500_000_000, separator='\t'))

# === Run ===
simulation.step(300_000_000) #3ns simulation
print("✅ Single-boost aMD simulation complete.")



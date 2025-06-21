from MMMD.MMTKinter import *

class DynamicsTrajectory:
	def __len__(self):
		return len(self.molecule.coordSets)
	def __getitem__(self, key):
		return None

class mdMMTKinter(MMTKinter):
	

	def __init__(self, mols, trajectory, autoPBC = False, PBCbox = False, *args, **kw):
		self.traj = trajectory
		self.heatTraj = None
		self.prodTraj = None
		self.PBCbox = PBCbox
		self.autoPBC = autoPBC
		self.production=False
		MMTKinter.__init__(self, mols, *args, **kw)

	def _makeUniverse(self):
		import os.path
		parmDir = os.path.dirname(__file__)
		timestamp("_makeUniverse")
		from MMTK import InfiniteUniverse, Vector
		from MMTK.ForceFields.Amber import AmberData
		from MMTK.ForceFields.Amber.AmberForceField import readAmber99
		from MMTK.ForceFields.MMForceField import MMForceField

		#
		# GAFF uses lower case atom types to distinguish
		# from Amber atom types.  MMTK, however, normalizes
		# all atom types to upper case.  So we hack MMTK
		# and temporarily replace _normalizeName function
		# with ours while reading our parameter files.
		# (We have to reread the parameter file each time
		# because we potentially have different frcmod files
		# for the different universes.)
		#
	
		saveNormalizeName = AmberData._normalizeName
		AmberData._normalizeName = simpleNormalizeName
		modFiles = [ unicode(m.frcmod) for m in self.molecules
				if m.frcmod is not None]
		from AmberInfo import amberHome
		paramDir = os.path.join(amberHome, "dat", "leap", "parm")
		parameters = readAmber99(os.path.join(paramDir, "gaff.dat"), modFiles)
		self._mergeAmber99(parameters)
		bondedScaleFactor = 1.0
		esOptions = self.esOptions
		ljOptions = self.ljOptions
		ff = MMForceField("Amber99/GAFF", parameters, ljOptions,
					esOptions, bondedScaleFactor)
		ff.arguments = ff.arguments[:1] + (None,) + ff.arguments[2:]
		AmberData._normalizeName = saveNormalizeName

		timestamp("Made forcefield")
		if self.PBCbox == False:
			self.universe = InfiniteUniverse(ff)
		else:
			import MMTK
			from MMTK import OrthorhombicPeriodicUniverse, Units
			if self.autoPBC:
				self.universe = InfiniteUniverse(ff)
			else:
				self.universe = OrthorhombicPeriodicUniverse((float(self.PBCbox[0])*Units.Ang,float(self.PBCbox[1])*Units.Ang,float(self.PBCbox[2])*Units.Ang),ff)
	
		timestamp("Made universe")
		for mm in self.molecules:
			self.universe.addObject(mm)
			timestamp("Added model %s" % mm.name)
		timestamp("end _makeUniverse")

		self.initial_ff = self.universe.forcefield()

	def setAutoPBCUniverse(self):
		from MMTK import Vector, OrthorhombicPeriodicUniverse, Units
		box = self.universe.boundingBox()
		box = box[1]-box[0]+Vector(0.2,0.2,0.2)
		for mm in self.molecules:
			self.universe.removeObject(mm)
		self.universe = OrthorhombicPeriodicUniverse(tuple(box),self.initial_ff)
		print "Auto-PBC universe size: %g %g %g" % tuple(box*10.0)
		timestamp("Making new PBC universe: %g %g %g" % tuple(box))
		for mm in self.molecules:
			self.universe.addObject(mm)
			timestamp("Added model %s" % mm.name)
		timestamp("end _makeUniverse")

		
	def tag_atoms(self, selected_atoms):

		for a in self.universe.atomList():
			if a in selected_atoms: 
				a.fixed = 1
			else:
				a.fixed = 0
	
	def dynamics(self, frame,
			heatMD = None, prodMD = None, dynVar = None,
			fixed = None, filename = None, outside = False, generate = False, 
			multi=1, live = None, rot = True, trans = True):
	
		if fixed:
			selected_atoms = [self.atomMap[a] for a in fixed]
			self.tag_atoms(selected_atoms)

		if outside or generate:
			self.runInBackground(dynVar, frame, filename, outside, generate, multi = multi, heater = heatMD, rot = rot, trans = trans)
			return
	
		fileChecks = []
		if heatMD:
			fileChecks.extend([("heat", "equilibration"), ("heatRes", "equilibration restart")])
		if prodMD:
			fileChecks.extend([("prod", "production"), ("prodRes", "production restart")])
		for ftype, descript in fileChecks:
			try:
				self.traj[ftype].encode("ascii")
			except KeyError:
				if ftype == "prodRes":
					# prodRes is optional
					continue
				raise
			except UnicodeError:
				from chimera import LimitationError
				raise LimitationError("The %s output file name, and the name of all folders"
					" above it, must be composed of only ASCII characters.  We hope to remove this"
					" limitation in a future release." % descript)
		try:
			if heatMD:
				self.heatDynamics(heatMD, prodMD, dynVar, multi, frame, rot, trans, live)
				return
			if prodMD:
				self.prodDynamics(prodMD, dynVar, multi, frame, rot, trans, live)
				return
		except ValueError, v:
			if str(v) == "trajectory file not compatible with universe":
				from chimera import UserError
				raise UserError("The existing trajectory output files are not compatible"
					" with the current molecular system, and therefore cannot"
					" be appended to with additional MD steps.  You need to"
					" either remove/rename the existing files, or specify"
					" different file names for output.")
			else:
				raise

	def heatDynamics(self, heatMD, prodMD, dynVar, multi, frame, rot, trans, live):
		from MMTK import Units, ParticleVector
		from MMTK.Dynamics import VelocityVerletIntegrator, TranslationRemover, BarostatReset, \
			RotationRemover, Heater, VelocityScaler
		from MMTK.Trajectory import TrajectoryOutput, Trajectory, LogOutput, RestartTrajectoryOutput
		from MMTK.Environment import AndersenBarostat
		import chimera

		integrator = VelocityVerletIntegrator(self.universe, delta_t = int(heatMD["int"])*Units.fs,
								background = True)
		import os
		noExt = os.path.splitext(self.traj["heat"])[0]
		shortName = os.path.basename(noExt)
		trajectory = Trajectory(self.universe, "%s" % self.traj["heat"],"w","%s's Dynamics" % shortName, with_database=True)

		timestamp("Dynamic Running")
		dynActions = list()
		if "iTemp" in heatMD:
			itemp = float(heatMD["iTemp"])
			ftemp = float(heatMD["fTemp"])
			dynActions.append(Heater(itemp*Units.K,ftemp*Units.K,float(heatMD["grad"])*Units.K/Units.fs,int(heatMD["first"]),heatMD["last"],int(heatMD["skip"])))

		else:
			dynActions.append(VelocityScaler(heatMD["velTemp"],heatMD["velTemp_win"],heatMD["velFirst"],heatMD["velLast"],heatMD["velSkip"]))
			itemp = ftemp = heatMD["velTemp"]
		self.universe.initializeVelocitiesToTemperature(itemp*Units.K)

		if rot:
			dynActions.append(RotationRemover(dynVar["rfirst"],dynVar["rlast"],dynVar["rskip"]))
		if trans:
			dynActions.append(TranslationRemover(dynVar["tfirst"],dynVar["tlast"],dynVar["tskip"]))

		dynActions.append(TrajectoryOutput(trajectory,('configuration','energy','thermodynamic','time', 'auxiliary'), frame, None, frame))
		dynActions.append(LogOutput("%s.log" % noExt, ('time', 'energy'), 0, None, 100))

		if prodMD:
			dynActions.append(RestartTrajectoryOutput("%s" % self.traj["heatRes"], 5))
		if live:
			thread = integrator(steps = int(heatMD["steps"]),
				threads = int(multi),
				actions = dynActions)
			atomMap = {}
			for ca, ma in self.atomMap.iteritems():
				atomMap[ma] = ca
			from MMTK2Molecule import updateChimera
			updateChimera(thread, self.universe, atomMap, 1)
			while thread.is_alive():
				thread.join(0.01)
				chimera.tkgui.app.update()
	
		else:
			self._doDynamics(integrator,"Equilibration",int(heatMD["steps"]),1000,dynActions,int(multi),ftemp=ftemp)

		self.heatTraj = trajectory

		if prodMD:
			self.prodDynamics(prodMD, dynVar, multi, frame, rot, trans, live)
			return
		else:
			self.readTrajectory()
			
	def prodDynamics(self, prodMD, dynVar, multi, frame, rot, trans, live):
		from MMTK import Units, ParticleVector
		from MMTK.Dynamics import VelocityVerletIntegrator, VelocityScaler, \
					TranslationRemover, BarostatReset, RotationRemover
		from MMTK.Environment import NoseThermostat, AndersenBarostat
		from MMTK.Trajectory import TrajectoryOutput, Trajectory, LogOutput, RestartTrajectoryOutput
		import chimera

 		try:
 			self.universe.setFromTrajectory(Trajectory(self.universe, "%s" % self.traj["heatRes"]),-1)
 			try:	
 				self.universe.thermostat = NoseThermostat(float(prodMD["thermostat"])*Units.K, relaxation_time=float(prodMD["thermostatRelax"]))
 			except:
 				pass 
 			try:	
 				self.universe.barostat = AndersenBarostat(float(prodMD["bar"])*Units.Pa, relaxation_time=float(prodMD["barRelax"]))
 			except:
 				pass
 		except IOError:
 			self.universe.initializeVelocitiesToTemperature(50.0*Units.K)
 			try:	
 				self.universe.thermostat = NoseThermostat(float(prodMD["thermostat"])*Units.K, relaxation_time=float(prodMD["thermostatRelax"]))
 			except:
 				pass
 			try:	
 				self.universe.barostat = AndersenBarostat(float(prodMD["bar"])*Units.Pa, relaxation_time=float(prodMD["barRelax"]))
 			except:
 				pass
		
		integrator = VelocityVerletIntegrator(self.universe, delta_t = int(prodMD["int"])*Units.fs,
								background = True)
		import os
		noExt=os.path.splitext(self.traj["prod"])[0]
		shortName=os.path.basename(noExt)
		trajectory=Trajectory(self.universe, "%s" % self.traj["prod"],"w","%s's Dynamics" % shortName, with_database=True)

		timestamp("Dynamic Running")
		dynActions = list()
		
		if rot:
			dynActions.append(RotationRemover(dynVar["rfirst"],dynVar["rlast"],dynVar["rskip"]))
		if trans:
			dynActions.append(TranslationRemover(dynVar["tfirst"],dynVar["tlast"],dynVar["tskip"]))

		#dynActions.append(TrajectoryOutput(trajectory,('configuration','energy','thermodynamic','time', 'auxiliary'), 0, None, frame))
		dynActions.append(TrajectoryOutput(trajectory,('configuration','energy','thermodynamic','time'), frame, None, frame))
		dynActions.append(LogOutput("%s.log" % noExt, ('time', 'energy'), 0, None, 100))

		try:
			dynActions.append(BarostatReset(prodMD["barFirst"],prodMD["barLast"],prodMD["skip"]))
		except:
			pass
		try:
			dynActions.append(VelocityScaler(prodMD["velTemp"],prodMD["velTemp_win"],prodMD["velFirst"],prodMD["velLast"],prodMD["velSkip"]))
		except:
			pass

		try:
			dynActions.append(RestartTrajectoryOutput("%s" % self.traj["prodRes"], 5))
		except:
			pass

		if live:
			thread = integrator(steps = int(prodMD["steps"]),
				threads = int(multi),
				actions = dynActions)
			atomMap = {}
			for ca, ma in self.atomMap.iteritems():
				atomMap[ma] = ca
			from MMTK2Molecule import updateChimera
			updateChimera(thread, self.universe, atomMap, 1)
			while thread.is_alive():
				thread.join(0.01)
				chimera.tkgui.app.update()
		else:
			self._doDynamics(integrator,"Production",int(prodMD["steps"]),1000,dynActions,int(multi))
		self.prodTraj = trajectory
		self.readTrajectory()

	def _doDynamics(self, dynamic, name, steps, interval, actions, multi,ftemp=None):
		from chimera import replyobj
		from MMTK.Trajectory import Trajectory
		from MMTK import Units
		from MMTK.Dynamics import VelocityScaler
		remaining = steps
		removeHeater=0
		while remaining > 0:
			if interval is None:
				realSteps = remaining
			else:
				realSteps = min(remaining, interval)
			if str(name) == "Equilibration":
				if removeHeater==1 and ftemp != None:
					del actions[0]
					actions.append(VelocityScaler(ftemp*Units.K,0,1,None,1))
			thread = dynamic(steps = realSteps, threads=multi, actions= actions)
			thread.join()
			remaining -= realSteps

			timestamp(" finished %d steps" % realSteps)
			msg = "Finished %d of %d steps from %s dynamic phase" % (
						steps - remaining, steps, name)
			replyobj.status(msg)
			replyobj.info(msg)
			removeHeater+=1
		replyobj.info("\n")

	def writeScript(self, dynVar, frame, filename, multi=None, heater = None, rot = True, trans = True):

		f = open("%s.py" % filename, "w")
		print >> f, "from MMTK import Units, ParticleVector"
		print >> f, "from MMTK.ForceFields import Amber99ForceField"
		print >> f, "from MMTK.Dynamics import VelocityVerletIntegrator, VelocityScaler,\\"
		print >> f, "\t\t\t\tTranslationRemover, BarostatReset, RotationRemover"
		print >> f, "from MMTK.Environment import NoseThermostat, AndersenBarostat"
		print >> f, "from MMTK.Trajectory import TrajectoryOutput, Trajectory, LogOutput"
		print >> f, "import sys"
		print >> f, "import MMTK\n"
		
		print >> f, "universe = MMTK.load(\"%s.mmtk\")" % filename
		print >> f, "universe.initializeVelocitiesToTemperature(%s.*Units.K)" % dynVar["temperatureProd"]
		print >> f, "integrator = VelocityVerletIntegrator(universe, delta_t = %s.*Units.fs)" % dynVar["integrationProd"]
		print >> f, "trajectory = Trajectory(universe, \"%s\", \"w\", \"%s Dynamics\", with_database=True)" % (self.traj["prod"], self.traj["prod"])

		print >> f, "integrator(steps = %s," % dynVar["prodStepsProd"]
		if multi:
			print >> f, "\tthreads=%i," % multi
		else:
			pass
		print >> f, "\tactions = ["
		if trans:
			print >> f, "\t\tTranslationRemover(%s,%s,%s)," % (dynVar["tfirst"],dynVar["tlast"],dynVar["tskip"])
		if rot:
			print >> f, "\t\tRotationRemover(%s,%s,%s)," % (dynVar["rfirst"],dynVar["rlast"],dynVar["rskip"])
		print >> f, "\t\tTrajectoryOutput(trajectory,"
		print >> f, "\t\t\t('configuration', 'energy', 'thermodynamic',"
		print >> f, "\t\t\t'time', 'auxiliary'), %s, None, %s)," % (frame, frame)
		if heater:
			print >> f, "\t\t\tHeater(%f*Units.K,%f*Units.K,%f*Units.K/Units.fs,%i,%s,%i)," % (dynVar["iTemp"],dynVar["fTemp"],dynVar["grad"],dynVar["first"],dynVar["last"],dynVar["skip"])
		print >> f, "\t\tLogOutput(\"%s.log\", ('time', 'energy'), 0, None, 100)])" % self.traj["prod"]
		print >> f, "\ntrajectory.close()"
		print >> f, "MMTK.save(universe, \"%s.mmtk\")" % filename
		
		f.close()

	def deleteChimeraAtoms(self):

		for a in self.universe.atomList():
			del a.chimera_atom

		#del self.universe._environment
		for a in self.molecules:
			del a.needParmchk

		for a in self.universe.objectList():
			del a.atomMap
			del a.chimeraMolecule

	def saveData(self):
		
		saveData = dict()
		for a in self.universe.objectList():
			saveData[a] = [a.atomMap, a.chimeraMolecule]
		saveParmchk = dict()
		for a in self.molecules:
			saveParmchk[a] = [a.needParmchk]
		return saveData,saveParmchk

	def restoreChimeraAtoms(self, saveData, saveParmchk):

		for ma in self.universe.atomList():
			for ca, ma in self.atomMap.iteritems():
				ma.chimera_atom = ca

		for a in self.universe.objectList():
			a.atomMap = saveData[a][0]	
			a.chimeraMolecule = saveData[a][1]

		for a in self.molecules:
			a.needParmchk = saveParmchk[a]

	def readTrajectory(self, filename=None):
		
		import MMTK
		from MMTK.Trajectory import Trajectory
		from chimera import Coord

		t = self.heatTraj
		t3 = self.prodTraj
		
		timestamp("Reading Trajectory File")

		parm = []
		parm.append([self.universe.energy(), self.universe.kineticEnergy(), self.universe.temperature()])

		if t:
			for en in t:
				parm.append([en["potential_energy"], en["kinetic_energy"], en["temperature"]])
		if t3:
			for en in t3:
				parm.append([en["potential_energy"], en["kinetic_energy"], en["temperature"]])
		m = self.mols[0]

		crd = Coord()
		if t:
			for i in range(len(t)):
				conf = t[i]["configuration"]
				cs = m.newCoordSet(m.activeCoordSet.id+1)
				for ma in self.universe.atomList():
					ca = ma.chimera_atom
					crd.x, crd.y, crd.z = conf[ma.index]*10
					ca.setCoord(crd, cs)
				m.activeCoordSet = cs
			t.close()

		if t3:
			for i in range(len(t3)):
				conf = t3[i]["configuration"]
				cs = m.newCoordSet(m.activeCoordSet.id+1)
				for ma in self.universe.atomList():
					ca = ma.chimera_atom
					crd.x, crd.y, crd.z = conf[ma.index]*10
					ca.setCoord(crd, cs)
				m.activeCoordSet = cs
			t3.close()

		self.ensemble = DynamicsTrajectory() 
		self.ensemble.name = "Dynamics Trajectory"
		self.ensemble.dynamicBonds = True
		keys = m.coordSets.keys()
		self.ensemble.startFrame = min(keys)+1
		self.ensemble.endFrame = max(keys)+1
		import chimera
		self.ensemble.molecule = m
		from mdMovie import mdMovieDialog
		self.movieDialog = mdMovieDialog(self.ensemble, biomet_parm=parm, externalEnsemble = True)	

	def runInBackground(self, dynVar, frame, filename, outside, generate, multi=None, heater = None, rot = True, trans = True):
		
		import MMTK
		import subprocess
		import os, os.path
		from chimera import SubprocessMonitor as SM
		import sys
	
		saveData,saveParmchk = self.saveData()
		self.deleteChimeraAtoms()
		if dynVar["thermostat"]:
			from MMTK.Environment import NoseThermostat
			from MMTK import Units
			self.universe.thermostat = NoseThermostat(float(dynVar["temperatureProd"])*Units.K, relaxation_time=0.2)
		MMTK.save(self.universe, "%s.mmtk" % filename)
		self.restoreChimeraAtoms(saveData,saveParmchk)
		self.writeScript(dynVar, frame, filename, multi=multi, heater = heater, rot = rot, trans = trans)

		def afterCB(aborted, s=self, f=filename):
			from tkMessageBox import askokcancel
			question = askokcancel("Molecular Dynamics Simulation","The simulation %s has finished. Do you want to view the results?" % filename)
			if question==1:
				s.readTrajectory(filename=filename)
			else:
				pass

		if generate:
			pass
		else:
			exe = os.path.join(os.environ["CHIMERA"], "bin", "chimera")
			p = SM.Popen([exe, "--nogui", str(filename) + ".py" ])
			SM.monitor("Running Dynamics Simulation", p, afterCB = afterCB)


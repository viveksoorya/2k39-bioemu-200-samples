# vim: set expandtab ts=4 sw=4:

def simpleNormalizeName(name):
    return name.strip()

class Unimplemented(ValueError):
    pass

ExtraSteps = 2        # number of extra steps to add to MMTK minimization
            # Execute two extra steps because
            # step 0 only calculates energy and not gradient
            # step 1 calculates gradient but positions are same as 0
            # step 2 is the first step where atoms move

def mmtkIdent(obj):
        import chimera
        if isinstance(obj, chimera.Atom):
            ident = obj.name.replace('.', '_')
            if ident[0].isdigit():
                ident = '_' + ident
            if len(obj.residue.atomsMap[obj.name]) > 1:
                # non-unique atom names
                ident += '_' + str(obj.residue.atomsMap[obj.name].index(obj))
            return ident
        ident = obj.oslIdent().replace('#', '_0_').replace(':', '_1_').replace(
            '.', '__')
        if isinstance(obj, chimera.Residue):
            # so that residue type can be deduced when read back in,
            # as well as the ordering of the residues...
            ident = obj.type + '_' + str(obj.molecule.residues.index(obj)) \
                + "_" + ident
        return ident

class MMTKinter:

    def __init__(self, mols, exclres=set(),
             nogui=False, addhyd=True, memorize=False, prep=True,
             ljOptions=None, esOptions=None, callback=None):
        # MMTK lengths are in nm while Chimera ones are in Angstroms
        # so we need a scale factor when converting
        if not mols:
            raise ValueError("No molecules specified")
        self.tempDir = None
        self.molId = 0
        self.ljOptions = ljOptions
        self.esOptions = esOptions
        self.callback = callback
        self.mols = mols
        self.exclres = exclres
        self._getParameters(mols, nogui, addhyd, memorize, prep)

    def _finishInit(self):
        timestamp("_finishInit")
        self.molecules = []
        self.atomMap = {}
        try:
            for m in self.mols:
                self.molecules.extend(self._makeMmtkMolecules(m))
            self._makeUniverse()
            if self.callback:
                self.callback(self)
                del self.callback
        finally:
            self._removeTempDir()

    def _makeUniverse(self):
        import os.path
        parmDir = os.path.dirname(__file__)
        timestamp("_makeUniverse")
        from MMTK import InfiniteUniverse
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
        modFiles = set([ str(m.frcmod) for m in self.molecules
                if m.frcmod is not None])
        from AmberInfo import amberHome
        paramDir = os.path.join(amberHome, "dat", "leap", "parm")
        parameters = readAmber99(os.path.join(paramDir, "gaff.dat"), modFiles)
        self._mergeAmber99(parameters)
        bondedScaleFactor = 1.0
        ff = MMForceField("Amber99/GAFF", parameters, self.ljOptions,
                    self.esOptions, bondedScaleFactor)
        AmberData._normalizeName = saveNormalizeName

        timestamp("Made forcefield")
        self.universe = InfiniteUniverse(ff)
        timestamp("Made universe")
        for mm in self.molecules:
            self.universe.addObject(mm)
            timestamp("Added model %s" % mm.name)
        timestamp("end _makeUniverse")

    def _getParameters(self, mols, nogui, addhyd, memorize, prep):
        if not prep:
            self.addedAtoms = []
            self._finishInit()
            return
        timestamp("_getParameters")
        import DockPrep
        import chimera
        self.originalAtoms = set([])
        for m in mols:
            self.originalAtoms.update(m.atoms)
        from AddCharge import defaultChargeModel
        kw = { "doneCB": self._finishDockPrep, "gaffType": True,
            "chargeModel": defaultChargeModel }
        if nogui or chimera.nogui:
            if not addhyd:
                kw["addHFunc"] = None
            DockPrep.prep(mols, nogui=nogui, **kw)
        else:
            d = DockPrep.memoryPrep("Minimize", memorize, mols,
                                    nogui=nogui, **kw)
            if d:
                d.addHydVar.set(addhyd)
                d.writeMol2Var.set(False)

    def _finishDockPrep(self):
        timestamp("end _getParameters")
        self.addedAtoms = sum([[a for a in m.atoms
                    if not a in self.originalAtoms]
                       for m in self.mols], [])
        # If atom was added to a selected atom, then we add it
        # into the current selection as well.
        from chimera import selection
        attached = attachedAtoms(self.addedAtoms,
                     selection.currentAtoms())
        if len(attached) > 0:
            selection.addCurrent(attached)
        del self.originalAtoms
        self._finishInit()

    def _mergeAmber99(self, parm):
        "Merge parameters appropriate to charge model into our parameters"
        from MMTK.ForceFields.Amber.AmberForceField import readAmber99
        chargeModels = set([getattr(m, 'chargeModel', None) for m in self.mols])
        if None in chargeModels:
            if len(chargeModels) == 1:
                from AddCharge import defaultChargeModel
                chargeModels = set([defaultChargeModel])
            else:
                chargeModels.remove(None)
        if len(chargeModels) > 1:
            from chimera import LimitationError
            raise LimitationError("Molecules have differing charge models (%s);"
                " don't know what parameter set to use." % ", ".join(list(chargeModels)))
        mainFile, modFiles = chargeModelToFiles(chargeModels.pop())
        from chimera import replyobj
        import os.path
        if modFiles:
            replyobj.info("Using main parameter file %s modified by %s\n"
                % (os.path.basename(mainFile), ", ".join([os.path.basename(mf)
                for mf in modFiles])))
        else:
            replyobj.info("Using main parameter file %s with no modifications\n"
                % os.path.basename(mainFile))
        parm99 = readAmber99(main_file=mainFile, mod_files=[open(mf, "r") for mf in modFiles])
        parm.atom_types.update(parm99.atom_types)
        parm.bonds.update(parm99.bonds)
        parm.bond_angles.update(parm99.bond_angles)
        parm.dihedrals.update(parm99.dihedrals)
        parm.dihedrals_2.update(parm99.dihedrals_2)
        parm.impropers.update(parm99.impropers)
        parm.impropers_1.update(parm99.impropers_1)
        parm.impropers_2.update(parm99.impropers_2)
        parm.hbonds.update(parm99.hbonds)
        parm.lj_equivalent.update(parm99.lj_equivalent)
        for name, ljpar_set99 in parm99.ljpar_sets.iteritems():
            try:
                ljpar_set = parm.ljpar_sets[name]
            except KeyError:
                parm.ljpar_sets[name] = ljpar_set99
            else:
                if ljpar_set.type != ljpar_set99.type:
                    print "incompatible ljpar_set"
                    print " GAFF type:", ljpar_set.type
                    print " AMBER99 type:", ljpar_set99.type
                ljpar_set.entries.update(ljpar_set99.entries)

    def _makeMmtkMolecules(self, m):
        timestamp("_makeMmtkMolecules %s" % m.name)
        mols = MMTKChimeraModel(m, self.molId, self.exclres,
            self).retrieveMolecules()
        self.molId += 1
        timestamp("end _makeMmtkMolecules")
        return mols

    def setFixed(self, atoms):
        for ma in self.universe.atomList():
            ma.fixed = False
        for a in atoms:
            if a in self.atomMap:
                ma = self.atomMap[a]
                ma.fixed = True
        # Fix added atoms that are connected to fixed atoms.
        for a in attachedAtoms(self.addedAtoms, atoms):
            if a in self.atomMap:
                ma = self.atomMap[a]
                ma.fixed = True

    def loadMMTKCoordinates(self):
        "Load MMTK coordinates from Chimera models"
        import chimera
        from Scientific.Geometry import Vector
        from MMTK import Units
        s = Units.Ang
        for ma in self.universe.atomList():
            try:
                ca = ma.getAtomProperty(ma, "chimera_atom")
            except AttributeError:
                pass
            else:
                c = ca.coord()
                p = Vector(c[0] * s, c[1] * s, c[2] * s)
                ma.setPosition(p)

    def saveMMTKCoordinates(self):
        "Save MMTK coordinates into Chimera models"
        import chimera
        from chimera import Coord
        from MMTK import Units
        s = Units.Ang
        sum = 0.0
        count = 0
        for ma in self.universe.atomList():
            if ma.fixed:
                continue
            ca = ma.getAtomProperty(ma, "chimera_atom")
            p = ma.position()
            c = Coord(p[0] / s, p[1] / s, p[2] / s)
            dsq = (c - ca.coord()).sqlength()
            ca.setCoord(c)
            #print "%.6f" % dsq
            sum += dsq
            count += 1
        import math
        if count > 0:
            print "Updated", count, "atoms.  RMSD: %.6f" \
                % math.sqrt(sum / count)
        else:
            print "No atoms updated."

    def minimize(self, nsteps, stepsize=0.02,
            cgsteps=0, cgstepsize=0.02,
            interval=None, action=None, **kw):
        timestamp("_minimize")
        if not interval:
            actions = []
        else:
            import sys
            from MMTK.Trajectory import LogOutput
            report = interval + ExtraSteps
            actions = [ LogOutput(sys.stdout, ["energy"],
                        report, None, report) ]
        from MMTK import Units
        if action is None or not interval:
            interval = None

        from MMTK.ForceFields.Amber import AmberData
        saveNormalizeName = AmberData._normalizeName
        AmberData._normalizeName = simpleNormalizeName

        from chimera import replyobj
        try:
            msg = "Initial energy: %f kJ/mol" % self.universe.energy()
        except KeyError, e:
            msg = ("Chimera/MMTK cannot minimize structure, "
                "probably because there is no parameter "
                "for '%s'" % e)
            replyobj.error(msg)
            return
        else:
            replyobj.info(msg)
        if nsteps:
            replyobj.status("starting %d steps of steepest descent" % nsteps)
            kw["step_size"] = stepsize * Units.Ang
            from MMTK.Minimization import SteepestDescentMinimizer
            minimizer = SteepestDescentMinimizer(self.universe,
                        actions=actions, **kw)
            self._doMinimize(minimizer, "steepest descent",
                        nsteps, interval, action)
        if cgsteps:
            replyobj.status("starting %d steps of conjugate gradient" % cgsteps)
            kw["step_size"] = cgstepsize * Units.Ang
            from MMTK.Minimization import ConjugateGradientMinimizer
            minimizer = ConjugateGradientMinimizer(self.universe,
                        actions=actions, **kw)
            self._doMinimize(minimizer, "conjugate gradient",
                        cgsteps, interval, action)

        AmberData._normalizeName = saveNormalizeName
        timestamp("end _minimize")

    def _doMinimize(self, minimizer, name, steps, interval, action):
        from chimera import replyobj
        remaining = steps
        while remaining > 0:
            timestamp(" minimize interval")
            if interval is None:
                realSteps = remaining
            else:
                realSteps = min(remaining, interval)
            minimizer(steps=realSteps + ExtraSteps)
            remaining -= realSteps
            if action is not None:
                action(self)
            timestamp(" finished %d steps" % realSteps)
            msg = "Finished %d of %d %s minimization steps" % (
                        steps - remaining, steps, name)
            replyobj.status(msg)
            replyobj.info(msg)
        replyobj.info("\n")

    def getTempDir(self):
        if self.tempDir:
            return self.tempDir
        from tempfile import mkdtemp
        self.tempDir = mkdtemp()
        #self.tempDir = "."
        return self.tempDir

    def _removeTempDir(self):
        if not self.tempDir:
            return
        if True:
            import os, os.path
            for filename in os.listdir(self.tempDir):
                os.remove(os.path.join(self.tempDir, filename))
            os.rmdir(self.tempDir)
        else:
            print "Did not clean up temp dir", self.tempDir
        self.tempDir = None

def attachedAtoms(atoms, baseAtoms):
    bset = set(baseAtoms)
    attached = []
    for a in atoms:
        for b in a.bonds:
            oa = b.otherAtom(a)
            if oa in bset:
                attached.append(a)
                break
    return attached

from MMTK.MoleculeFactory import MoleculeFactory, AtomTemplate, GroupTemplate

class ChimeraGroupTemplate(GroupTemplate):
    """GroupTemplate that handles containing actual Groups/Atoms"""

    def __init__(self, *args, **kw):
        GroupTemplate.__init__(self, *args, **kw)

    def atomNameToPath(self, atom_name):
        atom_name = atom_name.split('.')
        object = self
        from MMTK.ChemicalObjects import Group, Atom
        try:
            for path_element in atom_name:
                if isinstance(object, Group):
                    for subobj in object.atomList():
                        if subobj.name == path_element or subobj.chimera_atom.name == path_element:
                            object = subobj
                            if isinstance(object, Atom):
                                return object
                            break
                    else:
                        break
                else:
                    object = object.children[object.names[path_element]]
            if not isinstance(object, (Atom, AtomTemplate)):
                raise ValueError("no atom " + '.'.join(atom_name))
        except KeyError:
            raise ValueError("no atom " + '.'.join(atom_name))
        return atom_name

class ChimeraMoleculeFactory(MoleculeFactory):
    """MoleculeFactory that supports containing actual Groups/Atoms"""

    def createGroup(self, name):
        """
        Create a new (initially empty) group object.
        """
        if self.groups.has_key(name):
            raise ValueError("redefinition of group " + name)
        self.groups[name] = ChimeraGroupTemplate(name)

    def makeChemicalObjects(self, template, top_level):
        from MMTK import Bonds, ChemicalObjects
        self.groups[template.name].locked = True
        if top_level:
            if template.attributes.has_key('sequence'):
                object = ChemicalObjects.ChainMolecule(None)
            else:
                object = ChemicalObjects.Molecule(None)
        else:
            object = ChemicalObjects.Group(None)
        object.atoms = []
        object.bonds = Bonds.BondList([])
        object.groups = []
        object.type = self.groups[template.name]
        object.parent = None
        child_objects = []
        for child in template.children:
            if isinstance(child, GroupTemplate):
                group = self.makeChemicalObjects(child, False)
                object.groups.append(group)
                object.atoms.extend(group.atoms)
                object.bonds.extend(group.bonds)
                group.parent = object
                child_objects.append(group)
            elif not isinstance(child, AtomTemplate):
                # actual Molecule or Group, returned by
                # _findStandardResidue
                object.groups.append(child)
                object.atoms.extend(child.atoms)
                object.bonds.extend(child.bonds)
                child.parent = object
                child_objects.append(child)
            else:
                try:
                    atom = ChemicalObjects.Atom(child.element)
                except IOError:
                    from chimera import LimitationError
                    raise LimitationError("Atom type \"%s\" "
                        "is not supported by MMTK" % child.element)
                object.atoms.append(atom)
                atom.parent = object
                child_objects.append(atom)
                a = self.atomMap[child]
                del self.atomMap[child]
                self.atomMap[a] = atom
        for name, index in template.names.items():
            setattr(object, name, child_objects[index])
            child_objects[index].name = name
        for name, value in template.attributes.items():
            path = name.split('.')
            setattr(self.namePath(object, path[:-1]), path[-1], value)
        for atom1, atom2 in template.bonds:
            if not isinstance(atom1, ChemicalObjects.Atom):
                atom1 = self.namePath(object, atom1)
            if not isinstance(atom2, ChemicalObjects.Atom):
                atom2 = self.namePath(object, atom2)
            object.bonds.append(Bonds.Bond((atom1, atom2)))
        for name, vector in template.positions.items():
            path = name.split('.')
            self.namePath(object, path).setPosition(vector)
        return object

class MMTKChimeraModel(object):

    def __init__(self, m, ident, exclres, owner):
        from MMTK import Bonds
        self.chimeraMolecule = m
        molResGroups = connectedResidues(m, exclres)
        self.atomMap = owner.atomMap

        self.mf = ChimeraMoleculeFactory()
        self.mf.atomMap = self.atomMap
        rtype2frcmod = {}
        self.frcmods = frcmods = []
        res2grp = {}
        for i, mrg in enumerate(molResGroups):
            self.mf.createGroup(str(i))
            molGroup = self.mf.groups[str(i)]
            needParmchk = {}
            # sort each residue group, so that
            # universes match when appending
            # to a trajectory...
            for r in sorted([sr for sr in mrg]):
                res2grp[r] = molGroup
                v = self._findStandardResidue(r)
                if v is None:
                    self._makeNonStandardResidue(str(i), r)
                    needParmchk[r.type] = r
                else:
                    self._makeStandardResidue(molGroup, r, *v)
            if needParmchk:
                frcmod = None
                # are all needed residue types already in some
                # frcmod file we've computed?
                for rtype in needParmchk.keys():
                    if rtype in rtype2frcmod:
                        if frcmod is None:
                            frcmod = rtype2frcmod[rtype]
                        elif frcmod != rtype2frcmod[rtype]:
                            frcmod = None
                            break
                    else:
                        break
                if frcmod is None:
                    frcmod = self._runParmchk("%s-%d" % (ident, i),
                        owner.getTempDir(), needParmchk)
                    for rtype in needParmchk.keys():
                        rtype2frcmod[rtype] = frcmod
                frcmods.append(frcmod)
            else:
                frcmods.append(None)

        from chimera import Bond
        for b in m.bonds:
            if b.display == Bond.Never:
                continue
            a0, a1 = b.atoms
            if a0.residue is a1.residue:
                continue
            if a0.residue in exclres or a1.residue in exclres:
                continue
            res2grp[a0.residue].addBond(
                mmtkIdent(a0.residue) + "." + mmtkIdent(a0),
                mmtkIdent(a1.residue) + "." + mmtkIdent(a1))

    def retrieveMolecules(self):
        mols = []
        for i, frcmod in enumerate(self.frcmods):
            mol = self.mf.retrieveMolecule(str(i))
            mol.type.frcmod = frcmod
            mols.append(mol)
        return mols

    def _findStandardResidue(self, r):
        try:
            amberName = r.amberName
        except AttributeError:
            pass
        else:
            from AddCharge import unitedAtomChargeModels
            if r.molecule.chargeModel in unitedAtomChargeModels:
                resMaps = [ UnitedAtomResidueNameMap,
                        ResidueNameMap ]
            else:
                resMaps = [ ResidueNameMap ]
            for rm in resMaps:
                try:
                    blueprint = rm[amberName]
                except KeyError:
                    pass
                else:
                    from MMTK.ChemicalObjects import Group
                    return Group(blueprint), amberName
        try:
            blueprint = MoleculeNameMap[r.type]
        except KeyError:
            return None
        else:
            from MMTK.ChemicalObjects import Molecule
            return Molecule(blueprint), r.type

    def _makeStandardResidue(self, molGroup, r, mg, blueprint):
        chimera2mmtk = self._mapStandardAtoms(r, mg)
        if (len(chimera2mmtk) == len(mg.atomList())
        and len(chimera2mmtk) == len(r.atoms)):
            self._addStandardResidue(molGroup, mg, chimera2mmtk)
            return

        # Some atoms were not used.
        # If residue is a histidine, try other protonation forms.
        resType = blueprint[-3:]
        hisList = [ "HIE", "HID", "HIP", "HIS" ]
        if resType in hisList:
            prefix = blueprint[:-3]
            from MMTK.ChemicalObjects import Group
            from chimera import LimitationError
            for hisType in hisList:
                if hisType == resType:
                    continue
                newType = prefix + hisType
                mg = Group(ResidueNameMap[newType])
                try:
                    chimera2mmtk = self._mapStandardAtoms(r, mg)
                except LimitationError:
                    # Must have hit a Chimera atom with
                    # no corresponding MMTK atom when
                    # using the wrong blueprint
                    continue
                if (len(chimera2mmtk) == len(mg.atomList())
                and len(chimera2mmtk) == len(r.atoms)):
                    break
            from chimera import replyobj
            replyobj.warning("histidine %s reclassified "
                        "from AMBER type %s to %s\n" %
                        (r.oslIdent(), blueprint,
                        newType))
            self._addStandardResidue(molGroup, mg, chimera2mmtk)
            return

        # There is an irreconcilable atom mismatch.
        allMMTKAtoms = set(mg.atomList())
        allChimeraAtoms = set(r.atoms)
        usedMMTKAtoms = set(chimera2mmtk.itervalues())
        usedChimeraAtoms = set(chimera2mmtk.iterkeys())
        extra = [ a.name
            for a in allChimeraAtoms - usedChimeraAtoms ]
        if extra:
            extraAtoms = " has extra " + makeAtomList(extra)
        else:
            extraAtoms = None
        missing = [ ma.name
            for ma in allMMTKAtoms - usedMMTKAtoms ]
        if missing:
            missingAtoms = " is missing " + makeAtomList(missing)
        else:
            missingAtoms = None
        if extra and missing:
            msg = extraAtoms + " and" + missingAtoms
        elif extra:
            msg = extraAtoms
        else:
            msg = missingAtoms
        from chimera import LimitationError
        raise LimitationError("Residue %s (%s/%s) %s"
                    % (r.oslIdent(), r.type, mg.name, msg))

    def _mapStandardAtoms(self, r, mg):
        pdbmap = {}
        altmap = {}
        self._getMaps(mg, pdbmap, altmap)
        try:
            subgroups = mg.groups
        except AttributeError:
            pass
        else:
            for subg in mg.groups:
                self._getMaps(subg, pdbmap, altmap)
        used = {}
        chimera2mmtk = {}
        for a in r.atoms:
            aname = self.getMMTKname(a.name, r.type, pdbmap, altmap)
            ma = mg.getAtom(aname)
            if ma in used:
                from chimera import LimitationError
                raise LimitationError("Residue %s (%s/%s) should have either atom %s "
                            "or %s, but not both" % (r.oslIdent(),
                            r.type, mg.name, used[ma], a.name))
            chimera2mmtk[a] = ma
            used[ma] = a.name
        return chimera2mmtk

    def getMMTKname(self, aname, rtype, pdbmap, altmap):
        # If the name does not start with an alphabetic
        # character, try rotating it until it does.  This works
        # for hydrogens in amino acids.
        letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        n = aname
        while n[0] not in letters:
            n = n[1:] + n[0]
        n = altmap.get(n, n)
        if pdbmap.has_key(n):
            return pdbmap[n]
        # Nope.  If the name contains a ', try replacing it with
        # a *.  This works for hydrogens in nucleotides.
        n = aname.replace("'", '*')
        n = altmap.get(n, n)
        if pdbmap.has_key(n):
            return pdbmap[n]
        #print pdbmap.keys()
        #print altmap.keys()
        from chimera import LimitationError
        raise LimitationError("No MMTK name for atom \"%s\" "
                    "in standard residue \"%s\""
                    % (aname, rtype))

    def _getMaps(self, obj, pdbmap, altmap):
        try:
            pm = obj.pdbmap
        except AttributeError:
            pass
        else:
            for item in pm:
                for name, ref in item[1].iteritems():
                    atom = obj.getAtom(ref)
                    pdbmap[name] = atom
        try:
            am = obj.pdb_alternative
        except AttributeError:
            pass
        else:
            altmap.update(am)

    def _addStandardResidue(self, molGroup, mg, chimera2mmtk):
        for a, ma in chimera2mmtk.iteritems():
            properties = {
                "amber_charge": a.charge,
                "amber_atom_type": a.gaffType,
                "chimera_atom": a,
            }
            ma.addProperties(properties)
            self.atomMap[a] = ma
        molGroup.addSubgroup(mmtkIdent(a.residue), mg)

    def _makeNonStandardResidue(self, molGroupName, r):
        #print "makeNonstandardResidue", r.oslIdent(), r.type
        import chimera
        atoms = []
        c2m = {}
        residueBonds = set([])
        rIdent = mmtkIdent(r)
        self.mf.createGroup(rIdent)
        rg = self.mf.groups[rIdent]
        self.mf.addSubgroup(molGroupName, rIdent, rIdent)
        for a in r.atoms:
            aIdent = mmtkIdent(a)
            rg.addAtom(aIdent, a.element.name)
            ma = rg.children[-1]
            try:
                charge = a.charge
            except AttributeError:
                from chimera import LimitationError
                raise LimitationError("Unable to find "
                    "partial charge for %s" % a.oslIdent())
            try:
                gaffType = a.gaffType
            except AttributeError:
                from chimera import LimitationError
                raise LimitationError("Element %s (atom %s)"
                " is not currently supported [no GAFF type]"
                    % (a.element.name, a.oslIdent()))
            for attrName, val in [ ("amber_charge", charge),
                    ("amber_atom_type", gaffType), ("chimera_atom", a)]:
                rg.setAttribute(aIdent + "." + attrName, val)
            c2m[a] = ma
            for b in a.bonds:
                if b.display == chimera.Bond.Never:
                    continue
                other = b.otherAtom(a)
                if other.residue == r:
                    residueBonds.add(b)
            # yes, map is reversed for templates,
            # corrected when actual objects are made
            self.atomMap[ma] = a
        for b in residueBonds:
            a0, a1 = b.atoms
            rg.addBond(mmtkIdent(a0), mmtkIdent(a1))
        if len(r.atoms) == 1:
            atom = r.atoms[0]
            if len(atom.neighbors) == 0:
                gaffType = atom.gaffType
                if gaffType.upper() == gaffType or not gaffType.isalnum():
                    # don't parmchk known ions
                    return

    def _runParmchk(self, uniquifier, tempDir, needParmchk):
        import os, os.path, sys
        from subprocess import Popen, STDOUT, PIPE
        from chimera import replyobj
        parmDir = os.path.dirname(__file__)
        if not parmDir:
            parmDir = os.getcwd()
        parmchkIn = os.path.join(tempDir, "parmchk.in.%s" % uniquifier)
        self._writeParmchk(parmchkIn, needParmchk)

        frcmod = os.path.join(tempDir, "frcmod.%s" % uniquifier)
        chimeraRoot = os.environ["CHIMERA"]
        from AmberInfo import amberBin, amberHome
        command = [
            os.path.join(amberBin, "parmchk2"),
            "-i", parmchkIn,
            "-f", "mol2",
            "-o", frcmod,
            "-p", os.path.join(amberHome, "dat", "leap", "parm", "gaff.dat")
        ]
        replyobj.status("Running PARMCHK for %s" %
                self.chimeraMolecule.name, log=True)
        replyobj.info("command: %s\n" % " ".join(command))
        p = Popen(command, stdin=PIPE, stdout=PIPE, stderr=STDOUT,
                cwd=tempDir, shell=False,
                env={"AMBERHOME": amberHome},
                bufsize=1).stdout
        while True:
            line = p.readline()
            if not line:
                break
            replyobj.info("(parmchk) %s\n" % line.rstrip())
        if not os.path.exists(frcmod):
            from chimera import LimitationError
            raise LimitationError("Unable to compute partial "
                    "charges: PARMCHK failed.\n"
                    "Check reply log for details.\n")
            return None
        replyobj.status("Finished PARMCHK for %s" %
                self.chimeraMolecule.name, log=True)
        return frcmod

    def _writeParmchk(self, filename, needParmchk):
        # generate Mol2 input file for parmchk
        import WriteMol2
        from chimera.selection import ItemizedSelection
        from chimera import Bond
        rSet = set(needParmchk.values())
        npSet = set(needParmchk.values())
        for b in self.chimeraMolecule.bonds:
            if b.display == Bond.Never:
                continue
            a0, a1 = b.atoms
            r0 = a0.residue
            r1 = a1.residue
            if (r0 in npSet and r1 not in npSet):
                rSet.add(r1)
            elif (r0 not in npSet and r1 in npSet):
                rSet.add(r0)
        sel = ItemizedSelection()
        sel.add(rSet)
        WriteMol2.writeMol2(sel, filename, gaffType=True, temporary=True)

class MMTKChimeraGroupType:
    # This class is needed to supply the necessary attributes
    # so that MMTK description() method will complete successfully.
    def __init__(self):
        self.name = "ChimeraGroup"
        self.groups = []
ChimeraGroupType = MMTKChimeraGroupType()

from MMTK import Biopolymers
class MMTKChimeraGroup(Biopolymers.Residue):

    def __init__(self, r, atomMap):
        import chimera
        from MMTK.ChemicalObjects import Atom
        from MMTK.Bonds import Bond
        self.type = ChimeraGroupType    # see class above
        self.parent = None
        self.name = r.oslIdent()
        atoms = []
        c2m = {}
        residueBonds = set([])
        for a in r.atoms:
            try:
                ma = Atom(a.element.name)
            except IOError:
                from chimera import LimitationError
                raise LimitationError("Atom type \"%s\" "
                    "is not supported by MMTK" %
                    a.element.name)
            ma.parent = self
            try:
                charge = a.charge
            except AttributeError:
                from chimera import LimitationError
                raise LimitationError("Unable to find "
                    "partial charge for %s" % a.oslIdent())
            try:
                gaffType = a.gaffType
            except AttributeError:
                from chimera import LimitationError
                raise LimitationError("Element %s (atom "
                    "%s) is not currently supported"
                    % (a.element.name, a.oslIdent()))
            properties = {
                "amber_charge": charge,
                "amber_atom_type": gaffType,
                "chimera_atom": a,
            }
            ma.addProperties(properties)
            atoms.append(ma)
            c2m[a] = ma
            for b in a.bonds:
                if b.display == chimera.Bond.Never:
                    continue
                other = b.otherAtom(a)
                if other.residue == r:
                    residueBonds.add(b)
            atomMap[a] = ma
        bonds = []
        for b in residueBonds:
            a0, a1 = b.atoms
            ma0 = c2m[a0]
            ma1 = c2m[a1]
            mb = Bond((ma0, ma1))
            mb.parent = self
            bonds.append(mb)
        self.atoms = atoms
        self.bonds = bonds

def _dumpChain(obj):
    while obj is not None:
        print "object", obj
        _dumpDataAttributes(obj)
        obj = getattr(obj, "parent", None)

def _dumpDataAttributes(mg):
    for attr in dir(mg):
        if attr.startswith("__"):
            continue
        val = getattr(mg, attr)
        if callable(val):
            continue
        print " ", attr, val

def connectedResidues(mol, excludedResidues):
    connectedSets = []
    seenResidues = set()
    for res in mol.residues:
        if res in seenResidues or res in excludedResidues:
            continue
        roots = set([res.molecule.rootForAtom(a, True) for a in res.atoms])
        connected = set([a.residue
            for rt in roots for a in mol.traverseAtoms(rt)])
        connectedSets.append(connected)
        seenResidues.update(connected)
    return connectedSets

def makeAtomList(names):
    # Assume names is not empty
    if len(names) == 1:
        return "atom %s" % names[0]
    else:
        return "atoms %s and %s" % (", ".join(names[:-1]), names[-1])

def chargeModelToFiles(chargeModel):
    expectedPrefix = "AMBER ff"
    from chimera import LimitationError
    if not chargeModel.startswith(expectedPrefix):
        raise LimitationError("Don't know how to find parameter files for charge model '%s'"
                % chargeModel)
    ffName = chargeModel[len(expectedPrefix):]
    if not ffName[:2].isdigit():
        raise LimitationError("Charge model name not of the expected form (starting with"
                " %s[year])" % expectedPrefix)

    from AmberInfo import amberHome
    import os.path
    paramDir = os.path.join(amberHome, "dat", "leap", "parm")
    year = int(ffName[:2])
    mainFile = os.path.join(paramDir, "parm" + ffName + ".dat")
    tries = 0
    while not os.path.exists(mainFile):
        mainFile = os.path.join(paramDir, "parm%02d.dat" % year)
        year -= 1
        if year < 0:
            year += 100
        tries += 1
        if tries > 100:
            raise AssertionError("No parm files in %s?!?" % paramDir)

    modFiles = [os.path.join(paramDir, "heme-iron.frcmod")]
    baseFF = os.path.join(paramDir, "frcmod.ff" + ffName[:2])
    if os.path.exists(baseFF):
        baseSuffixes = ["ff" + ffName[:2]]
    else:
        baseSuffixes = []
    for suffix in baseSuffixes + ["ff"+ffName, "parm"+ffName[2:], "ionsjc_tip3p"]:
        modFile = os.path.join(paramDir, "frcmod." + suffix)
        if os.path.exists(modFile):
            modFiles.append(modFile)
    return mainFile, modFiles

def timestamp(s):
    pass
    #import time
    #print "%s: %s" % (time.ctime(time.time()), s)

ResidueNameMap = {
    "ACE":    "ace_beginning_nt",
    "NME":    "methyl",

    "ALA":    "alanine",
    "ARG":    "arginine",
    "ASP":    "aspartic_acid",
    "ASN":    "asparagine",
    "CYS":    "cysteine",
    "CYX":    "cystine_ss",
    "GLU":    "glutamic_acid",
    "GLN":    "glutamine",
    "GLY":    "glycine",
    "HIS":    "histidine",
    "HID":    "histidine_deltah",
    "HIE":    "histidine_epsilonh",
    "HIP":    "histidine_plus",
    "ILE":    "isoleucine",
    "LEU":    "leucine",
    "LYS":    "lysine",
    "MET":    "methionine",
    "PHE":    "phenylalanine",
    "PRO":    "proline",
    "SER":    "serine",
    "NA":    "sodium",
    "THR":    "threonine",
    "TRP":    "tryptophan",
    "TYR":    "tyrosine",
    "VAL":    "valine",
    "CALA":    "alanine_ct",
    "CARG":    "arginine_ct",
    "CASP":    "aspartic_acid_ct",
    "CASN":    "asparagine_ct",
    "CCYS":    "cysteine_ct",
    "CCYX":    "cystine_ss_ct",
    "CGLU":    "glutamic_acid_ct",
    "CGLN":    "glutamine_ct",
    "CGLY":    "glycine_ct",
    "CHIS":    "histidine_ct",
    "CHID":    "histidine_deltah_ct",
    "CHIE":    "histidine_epsilonh_ct",
    "CHIP":    "histidine_plus_ct",
    "CILE":    "isoleucine_ct",
    "CLEU":    "leucine_ct",
    "CLYS":    "lysine_ct",
    "CMET":    "methionine_ct",
    "CPHE":    "phenylalanine_ct",
    "CPRO":    "proline_ct",
    "CSER":    "serine_ct",
    "CNA":    "sodium_ct",
    "CTHR":    "threonine_ct",
    "CTRP":    "tryptophan_ct",
    "CTYR":    "tyrosine_ct",
    "CVAL":    "valine_ct",
    "NALA":    "alanine_nt",
    "NARG":    "arginine_nt",
    "NASP":    "aspartic_acid_nt",
    "NASN":    "asparagine_nt",
    "NCYS":    "cysteine_nt",
    "NCYX":    "cystine_ss_nt",
    "NGLU":    "glutamic_acid_nt",
    "NGLN":    "glutamine_nt",
    "NGLY":    "glycine_nt",
    "NHIS":    "histidine_nt",
    "NHID":    "histidine_deltah_nt",
    "NHIE":    "histidine_epsilonh_nt",
    "NHIP":    "histidine_plus_nt",
    "NILE":    "isoleucine_nt",
    "NLEU":    "leucine_nt",
    "NLYS":    "lysine_nt",
    "NMET":    "methionine_nt",
    "NPHE":    "phenylalanine_nt",
    "NPRO":    "proline_nt",
    "NSER":    "serine_nt",
    "NNA":    "sodium_nt",
    "NTHR":    "threonine_nt",
    "NTRP":    "tryptophan_nt",
    "NTYR":    "tyrosine_nt",
    "NVAL":    "valine_nt",

    "A":    "adenine",
    "C":    "cytosine",
    "G":    "guanine",
    "T":    "thymine",
    "U":    "uracil",
    "DA":    "d-adenosine",
    "DC":    "d-cytosine",
    "DG":    "d-guanosine",
    "DT":    "d-thymine",
    "RA":    "r-adenosine",
    "RC":    "r-cytosine",
    "RG":    "r-guanosine",
    "RU":    "r-uracil",
    "DA3":    "d-adenosine_3ter",
    "DC3":    "d-cytosine_3ter",
    "DG3":    "d-guanosine_3ter",
    "DT3":    "d-thymine_3ter",
    "RA3":    "r-adenosine_3ter",
    "RC3":    "r-cytosine_3ter",
    "RG3":    "r-guanosine_3ter",
    "RU3":    "r-uracil_3ter",
    "DA5":    "d-adenosine_5ter",
    "DC5":    "d-cytosine_5ter",
    "DG5":    "d-guanosine_5ter",
    "DT5":    "d-thymine_5ter",
    "RA5":    "r-adenosine_5ter",
    "RC5":    "r-cytosine_5ter",
    "RG5":    "r-guanosine_5ter",
    "RU5":    "r-uracil_5ter",
    "DAN":    "d-adenosine_5ter_3ter",
    "DCN":    "d-cytosine_5ter_3ter",
    "DGN":    "d-guanosine_5ter_3ter",
    "DTN":    "d-thymine_5ter_3ter",
    "RAN":    "r-adenosine_5ter_3ter",
    "RCN":    "r-cytosine_5ter_3ter",
    "RGN":    "r-guanosine_5ter_3ter",
    "RUN":    "r-uracil_5ter_3ter",
}

UnitedAtomResidueNameMap = {
    "ALA":    "alanine_uni",
    "ARG":    "arginine_uni",
    "ASP":    "aspartic_acid_uni",
    "ASN":    "asparagine_uni",
    "CYS":    "cysteine_uni",
    "CYX":    "cystine_ss_uni",
    "GLU":    "glutamic_acid_uni",
    "GLN":    "glutamine_uni",
    "GLY":    "glycine_uni",
    "HIS":    "histidine_uni",
    "HID":    "histidine_deltah_uni",
    "HIE":    "histidine_epsilonh_uni",
    "HIP":    "histidine_plus_uni",
    "ILE":    "isoleucine_uni",
    "LEU":    "leucine_uni",
    "LYS":    "lysine_uni",
    "MET":    "methionine_uni",
    "PHE":    "phenylalanine_uni",
    "PRO":    "proline_uni",
    "SER":    "serine_uni",
    "NA":    "sodium_uni",
    "THR":    "threonine_uni",
    "TRP":    "tryptophan_uni",
    "TYR":    "tyrosine_uni",
    "VAL":    "valine_uni",
    "CALA":    "alanine_ct_uni",
    "CARG":    "arginine_ct_uni",
    "CASP":    "aspartic_acid_ct_uni",
    "CASN":    "asparagine_ct_uni",
    "CCYS":    "cysteine_ct_uni",
    "CCYX":    "cystine_ss_ct_uni",
    "CGLU":    "glutamic_acid_ct_uni",
    "CGLN":    "glutamine_ct_uni",
    "CGLY":    "glycine_ct_uni",
    "CHIS":    "histidine_ct_uni",
    "CHID":    "histidine_deltah_ct_uni",
    "CHIE":    "histidine_epsilonh_ct_uni",
    "CHIP":    "histidine_plus_ct_uni",
    "CILE":    "isoleucine_ct_uni",
    "CLEU":    "leucine_ct_uni",
    "CLYS":    "lysine_ct_uni",
    "CMET":    "methionine_ct_uni",
    "CPHE":    "phenylalanine_ct_uni",
    "CPRO":    "proline_ct_uni",
    "CSER":    "serine_ct_uni",
    "CNA":    "sodium_ct_uni",
    "CTHR":    "threonine_ct_uni",
    "CTRP":    "tryptophan_ct_uni",
    "CTYR":    "tyrosine_ct_uni",
    "CVAL":    "valine_ct_uni",
    "NALA":    "alanine_nt_uni",
    "NARG":    "arginine_nt_uni",
    "NASP":    "aspartic_acid_nt_uni",
    "NASN":    "asparagine_nt_uni",
    "NCYS":    "cysteine_nt_uni",
    "NCYX":    "cystine_ss_nt_uni",
    "NGLU":    "glutamic_acid_nt_uni",
    "NGLN":    "glutamine_nt_uni",
    "NGLY":    "glycine_nt_uni",
    "NHIS":    "histidine_nt_uni",
    "NHID":    "histidine_deltah_nt_uni",
    "NHIE":    "histidine_epsilonh_nt_uni",
    "NHIP":    "histidine_plus_nt_uni",
    "NILE":    "isoleucine_nt_uni",
    "NLEU":    "leucine_nt_uni",
    "NLYS":    "lysine_nt_uni",
    "NMET":    "methionine_nt_uni",
    "NPHE":    "phenylalanine_nt_uni",
    "NPRO":    "proline_nt_uni",
    "NSER":    "serine_nt_uni",
    "NNA":    "sodium_nt_uni",
    "NTHR":    "threonine_nt_uni",
    "NTRP":    "tryptophan_nt_uni",
    "NTYR":    "tyrosine_nt_uni",
    "NVAL":    "valine_nt_uni",
}

MoleculeNameMap = {
    "HOH":    "water",
    "WAT":    "water",
}

if __name__ == "__main__" or __name__ == "chimeraOpenSandbox":
    def minimize(mi):
        def update(mi):
            import chimera
            mi.saveMMTKCoordinates()
            chimera.runCommand("wait")
        mi.loadMMTKCoordinates()
        mi.minimize(nsteps=100, interval=10, action=update)

    def test():
        import chimera
        # Standard residues only
        #mList = chimera.openModels.open("testdata/small2.pdb")
        #mList = chimera.openModels.open("testdata/1gcn.pdb")
        # Non-standard residues only
        #mList = chimera.openModels.open("testdata/gdp.pdb")
        # Both standard and non-standard residues
        mList = chimera.openModels.open("testdata/3fx2.pdb")
        mi = MMTKinter(mList, callback=minimize)

    test()

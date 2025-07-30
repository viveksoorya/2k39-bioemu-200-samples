"""Add missing residues, atoms, and hydrogens to PDB files."""

import argparse
import os
def validate_input(path):
    if not os.path.exists(path):
        raise argparse.ArgumentTypeError(f"{path} does not exist.")
    if not (os.path.isfile(path) or os.path.isdir(path)):
        raise argparse.ArgumentTypeError(f"{path} is neither a file nor a directory.")
    return path

def wrapper_to_add_flags():

    from pdbfixer import PDBFixer
    from openmm.app import PDBFile
    from pathlib import Path

    def add_missing_atoms(input_file, output_file):
        # load the PDB file
        fixer = PDBFixer(filename=str(input_file))

        # add missing residues, atoms, and hydrogens
        #fixer.findMissingResidues()
        #fixer.findMissingAtoms()
        #fixer.addMissingAtoms()
        fixer.addMissingHydrogens(7.0)
        
        # write the fixed PDB file
        PDBFile.writeFile(fixer.topology, fixer.positions, open(output_file, 'w')) 

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-f', required=True, help="Input PDB file path, or folder path containing only pdb files to be fixed.")
    parser.add_argument('-o', required=False, help="Output folder for the fixed PDB file if input is a folder, otherwise, output file path.")
    args = parser.parse_args()

    if os.path.isdir(args.f) and not args.o:
        folder = Path(args.f)
        output_path = folder.parent / f"{folder.name}-now-1200-odd-atoms"
        output_path.mkdir(parents=True, exist_ok=True)
        for file in folder.glob('*.pdb'):
            add_missing_atoms(file, output_file=output_path / f"{file.stem}-now-1200-odd-atoms.pdb")

    elif os.path.isdir(args.f) and args.o:
        folder = Path(args.f)
        output_path = Path(args.o)
        output_path.mkdir(parents=True, exist_ok=True)
        for file in folder.glob('*.pdb'):
            add_missing_atoms(file, output_file=output_path / f"{file.stem}-now-1200-odd-atoms.pdb")

    elif os.path.isfile(args.f) and not args.o:
        file = args.f
        if not os.path.splitext(file)[1] == '.pdb':
            raise ValueError("Input file must be a PDB file with .pdb extension")
        add_missing_atoms(file, output_file=Path(os.path.dirname(file), f"{os.path.splitext(os.path.basename(file))[0]}-now-1200-odd-atoms.pdb"))

    elif os.path.isfile(args.f) and args.o:
        file = args.f
        if not os.path.splitext(file)[1] == '.pdb':
            raise ValueError("Input file must be a PDB file with .pdb extension")
        add_missing_atoms(file, output_file=args.o)
    else:
        raise ValueError("Input must be a PDB file or a folder containing PDB files.")
    print("Missing residues, atoms, and hydrogens added successfully.")


if __name__ == "__main__":
    wrapper_to_add_flags()
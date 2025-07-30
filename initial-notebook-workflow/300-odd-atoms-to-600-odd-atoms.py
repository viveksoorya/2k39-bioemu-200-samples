"""
    This script is designed to convert a PDB file with 300 odd atoms to a PDB file with 600 odd atoms by reconstructing sidechains.
    It uses the HPacker library to perform the reconstruction and writes the output to a specified PDB file.
    The script takes two command-line arguments: the input PDB file and the output PDB file.
    Usage:
    python 300-odd-atoms-to-600-odd-atoms.py -f input.pdb -o output.pdb
"""

import argparse
import os

def wrapper_to_add_flags():
    """
    This script is designed to convert a PDB file with 300 odd atoms to a PDB file with 600 odd atoms by reconstructing sidechains.
    It uses the HPacker library to perform the reconstruction and writes the output to a specified PDB file.
    The script takes two command-line arguments: the input PDB file and the output PDB file.
    Usage:
    python 300-odd-atoms-to-600-odd-atoms.py -f input.pdb -o output.pdb
    """

    def run_hpacker(input_file, output_file):
        from hpacker import HPacker
        hpacker = HPacker(input_file)  # backbone-only input
        hpacker.reconstruct_sidechains(num_refinement_iterations=5)
        hpacker.write_pdb(output_file)  # output PDB with reconstructed sidechains

        
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-f', required=True, help='Input PDB file with 300 odd atoms')
    parser.add_argument('-o', required=False, help='Output PDB file with 600 odd atoms')

    args = parser.parse_args()    

    if os.path.isdir(args.f) and not args.o:
        for file in os.listdir(args.f):
            if file.endswith('.pdb'):
                input_file = os.path.join(args.f, file)
                output_file = os.path.join(os.path.dirname(input_file), f"{os.path.splitext(file)[0]}-600-odd-atoms.pdb")
                run_hpacker(input_file, output_file)
    elif os.path.isdir(args.f) and args.o:
        if not os.path.exists(args.o):
            os.makedirs(args.o)
        for file in os.listdir(args.f):
            if file.endswith('.pdb'):
                input_file = os.path.join(args.f, file)
                output_file = os.path.join(args.o, f"{os.path.splitext(file)[0]}-600-odd-atoms.pdb")
                run_hpacker(input_file, output_file)
    elif os.path.isfile(args.f) and not args.o:
        output_file = os.path.join(os.path.dirname(args.f), f"{os.path.splitext(os.path.basename(args.f))[0]}-600-odd-atoms.pdb")
        run_hpacker(args.f, output_file)
    elif os.path.isfile(args.f) and args.o:
        run_hpacker(args.f, args.o)
    else:
        raise ValueError("Input must be a PDB file or a directory containing PDB files.")

    

if __name__ == "__main__":
    wrapper_to_add_flags()
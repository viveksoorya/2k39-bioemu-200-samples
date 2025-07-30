"""
Prompt: Vivek Soorya Maadoori
Author: Github Copilor
Verified by: Vivek Soorya Maadoori

"""

import sys
import MDAnalysis as mda

def dcd_to_pdb(topology_file, dcd_file, output_prefix):
    u = mda.Universe(topology_file, dcd_file)
    for i, ts in enumerate(u.trajectory):
        outname = f"{output_prefix}_{i:04d}.pdb"
        with mda.Writer(outname, u.atoms.n_atoms) as W:
            W.write(u.atoms)
        print(f"Written: {outname}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python dcd-to-pdbs.py <topology_file> <dcd_file> <output_prefix>")
        sys.exit(1)
    topology_file = sys.argv[1]
    dcd_file = sys.argv[2]
    output_prefix = sys.argv[3]
    dcd_to_pdb(topology_file, dcd_file, output_prefix)
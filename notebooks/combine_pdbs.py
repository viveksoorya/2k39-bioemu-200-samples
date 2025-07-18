import os
import glob
import argparse
from Bio import PDB

def combine_pdb_samples_to_trajectory(input_folder):
    """
    Combines multiple PDB files from the input_folder into a single 
    multi-model PDB trajectory and saves it in the same directory.
    """
    ms = PDB.Structure.Structure("multi_model")
    parser = PDB.PDBParser(QUIET=True)

    file_list = sorted(glob.glob(os.path.join(input_folder, "sample_*-fixed.pdb")))

    if not file_list:
        raise FileNotFoundError(f"No files matching 'sample_*-fixed.pdb' found in {input_folder}")

    for model_num, filename in enumerate(file_list, 1):
        model = parser.get_structure("temp", filename)[0]
        model.id = model_num
        model.serial_num = model_num
        ms.add(model)

    output_file = os.path.join(input_folder, "combined-samples-trajectory.pdb")
    io = PDB.PDBIO()
    io.set_structure(ms)
    io.save(output_file)

    return output_file

def main():
    parser = argparse.ArgumentParser(description="Combine PDB samples into a multi-model PDB trajectory.")
    parser.add_argument("-i", "--input_folder", required=True, help="Input folder containing pdb samples")

    args = parser.parse_args()
    output_path = combine_pdb_samples_to_trajectory(args.input_folder)
    print(f"Combined trajectory saved to: {output_path}")

if __name__ == "__main__":
    main()


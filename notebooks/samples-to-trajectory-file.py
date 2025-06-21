from Bio import PDB
import glob

ms = PDB.Structure.Structure("multi_model")
parser = PDB.PDBParser()

file_list = sorted(glob.glob("visualization-fixed/sample_*-fixed.pdb"))

for model_num, filename in enumerate(file_list, 1):
    model = parser.get_structure("temp", filename)[0]
    model.id = model_num
    model.serial_num = model_num
    ms.add(model)

io = PDB.PDBIO()
io.set_structure(ms)
io.save("visualization-fixed/combined-samples-trajectory.pdb")

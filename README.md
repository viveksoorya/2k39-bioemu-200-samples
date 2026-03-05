# 2K39 BioEmu 200 Samples

This repository contains 200 protein structure samples generated using BioEmu's diffusion-based protein structure emulator, along with analysis and molecular dynamics workflows. The work was completed during an internship at BioEmu under the supervision of Dr. Kalyan Chakrabarti (Krea University) and Dr. Sudip Roy (Krea University).

## Overview

This project demonstrates the use of BioEmu (a neural network that generates protein structures via a diffusion process) to create diverse conformational samples of the 2K39 protein. The repository includes:

- **200 generated protein structure samples** from BioEmu
- **Molecular dynamics (MD) simulations** to refine and relax the generated structures
- **Structural analysis** including RMSD, RMSF, PCA, and Ramachandran plots
- **Visualization tools** for examining the generated structures

## Background

### BioEmu

BioEmu is a diffusion-based model that generates protein structures by learning from the Protein Data Bank (PDB). Unlike AlphaFold (which predicts structure from sequence), BioEmu generates conformational ensembles from a reference structure, enabling exploration of protein dynamics and flexibility.

### Protein 2K39

2K39 is a ubiquitin-like protein from *Arabidopsis thaliana* involved in the SUMOylation pathway. It serves as an excellent test case due to its small size (76 residues), well-structured fold, and relevance to protein dynamics studies.

## Repository Structure

```
2k39-bioemu-200-samples/
├── amino-acid-diagrams/     # Amino acid reference diagrams
├── cg_coefficients/         # Coarse-grained model coefficients
├── chimera/                 # UCSF Chimera visualization scripts
├── configs/                 # Configuration files
├── docs/                    # Documentation
├── exports/                 # HTML exports and visualizations
├── initial-notebook-workflow/ # Initial exploration notebooks
├── molecule-ascii/          # ASCII molecule representations
├── molecular-dynamics/      # GROMACS MD simulation workflows
│   ├── gromacs-tutor/      # GROMACS training materials
│   ├── output/             # MD output PDBs
│   ├── 2k39-md.py          # Main MD script
│   └── aMD.py              # Accelerated MD implementation
├── pca/                     # Principal Component Analysis
├── PDBs/                    # Generated protein structures
├── ramachandran-plots-using-chimera-py-scripts/ # Ramachandran analysis
├── ramchandran-plots/       # Ramachandran plot results
├── reading-for-bioemu/      # Research papers and references
├── scripts/                 # Utility scripts
│   ├── combine_pdbs.py      # Combine PDBs into trajectory
│   └── dcd-to-pdbs.py      # Convert DCD to PDB format
└── chimerax-run-instructions.txt
```

## Key Results

### Sample Generation

- Generated **200 diverse samples** from the 2K39 reference structure using BioEmu
- Samples capture conformational diversity in the protein's loop regions and side chains

### Structural Quality

- **Ramachandran plots** show that generated structures maintain good backbone geometry
- Most residues fall in favored and allowed regions of the Ramachandran plot
- No residues in disallowed regions (typical of high-quality structures)

### RMSD Analysis

- All-atom RMSD of generated samples: ~2-4 Å from reference
- Core structure remains conserved while loops show expected flexibility

### Molecular Dynamics

- GROMACS MD simulations used to refine and relax generated structures
- 200 samples processed through energy minimization and equilibration
- Combined trajectory generated for ensemble analysis

## Getting Started

### Prerequisites

- Python 3.8+
- GROMACS (for MD simulations)
- UCSF Chimera or ChimeraX (for visualization)
- Required Python packages: MDAnalysis, NumPy, Matplotlib

### Running the Pipeline

1. **Generate samples with BioEmu** (requires BioEmu API access)

2. **Run molecular dynamics:**
   ```bash
   cd molecular-dynamics
   python 2k39-md.py
   ```

3. **Analyze structures:**
   ```bash
   cd ../scripts
   python combine_pdbs.py
   ```

4. **Visualize with ChimeraX:**
   ```
   See chimerax-run-instructions.txt
   ```

## Scripts

### `molecular-dynamics/2k39-md.py`
Main script for running GROMACS MD simulations on generated structures.

### `scripts/combine_pdbs.py`
Combines multiple PDB files into a single trajectory file for analysis.

### `scripts/dcd-to-pdbs.py`
Converts DCD trajectory files to individual PDB files.

## Visualization

### ChimeraX

Use UCSF ChimeraX to visualize the protein structures:
```bash
# See chimerax-run-instructions.txt for detailed commands
```

### HTML Exports

Pre-generated visualizations are available in the `exports/` directory:
- `2k39-analysis-using-all-atoms.html` - Interactive analysis view
- `bioemu-generated-ubq-samples-colabfold-run.html` - ColabFold comparison

## References

- BioEmu: Diffusion-based protein structure emulation
- 2K39 PDB: SUMO-conjugating enzyme from Arabidopsis thaliana
- Internship Report: Vivek Soorya Maadoori - "Protein Structure and Dynamics: An Exploration with BioEmu"

## Author

**Vivek Soorya Maadoori**  
Intern, BioEmu  
Under the supervision of Dr. Kalyan Chakrabarti (Krea University) and Dr. Sudip Roy (Krea University).

## License

This repository is provided for educational and research purposes.

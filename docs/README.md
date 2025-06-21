# Workflow

### Package and environment mangement:

Install conda for package and environemnt management. You will need it for this workflow, especially to manage environments. In the course of this workflow you will use at least two environments. If you choose to, you can create and activate separate environment for this workflow using the following command:

``` bash
conda env create --name <insert-environment-name>

conda activate <insert-environment-name>
```

### Run the following bash command to run bioemu:
```bash
python -m bioemu.sample --sequence MQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDGRTLSDYNIQKESTLHLVLRLRGG --num_samples 200 --output_dir ./.2k39-backbone-bioemu-samples
```
You can change the arguments passed as it suits your case.

##### This will get you a bunch of files in the stipulated output directory. About them:

1) You will see a lot of files with the npz extension. These are files you don't need to worry about. Just leave them as is and do not mess with them.
2) The files that you will directly use are: the files with pdb, fasta and xtc extensions.

### Running renders only samples with backbones, to render the sidechains use the following workflow:

1) clone hpacker

Using GitHub Cli:

``` bash
gh clone repo gvisani/hpacker
```

or using ssh:
``` bash
git clone git@github.com:gvisani/hpacker.git 
```

or using https:
``` bash
git clone https://github.com/gvisani/hpacker.git
```

2) cd into hpacker

3) Create and activate conda environment for hpacker

``` bash
conda create --name hpacker python=3.10
conda activate hpacker 
```
4) Install the dependencies for hpacker

``` bash
conda install pytorch==1.13.1 pytorch-cuda=11.7 -c pytorch -c nvidia
pip install biopython==1.81 tqdm==4.67.1 progress==1.6 h5py==3.13.0 hdf5plugin==5.1.0 sqlitedict==2.1.0 'numpy<2' e3nn==0.5.0 mkl==2024.0
```
5) install hpacker in edit mode

```bash
pip install -e .
```

6) run the following command:
``` bash
python 300-odd-atoms-to-600-odd-atoms.py -f <insert-input-file-or-path-of-directory-containing-only-files-to-be-converted>
```

If you want to, you can optionally specify a directory path for output folder if you have inputted a folder path, or, a file path for output, if you have inputted a file path using -o flag


7) Running the sidechain reconstruction renders the heavy atoms but not hydrogens; To get the complete picture of the conformation(s) by including the hydrogen atoms, run 600-odd-to-1200-odd-atoms.py:
``` bash
python 600-odd-to-1200-odd-atoms.py -f <insert-input-file-or-path-of-directory-containing-only-files-to-be-converted> 
```

Same as above, you can optionally specify output directory or file path using -o flag


### Use MDAnalysis to render individual frames






### Unsorted notes:
```bash
conda install ipywidgets
sudo apt upgrade jupyter 
```
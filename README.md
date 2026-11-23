# rat-brain-body-dataset
Code and processing workflows for the Rat Brain–Body Recordings and Rat Brain–Body Derived Data datasets published on EBRAINS.

## Installation

The code in `recordings/` needs Python 3.11 or newer.

### With pip

macOS and Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r recordings/requirements.txt
jupyter lab recordings
```

Windows:

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r recordings/requirements.txt
jupyter lab recordings
```

### With conda

```bash
conda env create -f recordings/environment.yml
conda activate rbbr
jupyter lab recordings
```

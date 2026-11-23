# rat-brain-body-dataset
Code and processing workflows for the Rat Brain–Body Recordings and Rat Brain–Body Derived Data datasets published on EBRAINS.

## Datasets

### Rat Brain–Body Recordings

Multimodal physiological recordings from eight rats, including EEG, EMG, ECG, EGG, temperature, and activity.
The dataset contains assembled 24-hour recordings and corresponding artefact-cleaned recordings.

## Repository structure
```text
rat-brain-body-dataset/
├── recordings/
│   ├── 01_read_and_concatenate_edf.ipynb
│   ├── 02_remove_artefacts_and_clean_nan.ipynb
│   ├── calibration.py
│   ├── edf_writer_worker.py
│   ├── environment.yml
│   └── requirements.txt
├── .gitignore
├── LICENSE
└── README.md
```

The `recordings/` directory contains the processing code for the Rat Brain–Body Recordings dataset. Additional workflows for the related derived data will be added separately.

## Processing workflows

### 01 — Assembly of 24-hour recordings

`01_read_and_concatenate_edf.ipynb`

Assembles hourly acquisition files into continuous 24-hour, single-channel EDF recordings for each animal and physiological signal.
- **Input:** Hourly acquisition EDF files.
- **Output:** Assembled 24-hour EDF files and JSON sidecars documenting missing-data intervals.
The original hourly acquisition files are available upon request.

### 02 — Artefact cleaning

`02_remove_artefacts_and_clean_nan.ipynb`

Identifies and masks high-amplitude artefacts in the assembled recordings, allowing users to review and adjust detection thresholds.
- **Input:** Assembled 24-hour EDF recordings.
- **Output:** Cleaned EDF recordings and corresponding JSON sidecars.
This notebook can be run using the assembled recordings available in the EBRAINS dataset.

## Data availability

The Rat Brain–Body Recordings dataset is hosted on EBRAINS and includes two recording layers:

- `recordings-24h/`: assembled recordings.
- `recordings-24h-clean/`: artefact-cleaned recordings.

Both layers contain EEG, EMG, ECG, EGG, temperature, and activity recordings organized by animal.

The original hourly acquisition files and transmitter-specific temperature calibration information are not included in the published dataset but are available upon request.

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

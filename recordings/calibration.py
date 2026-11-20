"""
Calibration helpers for notebooks 01 and 02.

Released values:
  EEG, ECG, EGG, EMG : uV = Lo + count * (Hi - Lo) / 65535, header range fixed to Lo..Hi
                       (digital -32768..32767: one digital step = one ADC count).
  Temperature        : degC = low + count * (high - low) / 65535, low/high per transmitter
                       (temp_calibration_final.xlsx); header range = min/max of each file.
  Activity           : a.u., values as exported; header range = min/max of each file.
  Clean layer        : same values and units as the 24-h layer; Activity x 1e-6.
Requires openpyxl (reads the xlsx).
"""

import numpy as np
import openpyxl

ADC_FULL_SCALE = 65535

EPHYS_RANGE_UV = {
    "EMG": (-18000.0, 12000.0),
    "ECG": (-36000.0, 24000.0),
    "EGG": (-72000.0, 48000.0),
    "EEG": (-72000.0, 48000.0),
}
OUTPUT_DIMENSION = {"EMG": "uV", "ECG": "uV", "EGG": "uV", "EEG": "uV",
                    "Temperature": "degC", "Activity": "a.u."}
TEMPERATURE_TRANSDUCER = "LMT70 in A3047A3D-C transmitter"

# Set from the configuration cell of notebook 01
SOURCE_VALUES = {}              # signal -> "counts" or "calibrated"

def load_temperature_table(path):
    """{(receiver, rat_idx): (low, high, transmitter_id)} from temp_calibration_final.xlsx."""
    rows = openpyxl.load_workbook(path, read_only=True, data_only=True).active.iter_rows(values_only=True)
    col = {name: i for i, name in enumerate(next(rows))}
    table = {}
    for r in rows:
        if r[col["receiver"]] is None:
            continue
        rat_idx = int(str(r[col["folder_index"]]).lower().replace("rat", ""))
        table[(str(r[col["receiver"]]).strip(), rat_idx)] = (
            float(r[col["low_C_at_sample_0"]]), float(r[col["high_C_at_sample_65535"]]),
            int(r[col["transmitter_id"]]))
    return table

def calibrate(signal, data, receiver, rat_idx, temperature_table):
    """
    Source values of one channel -> (values, kwargs for write_single_channel_edf:
    dimension, phys_range, transducer, sidecar_extra).
    """
    data = np.asarray(data, dtype=float)
    kw = {"dimension": OUTPUT_DIMENSION[signal], "phys_range": None,
          "transducer": "", "sidecar_extra": None}
    counts = SOURCE_VALUES.get(signal) == "counts"

    if signal in EPHYS_RANGE_UV:
        lo, hi = EPHYS_RANGE_UV[signal]
        kw["phys_range"] = (lo, hi)
        if counts:
            data = lo + np.rint(data) * (hi - lo) / ADC_FULL_SCALE
    elif signal == "Temperature":
        kw["transducer"] = TEMPERATURE_TRANSDUCER
        if counts:
            low, high, transmitter_id = temperature_table[(receiver, rat_idx)]
            data = low + np.rint(data) * (high - low) / ADC_FULL_SCALE
            kw["sidecar_extra"] = {
                "unit": "degC",
                "temperature_calibration": {
                    "formula": "T = low + sample * (high - low) / 65535",
                    "low_degC_at_sample_0": low,
                    "high_degC_at_sample_65535": high,
                    "transmitter_id": transmitter_id,
                    "source": ("OSI calibration sheet A235_2, fit-based values: low/high from "
                               "the slope and the count at 37.0 degC (temp_calibration_final.xlsx)"),
                }}
    return data, kw

def to_digital(values, lo, hi):
    """Physical values -> int16 digital values for the fixed range lo..hi."""
    dig = np.rint((np.asarray(values, dtype=float) - lo) * (ADC_FULL_SCALE / (hi - lo))) - 32768
    return np.clip(dig, -32768, 32767).astype(np.int16)

def clean_scale(signal):
    """
    Factor applied to the array MNE returns (notebook 02). MNE converts uV headers to volts,
    so EEG/ECG/EGG/EMG go back to uV. Activity keeps the x 1e-6 of the released clean layer
    (intentional; header a.u. in both layers). Temperature (degC) is not rescaled by MNE.
    """
    if signal in EPHYS_RANGE_UV:
        return 1e6
    return 1e-6 if signal == "Activity" else 1.0
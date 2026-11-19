"""
Worker function for parallel EDF writing.

Designed to be called from a ProcessPoolExecutor. Each invocation writes
a single-channel EDF file using pyedflib and validates the result.
"""

import json
from pathlib import Path
import numpy as np
import pyedflib

def _find_nan_gaps(data: np.ndarray, fs: float) -> list[list[float]]:
    """Return [[offset_s, duration_s], ...] for every contiguous NaN run."""
    mask = np.isnan(data)
    if not np.any(mask):
        return []
    padded = np.concatenate(([False], mask, [False]))
    diff = np.diff(padded.astype(np.int8))
    starts = np.where(diff == 1)[0]
    ends = np.where(diff == -1)[0]
    return [[float(s / fs), float((e - s) / fs)] for s, e in zip(starts, ends)]

def _write_sidecar_json(
    sidecar_out_path: str,
    data: np.ndarray,
    fs: float,
    label: str,
    starttime_unix: float,
    extra: dict | None = None,
) -> None:
    """Write a lightweight JSON sidecar with gap intervals only (no signal copy)."""
    path = Path(sidecar_out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "starttime_unix": float(starttime_unix),
        "fs": float(fs),
        "n_samples": int(len(data)),
        "label": label,
        "gaps": _find_nan_gaps(data, fs),
    }
    if extra:
        payload.update(extra)
    with open(path, "w") as fh:
        json.dump(payload, fh)

def _validate_written_edf(out_path: str, expected_samples: int, expected_fs: float) -> None:
    """Read the written EDF back and verify its basic timing metadata."""
    reader = pyedflib.EdfReader(out_path)
    try:
        actual_samples = int(reader.getNSamples()[0])
        actual_fs = float(reader.getSampleFrequency(0))
        actual_duration = float(reader.getFileDuration())
    finally:
        reader.close()

    expected_duration = expected_samples / expected_fs
    duration_tol = max(1e-6, 0.5 / expected_fs)
    fs_tol = max(1e-6, expected_fs * 1e-9)

    if actual_samples != expected_samples:
        raise ValueError(
            f"sample count mismatch: expected {expected_samples}, got {actual_samples}"
        )
    if abs(actual_fs - expected_fs) > fs_tol:
        raise ValueError(
            f"sampling frequency mismatch: expected {expected_fs}, got {actual_fs}"
        )
    if abs(actual_duration - expected_duration) > duration_tol:
        raise ValueError(
            f"duration mismatch: expected {expected_duration}s, got {actual_duration}s"
        )

def write_single_channel_edf(
    out_path: str,
    data: np.ndarray,
    fs: float,
    label: str,
    starttime_unix: float,
    sidecar_out_path: str | None = None,
    dimension: str = "uV",
    phys_range: tuple[float, float] | None = None,
    transducer: str = "",
    sidecar_extra: dict | None = None,
) -> str:
    """
    Write a one-channel EDF file.

    Parameters
    ----------
    out_path : str
        Destination file path.
    data : np.ndarray
        1-D signal array (NaN = missing → replaced by 0.0 on write).
    fs : float
        Sampling frequency in Hz.
    label : str
        Channel label (e.g. "EMG", "EEG", "Activity").
    starttime_unix : float
        Unix timestamp for the start of the recording (sets EDF header).
    sidecar_out_path : str | None
        Optional NPZ sidecar path. When provided, saves the original array
        with NaNs preserved plus a boolean missing-data mask.
    dimension : str
        Physical dimension written to the header ("uV", "degC", "a.u.").
    phys_range : (float, float) | None
        Fixed physical range of the header. The samples are then written as exact
        digital values (one digital step = one ADC count). None: min/max of the data.
    transducer : str
        Transducer text of the header.
    sidecar_extra : dict | None
        Extra keys added to the JSON sidecar.

    Returns
    -------
    str
        Short status message.
    """
    from datetime import datetime, timezone

    # Replace NaN with 0.0 for EDF (EDF has no NaN concept)
    clean = np.where(np.isnan(data), 0.0, data)

    n_samples = len(clean)
    duration_s = n_samples / fs

    # Physical min/max — guard against flat signals
    pmin = float(np.min(clean))
    pmax = float(np.max(clean))
    if pmin == pmax:
        pmin -= 1.0
        pmax += 1.0
    if phys_range is not None:
        pmin, pmax = phys_range

    # Start datetime (UTC)
    start_dt = datetime.fromtimestamp(starttime_unix, tz=timezone.utc)

    f = pyedflib.EdfWriter(out_path, 1, file_type=pyedflib.FILETYPE_EDFPLUS)
    try:
        f.setStartdatetime(start_dt)

        ch_info = {
            "label": label,
            "dimension": dimension,
            "sample_frequency": fs,
            "physical_min": pmin,
            "physical_max": pmax,
            "digital_min": -32768,
            "digital_max": 32767,
            "transducer": transducer,
            "prefilter": "",
        }
        f.setSignalHeader(0, ch_info)

        if phys_range is not None:
            digital = np.rint((clean - pmin) * (65535.0 / (pmax - pmin))) - 32768
            f.writeSamples([digital.astype(np.int16)], digital=True)
        else:
            f.writeSamples([clean])
    finally:
        f.close()

    try:
        _validate_written_edf(out_path, n_samples, fs)
    except Exception:
        path = Path(out_path)
        if path.exists():
            path.unlink()
        if sidecar_out_path is not None:
            sidecar_path = Path(sidecar_out_path)
            if sidecar_path.exists():
                sidecar_path.unlink()
        raise

    if sidecar_out_path is not None:
        _write_sidecar_json(sidecar_out_path, data, fs, label, starttime_unix, sidecar_extra)

    size_mb = n_samples * 2 / 1e6  # 16-bit → 2 bytes/sample
    sidecar_msg = " + sidecar" if sidecar_out_path is not None else ""
    return f"wrote {n_samples} samples ({duration_s:.0f}s, ~{size_mb:.1f} MB){sidecar_msg}"
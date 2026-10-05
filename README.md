# MRI 2D to 3D Brain Reconstruction

A Python-based research and demonstration project for reconstructing a 3D brain surface from a series of 2D MRI DICOM slices.

The project reads DICOM MRI series, reconstructs a volumetric representation, performs preprocessing and brain segmentation, extracts a 3D surface, and provides interactive visualization using PyVista.

> **Research / Demonstration Project**  
> This project is intended for research and visualization purposes and is **not a clinically validated diagnostic or surgical navigation system**.

---

## Demo

### 3D Brain Reconstruction

![3D Brain Reconstruction](demo/brain_3D.png)

### Interactive 3D Viewer

![3D Brain Viewer](demo/brain_3d_viewer.png)

### Surface Reconstruction

![Surface 3D](demo/surface_3d.png)

---

## Overview

MRI scanners produce a sequence of 2D cross-sectional images. This project demonstrates how these slices can be processed and reconstructed into a 3D representation of the brain.

The general process is:

```text
2D MRI DICOM Slices
        │
        ▼
DICOM Series Selection
        │
        ▼
Volume Reconstruction
        │
        ▼
Intensity Normalization
        │
        ▼
Isotropic Resampling
        │
        ▼
Brain Segmentation
        │
        ▼
3D Surface Extraction
        │
        ▼
Interactive 3D Visualization
```

The project currently contains **three independent Python implementations** for MRI 3D reconstruction and visualization.

---

## Project Structure

```text
MRI-2D-to-3D-Brain/
│
├── README.md
│
├── src/
│   ├── brain_3D.py
│   ├── brain_3d_viewer.py
│   └── surface_3d.py
│
├── demo/
│   ├── brain_3D.png
│   ├── brain_3d_viewer.png
│   └── surface_3d.png
│
├── outputs/
│   ├── brain_3d.ply
│   ├── brain_3d.stl
│   └── mri_3d_report.txt
│
├── requirements.txt
│
└── .gitignore
```

---

## Implementations

### 1. `brain_3D.py`

The main and most complete reconstruction implementation.

Features include:

- DICOM series discovery
- Automatic MRI series ranking
- T1 / T2 / FLAIR sequence prioritization
- DICOM slice ordering using image orientation and position
- MRI intensity normalization
- 1 mm isotropic resampling
- Brain mask extraction
- Brain surface reconstruction
- Ventricular / CSF estimation
- Mesh cleaning
- Mesh decimation
- Surface smoothing
- PLY and STL export
- NIfTI output
- Interactive PyVista visualization

The viewer also provides interactive controls for:

```text
Mouse Left   → Rotate
Mouse Wheel  → Zoom
Mouse Right  → Pan

1 → Toggle Brain
2 → Toggle Ventricles
O → Transparency
R → Reset Camera
Q → Exit
```

---

### 2. `brain_3d_viewer.py`

An independent implementation focused on generating and displaying a 3D brain surface.

Main steps:

```text
DICOM
  ↓
Series Selection
  ↓
Volume Reconstruction
  ↓
Normalization
  ↓
1 mm Resampling
  ↓
Brain Mask
  ↓
3D Surface
  ↓
Interactive Viewer
```

It provides a simplified interactive 3D visualization using PyVista.

---

### 3. `surface_3d.py`

A separate experimental implementation for extracting a 3D brain surface directly from a selected MRI series.

It performs:

- DICOM scanning
- Series analysis
- MRI volume reconstruction
- Intensity normalization
- Isotropic resampling
- Threshold-based brain extraction
- Connected-component filtering
- Marching Cubes surface extraction
- Mesh smoothing
- Interactive 3D visualization

---

## Technical Approach

### DICOM Processing

The project uses `pydicom` to read MRI DICOM files and extract important spatial information such as:

- `PixelSpacing`
- `ImagePositionPatient`
- `ImageOrientationPatient`
- `SliceThickness`
- `SeriesInstanceUID`
- `SeriesDescription`
- `Modality`

Slices are ordered according to their physical position rather than their filename.

---

### Volume Reconstruction

Individual 2D MRI slices are stacked into a 3D volume:

```text
Slice 1
Slice 2
Slice 3
   .
   .
   .
Slice N

      ↓

3D MRI Volume
```

The original voxel spacing is extracted from the DICOM metadata.

---

### Intensity Normalization

MRI intensity values are normalized using percentile-based clipping.

The lower and upper percentiles are used to reduce the influence of extreme intensity values before scaling the volume.

---

### Isotropic Resampling

The reconstructed volume is resampled toward:

```text
1.0 × 1.0 × 1.0 mm
```

isotropic voxel spacing.

This makes the spatial resolution approximately uniform in all three dimensions and provides a more consistent basis for 3D surface extraction.

---

### Brain Segmentation

A threshold-based segmentation approach is used to create an approximate brain mask.

The processing includes techniques such as:

- Otsu thresholding
- Binary opening
- Binary closing
- Hole filling
- Distance transform
- Connected-component analysis

The largest relevant connected component is retained as the primary brain region.

---

### 3D Surface Reconstruction

The 3D surface is extracted using the **Marching Cubes** algorithm.

Conceptually:

```text
3D MRI Volume
      │
      ▼
Brain Mask / Intensity Field
      │
      ▼
Marching Cubes
      │
      ▼
Vertices + Triangular Faces
      │
      ▼
3D Mesh
```

The resulting mesh can be cleaned, simplified and smoothed before visualization or export.

---

## Output Formats

The main reconstruction implementation can generate:

| Format | Purpose |
|---|---|
| `.PLY` | 3D mesh visualization and processing |
| `.STL` | 3D mesh / CAD-compatible representation |
| `.NII.GZ` | Volumetric medical imaging representation |
| `.TXT` | Reconstruction report |

Example outputs:

```text
outputs/
├── brain_3d.ply
├── brain_3d.stl
├── mri_3d_report.txt
└── ...
```

---

## Technologies

- Python
- NumPy
- SciPy
- scikit-image
- pydicom
- PyVista
- VTK
- nibabel
- Tkinter

### Main Algorithms

- DICOM spatial sorting
- Percentile-based intensity normalization
- Otsu thresholding
- Morphological operations
- Distance transform
- Connected-component analysis
- Marching Cubes
- Mesh decimation
- Taubin / surface smoothing
- Interactive 3D rendering

---

## Installation

Clone the repository:

```bash
git clone https://github.com/AlirezaSobhani82/MRI-2D-to-3D-Brain.git
cd MRI-2D-to-3D-Brain
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Input Data

The application expects a folder containing MRI DICOM files.

Example:

```text
MRI Dataset/
└── Patient/
    └── Image/
        ├── 1.dcm
        ├── 2.dcm
        ├── 3.dcm
        └── ...
```

The application scans the selected directory and attempts to identify usable DICOM series automatically.

For privacy and repository size reasons, the original patient DICOM dataset is **not included in this repository**.

---

## Running the Main Demo

Run:

```bash
python src/brain_3D.py
```

A folder-selection window will appear.

Select the directory containing the DICOM MRI data.

The program will then:

1. Scan available DICOM series
2. Rank candidate MRI sequences
3. Allow the user to select a series
4. Reconstruct the 3D volume
5. Normalize and resample the volume
6. Extract the brain mask
7. Generate the 3D brain surface
8. Estimate ventricular / CSF regions
9. Save 3D models
10. Open the interactive 3D viewer

---

## Research Notes

This project focuses on **3D reconstruction and visualization**, rather than medical diagnosis.

The ventricular / CSF region is an algorithmic intensity-based estimate and should not be interpreted as a clinically validated anatomical segmentation.

No tumor diagnosis, lesion diagnosis, or clinical decision-making is performed by this software.

---

## Limitations

The reconstruction quality depends strongly on the input MRI acquisition and DICOM series.

Potential factors include:

- Slice thickness
- In-plane resolution
- MRI sequence
- Patient positioning
- Image orientation
- Motion artifacts
- Intensity characteristics
- Missing or incomplete slices

Threshold-based segmentation may also include or exclude anatomical structures incorrectly in some datasets.

---

## Future Improvements

Potential future improvements include:

- Automatic T1 sequence selection
- More robust skull stripping
- Advanced brain segmentation
- Anatomical structure segmentation
- Better handling of anisotropic MRI
- Multi-planar visualization
- Web-based 3D visualization
- GPU acceleration
- Deep-learning-based segmentation
- Support for additional medical imaging formats

---

## Disclaimer

This repository is a **research and demonstration project**.

It has not been clinically validated and should not be used for diagnosis, treatment planning, surgical navigation, or other clinical decisions.

---

## Author

**Alireza Sobhani**

Computer Vision Engineer | AI Engineer

Focused on:

```text
Computer Vision
Machine Learning
Deep Learning
Medical Imaging
3D Reconstruction
Video AI
```
# MRI 2D → 3D Brain Reconstruction

**Medical Imaging · DICOM · 3D Reconstruction · Computer Vision · Python**

A research and demonstration project for reconstructing and visualizing a 3D brain surface from 2D MRI DICOM slices.

The project focuses on DICOM processing, volumetric reconstruction, image preprocessing, brain segmentation, 3D surface extraction, mesh processing, and interactive visualization.

> **Research / Demonstration Project**  
> This project is intended for research and visualization purposes and is not clinically validated for diagnosis or clinical decision-making.

---

## Demo

### 3D Brain Reconstruction

![3D Brain Reconstruction](demo/brain_3D.png)

### Interactive 3D Brain Viewer

![Interactive 3D Brain Viewer](demo/brain_3d_viewer.png)

### Surface Reconstruction

![Surface Reconstruction](demo/surface_3d.png)

---

## Project Overview

MRI data is typically acquired as a sequence of 2D cross-sectional slices.

This project demonstrates how these slices can be processed and reconstructed into a 3D representation of the brain.

```text
2D MRI DICOM Slices
        │
        ▼
DICOM Series Analysis
        │
        ▼
3D Volume Reconstruction
        │
        ▼
Intensity Normalization
        │
        ▼
1 mm Isotropic Resampling
        │
        ▼
Brain Segmentation
        │
        ▼
3D Surface Extraction
        │
        ▼
Mesh Processing
        │
        ▼
Interactive 3D Visualization
```

The repository contains **three independent Python implementations** for MRI 3D reconstruction and visualization.

---

# Key Features

- DICOM MRI series discovery and analysis
- MRI sequence selection and ranking
- Geometry-aware DICOM slice ordering
- 3D volumetric reconstruction
- MRI intensity normalization
- 1 mm isotropic resampling
- Brain mask extraction
- Morphological image processing
- Connected-component analysis
- Marching Cubes surface extraction
- 3D mesh cleaning and smoothing
- Mesh decimation
- PLY and STL export
- Interactive 3D visualization with PyVista
- Optional NIfTI output
- Reconstruction report generation

---

# Three Independent Implementations

The repository contains three separate implementations. They are **not sequential stages of a single pipeline**.

```text
                         MRI DICOM
                            │
             ┌──────────────┼──────────────┐
             │              │              │
             ▼              ▼              ▼
       brain_3D.py   brain_3d_viewer.py   surface_3d.py
             │              │              │
             ▼              ▼              ▼
          Demo 1          Demo 2          Demo 3
```

## 1. `brain_3D.py`

The main and most feature-rich implementation.

It provides a complete workflow for MRI volume reconstruction, brain extraction, mesh generation, and interactive visualization.

### Main capabilities

- DICOM series scanning
- MRI sequence ranking
- T1 / T2 / FLAIR prioritization
- Geometry-based slice ordering
- Intensity normalization
- 1 mm isotropic resampling
- Brain mask extraction
- Brain surface reconstruction
- Algorithmic ventricular / CSF estimation
- Mesh cleaning
- Mesh decimation
- Surface smoothing
- PLY export
- STL export
- Optional NIfTI export
- Interactive PyVista viewer
- Reconstruction report generation

### Interactive controls

```text
Mouse Left   → Rotate
Mouse Wheel  → Zoom
Mouse Right  → Pan

1 → Toggle Brain
2 → Toggle Ventricles
O → Change Transparency
R → Reset Camera
Q → Exit
```

---

## 2. `brain_3d_viewer.py`

An independent and simplified implementation focused on reconstructing and displaying a 3D brain surface.

Main stages:

```text
DICOM
  ↓
Series Selection
  ↓
Volume Reconstruction
  ↓
Intensity Normalization
  ↓
1 mm Resampling
  ↓
Brain Mask
  ↓
3D Surface
  ↓
Interactive Viewer
```

This implementation provides a simpler approach for generating a smooth 3D brain surface and visualizing it interactively with PyVista.

---

## 3. `surface_3d.py`

A separate experimental implementation focused on direct brain surface extraction.

Main operations include:

- DICOM scanning
- Series analysis
- MRI volume reconstruction
- Intensity normalization
- Isotropic resampling
- Threshold-based brain extraction
- Morphological processing
- Connected-component filtering
- Marching Cubes
- Mesh smoothing
- Interactive 3D visualization

---

# Technical Approach

## 1. DICOM Processing

The project uses `pydicom` to read MRI DICOM files and extract spatial and acquisition information.

Important metadata includes:

```text
PixelSpacing
ImagePositionPatient
ImageOrientationPatient
SliceThickness
SeriesInstanceUID
SeriesDescription
Modality
```

Slices are ordered according to their physical position and orientation rather than relying on filenames.

---

## 2. 3D Volume Reconstruction

Individual MRI slices are reconstructed into a volumetric array.

```text
Slice 1
Slice 2
Slice 3
   .
   .
   .
Slice N
   │
   ▼
3D MRI Volume
```

Voxel spacing is calculated from DICOM spatial metadata.

---

## 3. Intensity Normalization

MRI intensity values can vary significantly between scans.

The implementations use percentile-based intensity clipping and normalization to reduce the effect of extreme values and produce a more stable intensity range for subsequent processing.

---

## 4. Isotropic Resampling

The reconstructed volume is resampled toward:

```text
1.0 × 1.0 × 1.0 mm
```

isotropic voxel spacing.

This provides approximately uniform spatial resolution in all three dimensions and improves consistency during 3D surface extraction.

---

## 5. Brain Segmentation

The project uses classical image-processing techniques to create an approximate brain mask.

Methods include:

- Otsu thresholding
- Binary opening
- Binary closing
- Hole filling
- Distance transform
- Connected-component analysis
- Morphological filtering

The largest relevant connected component is used as the primary brain region.

---

## 6. 3D Surface Reconstruction

The 3D surface is extracted using the **Marching Cubes** algorithm.

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
      │
      ▼
Cleaning / Smoothing / Decimation
      │
      ▼
Interactive 3D Visualization
```

The resulting mesh can be exported as PLY or STL.

---

# Output

The repository contains example generated outputs:

```text
outputs/
├── brain_3d.ply
├── brain_3d.stl
└── mri_3d_report.txt
```

### Supported output types

| Format | Purpose |
|---|---|
| `.PLY` | 3D mesh visualization and processing |
| `.STL` | 3D mesh and CAD-compatible workflows |
| `.NII.GZ` | Volumetric medical imaging |
| `.TXT` | Reconstruction report |

---

# Technologies

### Programming

- Python

### Medical Imaging

- pydicom
- DICOM
- NIfTI

### Scientific Computing

- NumPy
- SciPy
- scikit-image

### 3D Processing & Visualization

- PyVista
- VTK
- Marching Cubes

### GUI

- Tkinter

### Optional

- nibabel

---

# Main Algorithms

```text
DICOM Spatial Sorting
        ↓
Percentile-Based Normalization
        ↓
Isotropic Resampling
        ↓
Otsu Thresholding
        ↓
Morphological Processing
        ↓
Connected Components
        ↓
Distance Transform
        ↓
Marching Cubes
        ↓
Mesh Cleaning
        ↓
Mesh Decimation
        ↓
Surface Smoothing
        ↓
Interactive 3D Rendering
```

---

# Installation

Clone the repository:

```bash
git clone https://github.com/AlirezaSobhani82/MRI-2D-to-3D-Brain.git
cd MRI-2D-to-3D-Brain
```

Install the required Python packages:

```bash
pip install -r requirements.txt
```

---

# Input Data

The application expects a directory containing MRI DICOM files.

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

The application scans the selected directory and identifies available DICOM series.

The original patient dataset is **not included in this repository**.

No patient-identifiable DICOM data is distributed with the project.

---

# Running the Project

## Main Implementation

Run:

```bash
python src/brain_3D.py
```

The application opens a folder-selection dialog.

Select the directory containing the MRI DICOM data.

The program then performs:

```text
1. Scan DICOM files
2. Analyze available MRI series
3. Rank candidate series
4. Select an MRI series
5. Reconstruct the 3D volume
6. Normalize image intensity
7. Resample to approximately 1 mm isotropic spacing
8. Extract the brain region
9. Generate the 3D surface
10. Generate optional ventricular / CSF estimate
11. Export 3D meshes
12. Open the interactive viewer
```

---

## Simplified Viewer

Run:

```bash
python src/brain_3d_viewer.py
```

This implementation provides an independent workflow for generating and interactively viewing a 3D brain surface.

---

## Surface Reconstruction

Run:

```bash
python src/surface_3d.py
```

This implementation provides another independent approach based on thresholding, morphological processing, and surface extraction.

---

# Example Result

The generated 3D mesh can be interactively rotated, zoomed, and inspected from different viewing angles.

The project is designed to demonstrate the complete concept of:

```text
2D Medical Images
        ↓
3D Volume
        ↓
3D Brain Surface
        ↓
Interactive Visualization
```

---

# Limitations

The reconstruction quality depends on the characteristics of the input MRI dataset.

Important factors include:

- MRI sequence
- Slice thickness
- In-plane resolution
- Voxel spacing
- Image orientation
- Patient positioning
- Motion artifacts
- Missing slices
- Intensity characteristics
- Quality of brain segmentation

Classical threshold-based segmentation can produce inaccurate boundaries on some MRI datasets.

Therefore, the resulting 3D surface should be considered an approximate reconstruction rather than a ground-truth anatomical model.

---

# Medical / Research Disclaimer

This project is intended for **research, education, experimentation, and visualization**.

It is **not a clinically validated medical device**.

The algorithmic ventricular / CSF estimation is based on image intensity and processing heuristics and should not be interpreted as clinically validated anatomical segmentation.

This software should not be used for:

- Medical diagnosis
- Treatment decisions
- Surgical planning
- Surgical navigation
- Clinical measurements

---

# Future Improvements

Potential future improvements include:

- More robust automatic T1 selection
- Advanced skull stripping
- Deep-learning-based brain segmentation
- Anatomical structure segmentation
- Improved handling of anisotropic MRI
- Multi-planar reconstruction
- Interactive slice viewer
- Web-based 3D visualization
- GPU acceleration
- Automated quality assessment
- Support for additional medical imaging formats

---

# Project Purpose

This project was developed to explore the practical challenges involved in converting 2D medical imaging data into an interactive 3D representation.

The main focus areas are:

```text
Medical Imaging
Computer Vision
3D Reconstruction
Image Processing
DICOM Processing
3D Mesh Generation
Interactive Visualization
```

---

# Author

**Alireza Sobhani**

Computer Vision Engineer | AI Engineer

Areas of interest:

- Computer Vision
- Machine Learning
- Deep Learning
- Medical Imaging
- 3D Reconstruction
- Video AI

---

## License

This repository is provided for research and educational purposes.

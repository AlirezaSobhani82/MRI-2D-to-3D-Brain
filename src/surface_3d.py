import os
import warnings
import tkinter as tk
from tkinter import filedialog

import numpy as np
import pydicom
import pyvista as pv

from scipy.ndimage import zoom
from scipy.ndimage import gaussian_filter
from scipy.ndimage import binary_fill_holes
from scipy.ndimage import binary_closing
from scipy.ndimage import binary_opening
from scipy.ndimage import label

from skimage.filters import threshold_otsu
from skimage.measure import marching_cubes


warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    module="pydicom"
)


TARGET_SPACING = 1.0

OUTPUT_DIR = r"D:\MRI_3D_Project\outputs"


os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


print("=" * 80)
print("MRI 3D BRAIN VIEWER")
print("=" * 80)


print()
print("Select DICOM folder...")


root = tk.Tk()

root.withdraw()

DICOM_DIR = filedialog.askdirectory(
    title="Select DICOM Folder"
)

root.destroy()


if not DICOM_DIR:

    raise RuntimeError(
        "No DICOM folder selected."
    )


print()
print("Selected folder:")
print(DICOM_DIR)


print()
print("Scanning DICOM files...")


all_files = []


for root_dir, dirs, files in os.walk(
    DICOM_DIR
):

    for filename in files:

        path = os.path.join(
            root_dir,
            filename
        )

        if os.path.isfile(path):

            all_files.append(
                path
            )


print(
    "Files found:",
    len(all_files)
)


if len(all_files) == 0:

    raise RuntimeError(
        "No files found in selected folder."
    )


print()
print("Reading DICOM headers...")


series_map = {}


for path in all_files:

    try:

        ds = pydicom.dcmread(
            path,
            stop_before_pixels=True,
            force=True
        )

        if not hasattr(
            ds,
            "SeriesInstanceUID"
        ):
            continue

        if not hasattr(
            ds,
            "SOPInstanceUID"
        ):
            continue

        uid = str(
            ds.SeriesInstanceUID
        )

        if uid not in series_map:

            series_map[uid] = {
                "paths": [],
                "number": -1,
                "description": "",
                "modality": "",
                "rows": 0,
                "columns": 0
            }


        series_map[uid]["paths"].append(
            path
        )


        if (
            series_map[uid]["number"] == -1
            and hasattr(ds, "SeriesNumber")
        ):

            try:

                series_map[uid]["number"] = int(
                    ds.SeriesNumber
                )

            except Exception:

                pass


        if not series_map[uid]["description"]:

            series_map[uid]["description"] = str(
                getattr(
                    ds,
                    "SeriesDescription",
                    ""
                )
            )


        if not series_map[uid]["modality"]:

            series_map[uid]["modality"] = str(
                getattr(
                    ds,
                    "Modality",
                    ""
                )
            )


        if series_map[uid]["rows"] == 0:

            try:

                series_map[uid]["rows"] = int(
                    ds.Rows
                )

                series_map[uid]["columns"] = int(
                    ds.Columns
                )

            except Exception:

                pass


    except Exception:

        continue


print(
    "DICOM series found:",
    len(series_map)
)


if not series_map:

    raise RuntimeError(
        "No DICOM series found."
    )


print()
print("Analyzing series...")


usable_series = []


for uid, info in series_map.items():

    paths = info["paths"]

    valid_paths = []


    for path in paths:

        try:

            ds = pydicom.dcmread(
                path,
                stop_before_pixels=True,
                force=True
            )


            if not hasattr(
                ds,
                "Rows"
            ):

                continue


            if not hasattr(
                ds,
                "Columns"
            ):

                continue


            if not hasattr(
                ds,
                "PixelSpacing"
            ):

                continue


            if not hasattr(
                ds,
                "ImagePositionPatient"
            ):

                continue


            if not hasattr(
                ds,
                "ImageOrientationPatient"
            ):

                continue


            valid_paths.append(
                path
            )


        except Exception:

            continue


    if len(valid_paths) < 5:

        continue


    description = info[
        "description"
    ].lower()


    modality = info[
        "modality"
    ].upper()


    score = 0


    slice_count = len(
        valid_paths
    )


    score += min(
        slice_count,
        40
    )


    if modality == "MR":

        score += 30


    if "t1" in description:

        score += 30


    elif "t2" in description:

        score += 25


    elif "flair" in description:

        score += 20


    elif "brain" in description:

        score += 15


    if info["rows"] >= 256:

        score += 10


    if info["columns"] >= 256:

        score += 10


    if slice_count >= 15:

        score += 15


    if slice_count >= 20:

        score += 10


    usable_series.append(
        {
            "uid": uid,
            "paths": valid_paths,
            "number": info["number"],
            "description": info["description"],
            "modality": modality,
            "rows": info["rows"],
            "columns": info["columns"],
            "score": score
        }
    )


if not usable_series:

    raise RuntimeError(
        "No usable DICOM series found."
    )


usable_series.sort(
    key=lambda x: x["score"],
    reverse=True
)


print()
print(
    "Usable series:",
    len(usable_series)
)


print()
print(
    "Available candidates:"
)


print("-" * 90)


for i, item in enumerate(
    usable_series[:10],
    1
):

    print(
        f"{i:2d} | "
        f"Series {item['number']:4d} | "
        f"{item['description'][:30]:30s} | "
        f"Slices={len(item['paths']):3d} | "
        f"Size={item['rows']}x{item['columns']} | "
        f"Score={item['score']}"
    )


print("-" * 90)


selected = usable_series[0]


print()
print("=" * 80)
print("SELECTED SERIES")
print("=" * 80)


print(
    "Series Number:",
    selected["number"]
)

print(
    "Description:",
    selected["description"]
)

print(
    "Modality:",
    selected["modality"]
)

print(
    "Slices:",
    len(selected["paths"])
)

print(
    "Image Size:",
    selected["rows"],
    "x",
    selected["columns"]
)

print(
    "Score:",
    selected["score"]
)


print()
print("Loading selected DICOM series...")


datasets = []


for path in selected["paths"]:

    try:

        ds = pydicom.dcmread(
            path,
            force=True
        )

        if not hasattr(
            ds,
            "PixelData"
        ):

            continue


        if not hasattr(
            ds,
            "ImagePositionPatient"
        ):

            continue


        if not hasattr(
            ds,
            "ImageOrientationPatient"
        ):

            continue


        datasets.append(
            ds
        )


    except Exception:

        continue


if len(datasets) < 5:

    raise RuntimeError(
        "Selected series does not contain enough readable slices."
    )


first = datasets[0]


orientation = np.array(
    first.ImageOrientationPatient,
    dtype=float
)


row_direction = orientation[:3]

column_direction = orientation[3:]


normal = np.cross(
    row_direction,
    column_direction
)


def position_value(ds):

    position = np.array(
        ds.ImagePositionPatient,
        dtype=float
    )

    return float(
        np.dot(
            position,
            normal
        )
    )


datasets.sort(
    key=position_value
)


print()
print("Slices sorted.")


print()
print("Loading pixel data...")


pixel_data = []

valid_datasets = []


for ds in datasets:

    try:

        image = ds.pixel_array.astype(
            np.float32
        )


        if image.ndim != 2:

            continue


        pixel_data.append(
            image
        )

        valid_datasets.append(
            ds
        )


    except Exception:

        continue


if len(pixel_data) < 5:

    raise RuntimeError(
        "Could not read enough DICOM pixel data."
    )


datasets = valid_datasets


volume = np.stack(
    pixel_data
)


print(
    "Original volume:",
    volume.shape
)


pixel_spacing = np.array(
    datasets[0].PixelSpacing,
    dtype=np.float32
)


positions = np.array(
    [
        position_value(ds)
        for ds in datasets
    ]
)


if len(positions) > 1:

    slice_spacing = float(
        np.median(
            np.abs(
                np.diff(
                    positions
                )
            )
        )
    )

else:

    slice_spacing = float(
        getattr(
            datasets[0],
            "SliceThickness",
            1.0
        )
    )


if slice_spacing <= 0:

    slice_spacing = float(
        getattr(
            datasets[0],
            "SliceThickness",
            1.0
        )
    )


print(
    "Pixel spacing:",
    pixel_spacing
)

print(
    "Slice spacing:",
    slice_spacing
)


print()
print("Normalizing MRI...")


low = np.percentile(
    volume,
    1
)


high = np.percentile(
    volume,
    99
)


volume = np.clip(
    volume,
    low,
    high
)


volume = (
    volume - low
) / (
    high - low + 1e-8
)


print(
    "Intensity normalized."
)


print()
print("Resampling to isotropic voxels...")


zoom_factors = (
    slice_spacing / TARGET_SPACING,
    pixel_spacing[0] / TARGET_SPACING,
    pixel_spacing[1] / TARGET_SPACING
)


volume = zoom(
    volume,
    zoom_factors,
    order=1
)


print(
    "Resampled volume:",
    volume.shape
)


print()
print("Smoothing MRI...")


volume = gaussian_filter(
    volume,
    sigma=1.0
)


print()
print("Creating brain mask...")


threshold = threshold_otsu(
    volume
)


print(
    "Otsu threshold:",
    float(threshold)
)


mask = volume > (
    threshold * 0.55
)


mask = binary_closing(
    mask,
    iterations=3
)


mask = binary_opening(
    mask,
    iterations=2
)


mask = binary_fill_holes(
    mask
)


print(
    "Initial mask percentage:",
    f"{mask.mean() * 100:.2f}%"
)


print()
print("Removing small disconnected regions...")


labeled, count = label(
    mask
)


if count > 0:

    sizes = np.bincount(
        labeled.ravel()
    )

    sizes[0] = 0

    largest_label = int(
        np.argmax(
            sizes
        )
    )

    mask = (
        labeled == largest_label
    )


print(
    "Largest connected component selected."
)


print(
    "Final mask percentage:",
    f"{mask.mean() * 100:.2f}%"
)


print()
print("Applying brain mask...")


brain = volume * mask


print(
    "Brain volume created."
)


print()
print("Extracting 3D brain surface...")


surface_level = 0.20


if brain.max() <= surface_level:

    surface_level = float(
        brain.max() * 0.5
    )


vertices, faces, normals, values = marching_cubes(
    brain,
    level=surface_level,
    spacing=(
        TARGET_SPACING,
        TARGET_SPACING,
        TARGET_SPACING
    )
)


print(
    "Vertices:",
    len(vertices)
)


print(
    "Faces:",
    len(faces)
)


if len(vertices) == 0:

    raise RuntimeError(
        "No 3D brain surface was extracted."
    )


faces_pv = np.column_stack(
    [
        np.full(
            len(faces),
            3
        ),
        faces
    ]
).astype(
    np.int64
)


mesh = pv.PolyData(
    vertices,
    faces_pv
)


print()
print("Cleaning mesh...")


mesh = mesh.clean()


if mesh.n_points == 0:

    raise RuntimeError(
        "Empty 3D brain mesh."
    )


print(
    "Mesh points:",
    mesh.n_points
)


print()
print("Smoothing 3D model...")


mesh = mesh.smooth(
    n_iter=60,
    relaxation_factor=0.01
)


output_mesh = os.path.join(
    OUTPUT_DIR,
    "brain_3d.ply"
)


mesh.save(
    output_mesh
)


print()
print("=" * 80)
print("3D MODEL SAVED")
print("=" * 80)


print(
    output_mesh
)


print()
print("Opening interactive viewer...")


plotter = pv.Plotter(
    window_size=(
        1400,
        900
    )
)


plotter.set_background(
    "black"
)


plotter.add_mesh(
    mesh,
    color="lightgray",
    opacity=0.45,
    smooth_shading=True,
    specular=0.25,
    specular_power=15
)


plotter.add_text(
    "MRI 3D Brain",
    position="upper_left",
    font_size=18
)


plotter.add_text(
    "Left Mouse: Rotate | Wheel: Zoom | Right Mouse: Pan",
    position="lower_left",
    font_size=12
)


plotter.add_axes(
    line_width=2
)


plotter.show()
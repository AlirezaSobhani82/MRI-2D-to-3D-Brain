import os
import warnings
import tkinter as tk
from tkinter import filedialog

import numpy as np
import pydicom
import pyvista as pv

from scipy.ndimage import (
    zoom,
    gaussian_filter,
    binary_fill_holes,
    binary_closing,
    binary_opening,
    distance_transform_edt,
    label,
)

from skimage.filters import threshold_otsu
from skimage.measure import marching_cubes


warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    module="pydicom"
)


OUTPUT_DIR = r"D:\MRI_3D_Project\outputs"

TARGET_SPACING = 1.0

ERODE_RADIUS = 10

TISSUE_FACTOR = 0.85

SURFACE_MODE = "smooth"


def banner(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def select_folder():

    root = tk.Tk()
    root.withdraw()

    folder = filedialog.askdirectory(
        title="Select DICOM Folder"
    )

    root.destroy()

    if not folder:
        raise RuntimeError(
            "No DICOM folder selected."
        )

    return folder


def scan_series(folder):

    series = {}

    for dirpath, _, files in os.walk(folder):

        for name in files:

            path = os.path.join(
                dirpath,
                name
            )

            try:

                ds = pydicom.dcmread(
                    path,
                    stop_before_pixels=True,
                    force=True
                )

                uid = str(
                    ds.SeriesInstanceUID
                )

                needed = (
                    "Rows",
                    "Columns",
                    "PixelSpacing",
                    "ImagePositionPatient",
                    "ImageOrientationPatient"
                )

                if not all(
                    hasattr(ds, a)
                    for a in needed
                ):
                    continue

            except Exception:

                continue


            s = series.setdefault(
                uid,
                {
                    "uid": uid,
                    "paths": [],
                    "number": int(
                        getattr(
                            ds,
                            "SeriesNumber",
                            -1
                        ) or -1
                    ),
                    "description": str(
                        getattr(
                            ds,
                            "SeriesDescription",
                            ""
                        )
                    ),
                    "modality": str(
                        getattr(
                            ds,
                            "Modality",
                            ""
                        )
                    ).upper(),
                    "rows": int(ds.Rows),
                    "columns": int(ds.Columns),
                }
            )


            s["paths"].append(
                path
            )


    usable = [
        s
        for s in series.values()
        if len(s["paths"]) >= 5
    ]


    if not usable:

        raise RuntimeError(
            "No usable DICOM series found."
        )


    for s in usable:

        d = s["description"].lower()

        score = min(
            len(s["paths"]),
            60
        )

        score += (
            30
            if s["modality"] == "MR"
            else 0
        )


        if "t1" in d:

            score += 30

        elif "t2" in d:

            score += 25

        elif "flair" in d:

            score += 20

        elif "brain" in d:

            score += 15


        score += (
            10
            if s["rows"] >= 256
            else 0
        )

        score += (
            10
            if s["columns"] >= 256
            else 0
        )


        s["score"] = score


    usable.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return usable


def choose_series(candidates):

    print("\nAvailable series:")

    print("-" * 90)


    for i, s in enumerate(
        candidates[:10],
        1
    ):

        print(
            f"{i:2d} | "
            f"Series {s['number']:4d} | "
            f"{s['description'][:30]:30s} | "
            f"Slices={len(s['paths']):3d} | "
            f"Size={s['rows']}x{s['columns']} | "
            f"Score={s['score']}"
        )


    print("-" * 90)


    choice = input(
        "Choose series number (Enter = best match [1]): "
    ).strip()


    index = 0


    if (
        choice.isdigit()
        and
        1 <= int(choice)
        <= min(10, len(candidates))
    ):

        index = int(choice) - 1


    return candidates[index]


def load_volume(series):

    datasets = []


    for path in series["paths"]:

        try:

            ds = pydicom.dcmread(
                path,
                force=True
            )

            _ = ds.pixel_array

            datasets.append(ds)

        except Exception:

            continue


    if len(datasets) < 5:

        raise RuntimeError(
            "Not enough readable slices in the selected series."
        )


    orientation = np.array(
        datasets[0].ImageOrientationPatient,
        dtype=float
    )


    normal = np.cross(
        orientation[:3],
        orientation[3:]
    )


    def pos(ds):

        return float(
            np.dot(
                np.array(
                    ds.ImagePositionPatient,
                    dtype=float
                ),
                normal
            )
        )


    datasets.sort(
        key=pos
    )


    slices = []


    for ds in datasets:

        img = ds.pixel_array.astype(
            np.float32
        )


        slope = float(
            getattr(
                ds,
                "RescaleSlope",
                1.0
            )
        )


        intercept = float(
            getattr(
                ds,
                "RescaleIntercept",
                0.0
            )
        )


        slices.append(
            img * slope + intercept
        )


    volume = np.stack(
        slices
    )


    positions = np.array(
        [
            pos(ds)
            for ds in datasets
        ]
    )


    slice_spacing = float(
        np.median(
            np.abs(
                np.diff(
                    positions
                )
            )
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


    pixel_spacing = np.array(
        datasets[0].PixelSpacing,
        dtype=np.float32
    )


    print(
        "Original volume :",
        volume.shape
    )

    print(
        "Pixel spacing   :",
        pixel_spacing
    )

    print(
        "Slice spacing   :",
        slice_spacing
    )


    return (
        volume,
        pixel_spacing,
        slice_spacing
    )


def preprocess(
    volume,
    pixel_spacing,
    slice_spacing
):

    low, high = np.percentile(
        volume,
        (1, 99)
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


    factors = (
        slice_spacing / TARGET_SPACING,
        pixel_spacing[0] / TARGET_SPACING,
        pixel_spacing[1] / TARGET_SPACING,
    )


    volume = zoom(
        volume,
        factors,
        order=1
    )


    volume = gaussian_filter(
        volume,
        sigma=1.0
    )


    print(
        "Isotropic volume:",
        volume.shape
    )


    return volume


def largest_component(binary):

    labeled, count = label(
        binary
    )


    if count == 0:

        return None


    sizes = np.bincount(
        labeled.ravel()
    )


    sizes[0] = 0


    return (
        labeled
        ==
        int(
            np.argmax(sizes)
        )
    )


def extract_brain_mask(volume):

    threshold = threshold_otsu(
        volume
    )


    print(
        "Otsu threshold:",
        float(threshold)
    )


    tissue = volume > (
        threshold * TISSUE_FACTOR
    )


    tissue = binary_opening(
        tissue,
        iterations=2
    )


    tissue = binary_fill_holes(
        tissue
    )


    radius = (
        ERODE_RADIUS
        /
        TARGET_SPACING
    )


    core = (
        distance_transform_edt(tissue)
        >
        radius
    )


    core = largest_component(
        core
    )


    if core is None:

        raise RuntimeError(
            "Brain core not found. Lower ERODE_RADIUS."
        )


    grown = (
        distance_transform_edt(~core)
        <=
        radius
    )


    mask = (
        grown
        &
        tissue
    )


    mask = binary_closing(
        mask,
        iterations=3
    )


    mask = binary_fill_holes(
        mask
    )


    mask = largest_component(
        mask
    )


    print(
        f"Brain mask: {mask.mean() * 100:.2f}% of volume"
    )


    return mask


def build_mesh(
    volume,
    mask
):

    if SURFACE_MODE == "detailed":

        field = gaussian_filter(
            volume * mask,
            sigma=0.8
        )


        level = float(
            np.percentile(
                field[mask],
                35
            )
        )

    else:

        field = gaussian_filter(
            mask.astype(
                np.float32
            ),
            sigma=1.5
        )


        level = 0.5


    verts, faces, _, _ = marching_cubes(
        field,
        level=level,
        spacing=(
            TARGET_SPACING,
            TARGET_SPACING,
            TARGET_SPACING
        )
    )


    print(
        "Vertices:",
        len(verts),
        "| Faces:",
        len(faces)
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
        verts,
        faces_pv
    ).clean()


    try:

        mesh = mesh.connectivity(
            extraction_mode="largest"
        )

        mesh = mesh.extract_geometry()

    except Exception:

        pass


    try:

        mesh = mesh.smooth_taubin(
            n_iter=40,
            pass_band=0.1
        )

    except Exception:

        mesh = mesh.smooth(
            n_iter=60,
            relaxation_factor=0.01
        )


    return mesh.compute_normals(
        auto_orient_normals=True
    )


def show_mesh(mesh):

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
        color="white",
        opacity=0.38,
        smooth_shading=True,
        specular=0.45,
        specular_power=25,
        ambient=0.25,
        diffuse=0.75,
    )


    plotter.add_text(
        "MRI 3D Brain",
        position="upper_left",
        font_size=18
    )


    plotter.add_text(
        "Left: Rotate | Wheel: Zoom | Right: Pan",
        position="lower_left",
        font_size=12
    )


    plotter.add_axes(
        line_width=2
    )


    plotter.show()


def main():

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )


    banner(
        "MRI 3D BRAIN VIEWER"
    )


    folder = select_folder()


    print(
        "Selected folder:",
        folder
    )


    print(
        "\nScanning DICOM series..."
    )


    candidates = scan_series(
        folder
    )


    series = choose_series(
        candidates
    )


    banner(
        "SELECTED SERIES"
    )


    print(
        "Series :",
        series["number"],
        "-",
        series["description"]
    )


    print(
        "Slices :",
        len(series["paths"])
    )


    print(
        "\nBuilding volume..."
    )


    (
        volume,
        pixel_spacing,
        slice_spacing
    ) = load_volume(
        series
    )


    volume = preprocess(
        volume,
        pixel_spacing,
        slice_spacing
    )


    print(
        "\nRemoving skull / scalp / neck..."
    )


    mask = extract_brain_mask(
        volume
    )


    print(
        "\nBuilding 3D brain surface..."
    )


    mesh = build_mesh(
        volume,
        mask
    )


    ply_path = os.path.join(
        OUTPUT_DIR,
        "brain_3d.ply"
    )


    stl_path = os.path.join(
        OUTPUT_DIR,
        "brain_3d.stl"
    )


    mesh.save(
        ply_path
    )


    mesh.save(
        stl_path
    )


    banner(
        "3D MODEL SAVED"
    )


    print(
        ply_path
    )


    print(
        stl_path
    )


    print(
        "\nOpening viewer..."
    )


    show_mesh(
        mesh
    )


if __name__ == "__main__":

    main()
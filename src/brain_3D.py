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
from skimage.morphology import remove_small_objects


warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    module="pydicom"
)


OUTPUT_DIR = r"D:\MRI_3D_Project\outputs"

TARGET_SPACING = 1.0

ERODE_RADIUS = 10

TISSUE_FACTOR = 0.85

MAX_MESH_POINTS = 500000

SURFACE_SMOOTHING = 10

BRAIN_COLOR = "white"

VENTRICLE_COLOR = "cyan"

BACKGROUND_COLOR = "black"

BRAIN_OPACITY = 0.25

VENTRICLE_OPACITY = 0.90

MIN_VENTRICLE_SIZE = 2000

VENTRICLE_PERCENTILE = 12


def banner(title):
    print()
    print("=" * 80)
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

                required = (
                    "Rows",
                    "Columns",
                    "PixelSpacing",
                    "ImagePositionPatient",
                    "ImageOrientationPatient"
                )

                if not hasattr(
                    ds,
                    "SeriesInstanceUID"
                ):
                    continue

                if not all(
                    hasattr(ds, item)
                    for item in required
                ):
                    continue

                uid = str(
                    ds.SeriesInstanceUID
                )

            except Exception:
                continue

            if uid not in series:

                series[uid] = {

                    "uid": uid,

                    "paths": [],

                    "number": int(
                        getattr(
                            ds,
                            "SeriesNumber",
                            -1
                        )
                        or -1
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

                    "rows": int(
                        ds.Rows
                    ),

                    "columns": int(
                        ds.Columns
                    )
                }

            series[uid]["paths"].append(
                path
            )

    usable = [
        item
        for item in series.values()
        if len(item["paths"]) >= 5
    ]

    if not usable:

        raise RuntimeError(
            "No usable DICOM series found."
        )

    for item in usable:

        description = (
            item["description"]
            .lower()
        )

        score = min(
            len(item["paths"]),
            60
        )

        if item["modality"] == "MR":
            score += 30

        if "t1" in description:
            score += 30

        elif "t2" in description:
            score += 25

        elif "flair" in description:
            score += 20

        elif "brain" in description:
            score += 15

        if item["rows"] >= 256:
            score += 10

        if item["columns"] >= 256:
            score += 10

        item["score"] = score

    usable.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return usable


def choose_series(candidates):

    print()
    print("Available series:")
    print("-" * 110)

    for index, item in enumerate(
        candidates[:10],
        1
    ):

        print(
            f"{index:2d} | "
            f"Series {item['number']:4d} | "
            f"{item['description'][:35]:35s} | "
            f"Slices={len(item['paths']):3d} | "
            f"Size={item['rows']}x{item['columns']} | "
            f"Modality={item['modality']:2s} | "
            f"Score={item['score']}"
        )

    print("-" * 110)

    choice = input(
        "Choose series number (Enter = best match [1]): "
    ).strip()

    selected_index = 0

    if (
        choice.isdigit()
        and 1 <= int(choice)
        <= min(10, len(candidates))
    ):

        selected_index = (
            int(choice) - 1
        )

    return candidates[
        selected_index
    ]


def load_volume(series):

    datasets = []

    print()
    print("Reading DICOM slices...")

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
            "Not enough readable slices."
        )

    orientation = np.asarray(
        datasets[0].ImageOrientationPatient,
        dtype=np.float64
    )

    row_direction = orientation[:3]

    column_direction = orientation[3:]

    normal = np.cross(
        row_direction,
        column_direction
    )

    def position_value(ds):

        position = np.asarray(
            ds.ImagePositionPatient,
            dtype=np.float64
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

    images = []

    for ds in datasets:

        image = ds.pixel_array.astype(
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

        image = (
            image * slope
            + intercept
        )

        images.append(image)

    volume = np.stack(
        images
    )

    positions = np.asarray(
        [
            position_value(ds)
            for ds in datasets
        ]
    )

    if len(positions) > 1:

        differences = np.abs(
            np.diff(positions)
        )

        differences = differences[
            differences > 1e-6
        ]

    else:

        differences = np.array([])

    if len(differences) > 0:

        slice_spacing = float(
            np.median(
                differences
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

    pixel_spacing = np.asarray(
        datasets[0].PixelSpacing,
        dtype=np.float32
    )

    print(
        "Original volume:",
        volume.shape
    )

    print(
        "Pixel spacing:",
        pixel_spacing
    )

    print(
        "Slice spacing:",
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

    print()
    print("Normalizing MRI...")

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

    print(
        "Intensity normalized."
    )

    print()
    print(
        "Resampling to 1mm isotropic..."
    )

    factors = (

        float(slice_spacing)
        / TARGET_SPACING,

        float(pixel_spacing[0])
        / TARGET_SPACING,

        float(pixel_spacing[1])
        / TARGET_SPACING
    )

    print(
        "Zoom factors:",
        factors
    )

    volume = zoom(
        volume,
        factors,
        order=1
    )

    print(
        "1mm isotropic volume:",
        volume.shape
    )

    print()
    print(
        "Applying detail-preserving smoothing..."
    )

    volume = gaussian_filter(
        volume,
        sigma=0.55
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

    largest = int(
        np.argmax(sizes)
    )

    return labeled == largest


def extract_brain_mask(volume):

    print()
    print(
        "Creating brain mask..."
    )

    threshold = threshold_otsu(
        volume
    )

    print(
        "Otsu threshold:",
        float(threshold)
    )

    tissue = (
        volume
        > threshold * TISSUE_FACTOR
    )

    tissue = binary_opening(
        tissue,
        iterations=2
    )

    tissue = binary_closing(
        tissue,
        iterations=2
    )

    tissue = binary_fill_holes(
        tissue
    )

    print(
        "Finding brain core..."
    )

    radius = (
        ERODE_RADIUS
        / TARGET_SPACING
    )

    distance = distance_transform_edt(
        tissue
    )

    core = largest_component(
        distance > radius
    )

    if core is None:

        raise RuntimeError(
            "Brain core not found. "
            "Try reducing ERODE_RADIUS."
        )

    grown = (
        distance_transform_edt(
            ~core
        )
        <= radius
    )

    mask = grown & tissue

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

    if mask is None:

        raise RuntimeError(
            "Final brain mask is empty."
        )

    print(
        f"Brain mask: "
        f"{mask.mean() * 100:.2f}% "
        f"of volume"
    )

    print(
        "Brain voxels:",
        int(mask.sum())
    )

    return mask


def segment_ventricles(
    volume,
    brain_mask
):

    print()
    print(
        "Segmenting ventricles..."
    )

    values = volume[
        brain_mask
    ]

    if len(values) == 0:

        return None

    threshold = np.percentile(
        values,
        VENTRICLE_PERCENTILE
    )

    print(
        f"CSF threshold: "
        f"{threshold:.4f}"
    )

    ventricles = (
        volume < threshold
    ) & brain_mask

    ventricles = binary_opening(
        ventricles,
        iterations=1
    )

    ventricles = binary_closing(
        ventricles,
        iterations=2
    )

    ventricles = remove_small_objects(
        ventricles,
        min_size=MIN_VENTRICLE_SIZE
    )

    if (
        ventricles.sum()
        < MIN_VENTRICLE_SIZE
    ):

        print(
            "Ventricle structure "
            "could not be extracted."
        )

        return None

    print(
        "Ventricle voxels:",
        int(ventricles.sum())
    )

    print(
        f"Ventricle volume: "
        f"{ventricles.sum() / 1000:.2f} cm3"
    )

    return ventricles


def geometry_only(mesh):

    if (
        mesh is None
        or mesh.n_points == 0
    ):

        return None

    try:

        mesh = mesh.extract_surface(
            algorithm=None,
            pass_pointid=False,
            pass_cellid=False
        )

    except Exception:

        pass

    points = np.asarray(
        mesh.points
    ).copy()

    faces = np.asarray(
        mesh.faces
    ).copy()

    if (
        len(points) == 0
        or len(faces) == 0
    ):

        return None

    mesh = pv.PolyData(
        points,
        faces
    )

    mesh = mesh.clean(
        absolute=True,
        tolerance=0.0
    )

    mesh = mesh.triangulate()

    points = np.asarray(
        mesh.points
    ).copy()

    faces = np.asarray(
        mesh.faces
    ).copy()

    return pv.PolyData(
        points,
        faces
    )


def safe_decimate(
    mesh,
    max_points
):

    if mesh is None:

        return None

    if (
        mesh.n_points
        <= max_points
    ):

        return mesh

    print()
    print(
        "Reducing mesh complexity..."
    )

    mesh = geometry_only(
        mesh
    )

    if mesh is None:

        return None

    if not mesh.is_all_triangles:

        mesh = mesh.triangulate()

        mesh = geometry_only(
            mesh
        )

    if (
        mesh is None
        or not mesh.is_all_triangles
    ):

        print(
            "Decimation skipped."
        )

        return mesh

    reduction = (
        1.0
        - max_points
        / float(mesh.n_points)
    )

    reduction = max(
        0.0,
        min(
            reduction,
            0.75
        )
    )

    print(
        "Reduction:",
        f"{reduction * 100:.1f}%"
    )

    try:

        mesh = mesh.decimate_pro(
            reduction=reduction,
            preserve_topology=True,
            boundary_vertex_deletion=False,
            inplace=False
        )

        mesh = geometry_only(
            mesh
        )

        if mesh is not None:

            print(
                "Decimated mesh points:",
                mesh.n_points
            )

        return mesh

    except Exception as error:

        print(
            "Decimation failed safely:",
            error
        )

        return mesh


def build_brain_mesh(
    volume,
    mask
):

    print()
    print(
        "Extracting detailed brain surface..."
    )

    field = gaussian_filter(
        volume * mask,
        sigma=0.50
    )

    values = field[
        mask
    ]

    if len(values) == 0:

        raise RuntimeError(
            "No valid brain intensity values."
        )

    level = float(
        np.percentile(
            values,
            35
        )
    )

    print(
        "Surface intensity level:",
        level
    )

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
        "Raw vertices:",
        len(verts)
    )

    print(
        "Raw faces:",
        len(faces)
    )

    faces_pv = np.column_stack(
        [
            np.full(
                len(faces),
                3,
                dtype=np.int32
            ),
            faces.astype(
                np.int32
            )
        ]
    )

    mesh = pv.PolyData(
        verts,
        faces_pv
    )

    mesh = geometry_only(
        mesh
    )

    if mesh is None:

        raise RuntimeError(
            "Brain mesh creation failed."
        )

    print(
        "Cleaned mesh points:",
        mesh.n_points
    )

    mesh = safe_decimate(
        mesh,
        MAX_MESH_POINTS
    )

    if mesh is None:

        raise RuntimeError(
            "Brain mesh decimation failed."
        )

    print(
        "Final mesh points:",
        mesh.n_points
    )

    print(
        "Final mesh cells:",
        mesh.n_cells
    )

    print()
    print(
        "Applying controlled mesh smoothing..."
    )

    try:

        mesh = mesh.smooth_taubin(
            n_iter=SURFACE_SMOOTHING,
            pass_band=0.08
        )

    except Exception:

        try:

            mesh = mesh.smooth(
                n_iter=12,
                relaxation_factor=0.01
            )

        except Exception:

            pass

    mesh = geometry_only(
        mesh
    )

    if mesh is None:

        raise RuntimeError(
            "Brain mesh became invalid."
        )

    mesh = mesh.compute_normals(
        cell_normals=True,
        point_normals=True,
        auto_orient_normals=True,
        consistent_normals=True,
        inplace=False
    )

    mesh = geometry_only(
        mesh
    )

    return mesh


def build_ventricle_mesh(
    mask
):

    if (
        mask is None
        or mask.sum() == 0
    ):

        return None

    field = (
        distance_transform_edt(
            mask
        )
        .astype(np.float32)
    )

    field *= mask

    field = gaussian_filter(
        field,
        sigma=0.45
    )

    values = field[
        mask
    ]

    if len(values) == 0:

        return None

    level = float(
        np.percentile(
            values,
            50
        )
    )

    try:

        verts, faces, _, _ = marching_cubes(
            field,
            level=level,
            spacing=(
                TARGET_SPACING,
                TARGET_SPACING,
                TARGET_SPACING
            )
        )

    except Exception as error:

        print(
            "Ventricle mesh failed:",
            error
        )

        return None

    faces_pv = np.column_stack(
        [
            np.full(
                len(faces),
                3,
                dtype=np.int32
            ),
            faces.astype(
                np.int32
            )
        ]
    )

    mesh = pv.PolyData(
        verts,
        faces_pv
    )

    mesh = geometry_only(
        mesh
    )

    if mesh is None:

        return None

    mesh = safe_decimate(
        mesh,
        150000
    )

    if mesh is None:

        return None

    try:

        mesh = mesh.smooth_taubin(
            n_iter=6,
            pass_band=0.08
        )

    except Exception:

        pass

    return geometry_only(
        mesh
    )


def save_mesh(
    mesh,
    path
):

    if mesh is None:

        return False

    mesh = geometry_only(
        mesh
    )

    if mesh is None:

        return False

    mesh.save(
        path
    )

    return True


def save_all_meshes(
    brain_mesh,
    ventricles_mesh=None
):

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    print()
    print(
        "Saving 3D models..."
    )

    models = [

        (
            brain_mesh,
            "brain_3d.ply",
            "Brain PLY"
        ),

        (
            brain_mesh,
            "brain_3d.stl",
            "Brain STL"
        ),

        (
            ventricles_mesh,
            "ventricles_3d.ply",
            "Ventricles PLY"
        ),

        (
            ventricles_mesh,
            "ventricles_3d.stl",
            "Ventricles STL"
        )
    ]

    for mesh, filename, label_text in models:

        if mesh is None:

            continue

        path = os.path.join(
            OUTPUT_DIR,
            filename
        )

        if save_mesh(
            mesh,
            path
        ):

            print(
                f"{label_text}: {path}"
            )


def save_clinical_outputs(
    volume,
    brain_mask,
    ventricles_mask,
    output_dir,
    series
):

    print()
    print(
        "Saving NIfTI outputs..."
    )

    try:

        import nibabel as nib

        affine = np.eye(
            4,
            dtype=np.float32
        )

        affine[0, 0] = TARGET_SPACING
        affine[1, 1] = TARGET_SPACING
        affine[2, 2] = TARGET_SPACING

        nib.save(

            nib.Nifti1Image(
                brain_mask.astype(
                    np.uint8
                ),
                affine
            ),

            os.path.join(
                output_dir,
                "brain_mask.nii.gz"
            )
        )

        nib.save(

            nib.Nifti1Image(
                volume.astype(
                    np.float32
                ),
                affine
            ),

            os.path.join(
                output_dir,
                "volume_normalized.nii.gz"
            )
        )

        if ventricles_mask is not None:

            nib.save(

                nib.Nifti1Image(
                    ventricles_mask.astype(
                        np.uint8
                    ),
                    affine
                ),

                os.path.join(
                    output_dir,
                    "ventricles_mask.nii.gz"
                )
            )

        print(
            "NIfTI files saved."
        )

    except ImportError:

        print(
            "nibabel not installed; "
            "skipping NIfTI output."
        )

    report_path = os.path.join(
        output_dir,
        "mri_3d_report.txt"
    )

    with open(
        report_path,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "MRI 3D BRAIN RECONSTRUCTION REPORT\n"
        )

        f.write(
            "=" * 60
            + "\n\n"
        )

        f.write(
            f"Modality: "
            f"{series['modality']}\n"
        )

        f.write(
            f"Series Number: "
            f"{series['number']}\n"
        )

        f.write(
            f"Series Description: "
            f"{series['description']}\n"
        )

        f.write(
            f"Slices: "
            f"{len(series['paths'])}\n"
        )

        f.write(
            f"Voxel spacing: "
            f"{TARGET_SPACING} x "
            f"{TARGET_SPACING} x "
            f"{TARGET_SPACING} mm\n"
        )

        f.write(
            f"Volume shape: "
            f"{volume.shape}\n\n"
        )

        f.write(
            "--- BRAIN ---\n"
        )

        f.write(
            f"Brain voxels: "
            f"{int(brain_mask.sum())}\n"
        )

        f.write(
            f"Brain volume: "
            f"{brain_mask.sum() / 1000:.2f} cm3\n"
        )

        f.write(
            f"Brain coverage: "
            f"{brain_mask.mean() * 100:.2f}%\n\n"
        )

        if ventricles_mask is not None:

            f.write(
                "--- VENTRICLES / CSF ESTIMATE ---\n"
            )

            f.write(
                f"Ventricle voxels: "
                f"{int(ventricles_mask.sum())}\n"
            )

            f.write(
                f"Estimated volume: "
                f"{ventricles_mask.sum() / 1000:.2f} cm3\n\n"
            )

        f.write(
            "--- PROCESSING ---\n"
        )

        f.write(
            "3D reconstruction performed at "
            "1 mm isotropic target spacing.\n"
        )

        f.write(
            "Ventricle visualization is an "
            "algorithmic intensity-based estimate.\n"
        )

        f.write(
            "No tumor diagnosis or lesion diagnosis "
            "is performed by this demo.\n\n"
        )

        f.write(
            "--- IMPORTANT ---\n"
        )

        f.write(
            "This software is a research/demo "
            "visualization pipeline.\n"
        )

        f.write(
            "It is not a clinically validated "
            "diagnostic or surgical navigation system.\n"
        )

    print(
        f"Report saved: {report_path}"
    )


def show_surgical_viewer(
    brain_mesh,
    ventricles_mesh=None,
    series=None,
    volume_shape=None
):

    print()
    print(
        "Opening professional 3D viewer..."
    )

    plotter = pv.Plotter(
        window_size=(
            1600,
            1000
        )
    )

    plotter.set_background(
        BACKGROUND_COLOR
    )

    brain_actor = plotter.add_mesh(

        brain_mesh,

        color=BRAIN_COLOR,

        opacity=BRAIN_OPACITY,

        smooth_shading=True,

        specular=0.35,

        specular_power=20,

        ambient=0.30,

        diffuse=0.70,

        name="brain"
    )

    ventricle_actor = None

    if ventricles_mesh is not None:

        ventricle_actor = plotter.add_mesh(

            ventricles_mesh,

            color=VENTRICLE_COLOR,

            opacity=VENTRICLE_OPACITY,

            smooth_shading=True,

            specular=0.55,

            specular_power=25,

            name="ventricles"
        )

    plotter.add_text(

        "MRI 3D BRAIN RECONSTRUCTION",

        position="upper_left",

        font_size=20
    )

    plotter.add_text(

        "Research Visualization | 1 mm Isotropic",

        position=(0.02, 0.925),

        font_size=11
    )

    if series is not None:

        modality = series[
            "modality"
        ]

        series_number = series[
            "number"
        ]

        description = series[
            "description"
        ]

        slices = len(
            series["paths"]
        )

        info = (

            f"Modality      : {modality}\n"
            f"Series        : {series_number}\n"
            f"Sequence      : {description}\n"
            f"Slices        : {slices}\n"
            f"Voxel Size    : 1.0 x 1.0 x 1.0 mm\n"
            f"Volume Shape  : {volume_shape}\n"
            f"\n"
            f"White  : Brain Surface\n"
            f"Cyan   : Ventricular / CSF Estimate"
        )

        plotter.add_text(

            info,

            position="upper_right",

            font_size=10
        )

    plotter.add_text(

        "1 Brain   |   2 Ventricles   |   O Transparency   |   R Reset   |   Q Exit",

        position="lower_left",

        font_size=10
    )

    plotter.add_text(

        "Research / Demonstration Only",

        position="lower_right",

        font_size=10
    )

    def toggle_brain():

        current = (
            brain_actor
            .GetProperty()
            .GetOpacity()
        )

        if current < 0.5:

            new_opacity = 1.0

        else:

            new_opacity = BRAIN_OPACITY

        brain_actor.GetProperty().SetOpacity(
            new_opacity
        )

        plotter.render()

    def toggle_ventricles():

        if ventricle_actor is None:

            return

        current = (
            ventricle_actor
            .GetProperty()
            .GetOpacity()
        )

        if current > 0.5:

            new_opacity = 0.0

        else:

            new_opacity = VENTRICLE_OPACITY

        ventricle_actor.GetProperty().SetOpacity(
            new_opacity
        )

        plotter.render()

    def toggle_transparency():

        current = (
            brain_actor
            .GetProperty()
            .GetOpacity()
        )

        if current > 0.15:

            brain_actor.GetProperty().SetOpacity(
                0.05
            )

        else:

            brain_actor.GetProperty().SetOpacity(
                BRAIN_OPACITY
            )

        plotter.render()

    def reset_view():

        plotter.reset_camera()

        plotter.render()

    plotter.add_key_event(
        "1",
        toggle_brain
    )

    plotter.add_key_event(
        "2",
        toggle_ventricles
    )

    plotter.add_key_event(
        "o",
        toggle_transparency
    )

    plotter.add_key_event(
        "r",
        reset_view
    )

    plotter.add_key_event(
        "q",
        plotter.close
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
        "MRI 3D BRAIN RECONSTRUCTION - "
        "1MM ISOTROPIC DEMO"
    )

    folder = select_folder()

    print()
    print(
        "Selected folder:",
        folder
    )

    print()
    print(
        "Scanning DICOM series..."
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
        "Series:",
        series["number"]
    )

    print(
        "Description:",
        series["description"]
    )

    print(
        "Modality:",
        series["modality"]
    )

    print(
        "Slices:",
        len(series["paths"])
    )

    print()
    print(
        "Building 3D volume..."
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

    print()
    print(
        "Segmenting brain..."
    )

    brain_mask = extract_brain_mask(
        volume
    )

    ventricles_mask = segment_ventricles(
        volume,
        brain_mask
    )

    print()
    print(
        "Building 3D surfaces..."
    )

    print()
    print(
        "[1/2] Brain mesh..."
    )

    brain_mesh = build_brain_mesh(
        volume,
        brain_mask
    )

    print()
    print(
        "[2/2] Ventricles mesh..."
    )

    ventricles_mesh = build_ventricle_mesh(
        ventricles_mask
    )

    save_all_meshes(
        brain_mesh,
        ventricles_mesh
    )

    save_clinical_outputs(
        volume,
        brain_mask,
        ventricles_mask,
        OUTPUT_DIR,
        series
    )

    banner(
        "3D RECONSTRUCTION READY"
    )

    print()
    print(
        "Output:"
    )

    print(
        "  Brain 3D surface"
    )

    print(
        "  Ventricular / CSF estimate"
    )

    print(
        "  1 mm isotropic reconstruction"
    )

    print(
        "  PLY / STL / NIfTI outputs"
    )

    print()
    print(
        "No tumor diagnosis is performed."
    )

    print(
        "This is a research/demo visualization."
    )

    print()
    print(
        "Viewer Controls:"
    )

    print(
        "  Left Mouse  : Rotate"
    )

    print(
        "  Wheel       : Zoom"
    )

    print(
        "  Right Mouse : Pan"
    )

    print(
        "  Key 1       : Toggle Brain"
    )

    print(
        "  Key 2       : Toggle Ventricles"
    )

    print(
        "  Key O       : Transparency"
    )

    print(
        "  Key R       : Reset Camera"
    )

    print(
        "  Key Q       : Exit"
    )

    print()

    show_surgical_viewer(

        brain_mesh,

        ventricles_mesh=ventricles_mesh,

        series=series,

        volume_shape=volume.shape
    )


if __name__ == "__main__":

    main()

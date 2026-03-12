from pathlib import Path
from datetime import datetime

from config import GridConfig
from errors import DirectoryNotFoundError

def build_output_path(output_dir: Path, grid_config: GridConfig) -> Path:
    time = datetime.now().strftime(format="%Y_%m_%d %H_%M_%S")
    filename = "{}_points_{}_{}_{}.shp".format(
        grid_config.n_grid_points,
        grid_config.margin_from_points,
        grid_config.margin_fn.__name__,
        time
    )
    return output_dir / filename

def clean_path_string(path: str) -> Path:
    path = path.strip('"').strip("'").strip()
    return Path(path)

def validate_output_dir(output_dir_str: str) -> Path:
    output_dir = clean_path_string(output_dir_str)
    if not output_dir.exists():
        raise DirectoryNotFoundError(output_dir)
    if not output_dir.is_dir():
        raise ValueError(f"{output_dir} no es un directorio válido")
    return output_dir

def validate_path_input(path_as_str: str):
    points_as_path = clean_path_string(path_as_str)
    if not points_as_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo en {points_as_path}")
    return points_as_path

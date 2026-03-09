from pathlib import Path
from geopandas import read_file, GeoDataFrame

from typing import Generator

def get_shp_files(path: str):
    dir = Path(path)
    if not dir.is_dir():
        raise TypeError("El path no es un directorio")
    return dir.rglob("*.shp")

def read_shp_files(files: Generator[Path, None, None]):
    return [read_file(file) for file in files]

def read_shp_file(file: Path):
    if not file.is_file():
        raise TypeError("El path no es un archivo")
    if file.suffix != ".shp":
        raise TypeError("El archivo no es un archivo shape")
    return read_file(file)

def read_points_from_gpkg(file: Path, layer: str) -> GeoDataFrame:
    if not file.is_file():
        raise TypeError("El path no es un archivo")
    if file.suffix != ".shp":
        raise TypeError("El archivo no es un archivo gpkg")
    return read_file(
        filename=file,
        layer=layer,
        )


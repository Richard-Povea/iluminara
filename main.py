from model.model import Scene, Grid, get_skyglow
from model.luminica import ModifiedLightSourceAlbersDuricoe,cd_per_m2_to_sqm_zotti
from geo import (
    array2points, grid_range_from_geodf, 
    flat_margin, percentage_margin
    )
from state import State, Event, machine, FileType, get_file_type

from typing import Literal
from pathlib import Path
from numpy import pi, ndarray
from datetime import datetime
from geopandas import read_file, list_layers, GeoDataFrame
from geopandas.array import GeometryArray
from shapely import Point
from functools import lru_cache
from abc import ABC, abstractmethod

# Current Work Constants
POINTS_PATH = Path(
    r"C:\Users\richa\Ruido Ambiental SpA\Proyectos - 9484 - Luminico Arena Generación\QGIS\luminarias.gpkg")
RESOULTS_PATH = Path(
    r"C:\Users\richa\Ruido Ambiental SpA\Proyectos - 9484 - Luminico Arena Generación\QGIS\Shapes\SHPs Adenda 1 - Modelo")
LAYER = "construccion_monoparte" # None para leer la capa por defecto del shapefile, o el nombre de la capa a leer
FILTER_COLUMN = "fase"
FILTER_BY = None

N_GRID_POINTS = 2_000
MARGIN_FROM_POINTS = 5_000 # [%] o [m]
MARGIN_FN: Literal["Percentage", "Flat"] = "Flat"
MARGIN_FN_DICT = {
    "Percentage": percentage_margin,
    "Flat": flat_margin
}

# Model Constants
BACKGROUND_SQM = 22.02
NATURAL_BACKGROUND_SKYGLOW = 2e-4
DEFAULT_ATTRIBUTE_NAMES = {
    "power": "Potencia",
    "eficiency": "eficiencia",
}
# ATLANTIS PRO II 100 W, 160 Lm/W
DEFAULT_LIGTH_POWER = 100
DEFAULT_LIGTH_EFICIENCY = 160

def points_to_geodf(points: GeometryArray, sqm:ndarray):
    d = {"Value":sqm.flat, "geometry":points}
    geo_df = GeoDataFrame(d)
    return geo_df

def export(geo_df: GeoDataFrame, output_path: Path|None=None):
    if output_path == None:
        output_dir = RESOULTS_PATH
        time = datetime.now().strftime(format="%Y_%m_%d %H_%M_%S")
        output_filename = f"{N_GRID_POINTS}_points_{MARGIN_FROM_POINTS}_per_margin"
        name=f"{output_filename}_{time}.shp"
        output_path = output_dir / name
    geo_df.to_file(output_path)
    return output_path

def add_light_source(scene: Scene, x:float, y:float, light_flux:int):
    light_source = ModifiedLightSourceAlbersDuricoe(
        x, 
        y, 
        light_flux)
    scene.add_light_source(light_source)

def get_sqm(scene: Scene, grid:Grid):
    skyglow_albers_duricoe = get_skyglow(scene, grid, omega=2*pi)
    skyglow_albers_duricoe += NATURAL_BACKGROUND_SKYGLOW
    # Sky Quality Magnitude (SQM)
    sqm = cd_per_m2_to_sqm_zotti(skyglow_albers_duricoe)
    
    sqm[sqm > BACKGROUND_SQM] = BACKGROUND_SQM
    return sqm

def build_sqm_one_ligth(
        scene: Scene, 
        grid: Grid, 
        ligths: GeoDataFrame,
        electric_power: int=DEFAULT_LIGTH_POWER,
        luminosity_efficiency: int=DEFAULT_LIGTH_EFICIENCY):
    ## AÑADIR FUENTES LUMÍNICAS AL MODELO
    light_flux = electric_power * luminosity_efficiency

    for lum in ligths.geometry:
        if not isinstance(lum, Point):
            raise TypeError("No corresponde a un punto")
        add_light_source(
            scene=scene,
            x=lum.x,
            y=lum.y,
            light_flux=light_flux
        )
    sqm = get_sqm(scene, grid)
    return sqm

def build_sqm_defined_ligths(
    scene: Scene, 
    grid: Grid, 
    ligths: GeoDataFrame,
    names: dict[str, str]=DEFAULT_ATTRIBUTE_NAMES):
    points = ligths.geometry
    print(f"Calculando SQM con {points.shape[0]} fuentes lumínicas")
    light_flux = (
        ligths[names["power"]] * ligths[names["eficiency"]]
        )
    for x, y, flux in zip(points.x, points.y, light_flux):
        scene.add_light_source(
            ModifiedLightSourceAlbersDuricoe(x, y, flux)
        )
    sqm = get_sqm(scene=scene, grid=grid)
    return sqm

def filter_geodf(
    geodf: GeoDataFrame,
    column: str,
    equals_to: str) -> GeoDataFrame:
    return geodf.loc[geodf[column]==equals_to].copy()

def ask_for_input():
    points_path = input("Ingrese la ruta del archivo de puntos (shapefile o geopackage): ")
    points_path = Path(points_path)
    if not points_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo en {points_path}")
    return points_path

class GeoFile:
    def __init__(self, file_path: Path):
        self.layer = None
        self._geo_data = None
        self.file_path = file_path

    @property
    @lru_cache
    def file_type(self) -> FileType:
        return get_file_type(self.file_path)

    @property
    @lru_cache
    def geodata(self) -> GeoDataFrame:
        if self._geo_data is None:
            self._geo_data = read_file(
                filename=self.file_path,
                layer=self.layer
            )
        return self._geo_data
    
    @property
    @lru_cache
    def columns(self):
        return self.geodata.columns

    def filter_data(self, column: str, equals_to: str):
        if column not in self.columns:
            raise ValueError(f"No se encontró la columna {column} en el archivo {self.file_path.stem}")
        self._geo_data = filter_geodf(
            geodf=self.geodata,
            column=column,
            equals_to=equals_to
        )
        return self
        
class GPKGFile(GeoFile):
    def __init__(self, file_path: Path):
        super().__init__(file_path)

    @property
    @lru_cache
    def layers(self):
        return list_layers(self.file_path)
    
    def set_layer(self, layer_name: str):
        if layer_name not in self.layers:
            raise ValueError(f"No se encontró la capa {layer_name} en el archivo {self.file_path}")
        self.layer = layer_name

class SHPFile(GeoFile):
    def __init__(self, file_path: Path):
        super().__init__(file_path)
        

def get_file(file_path: Path) -> GeoFile:
    file_type = get_file_type(file_path)
    if file_type == FileType.GEOPACKAGE:
        return GPKGFile(file_path)
    elif file_type == FileType.SHAPEFILE:
        return SHPFile(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")

def main():
    start_time = datetime.now()
    print("IluminaRA iniciado")
    file_path = ask_for_input()
    file = get_file(file_path)

    if LAYER is not None:
        all_ligths = read_file(
            filename=POINTS_PATH,
            layer=LAYER,
            )
    else:
        all_ligths = read_file(
            filename=POINTS_PATH,
            )
    ligths = all_ligths.copy()
    if FILTER_BY is not None:
        ligths = filter_geodf(
            geodf=all_ligths,
            column=FILTER_COLUMN,
            equals_to=FILTER_BY
        )
    print(f"Fuentes leídas desde {POINTS_PATH.name}")
    print(f"{ligths.shape[0]} Fuentes en total")
    x_limits, y_limts = grid_range_from_geodf(
        geo_df=ligths, 
        margin=MARGIN_FROM_POINTS,
        margin_fn=MARGIN_FN_DICT[MARGIN_FN]
        )
    grid = Grid(
        *x_limits,
        *y_limts,
        x_points=N_GRID_POINTS,
        y_points=N_GRID_POINTS
        )
    xv, yv = grid.values
    print(f"""Grilla creada
        {N_GRID_POINTS=}
        {MARGIN_FROM_POINTS=}
        {xv.shape=}""")
    scene = Scene()
    print("Calculando SQM ...")
    sqm = build_sqm_defined_ligths(scene, grid, ligths)
    points = array2points(xv, yv)
    geo_df = points_to_geodf(points, sqm)
    output_path = export(geo_df=geo_df)
    print(f"Archivo exportado en {RESOULTS_PATH.name} como {output_path.name}")
    end_time = datetime.now()
    print(f"Proceso terminado en {(end_time-start_time).seconds} segundos.")

if __name__ == "__main__":
    main()

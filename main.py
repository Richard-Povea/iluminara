from model.model import Scene, Grid, get_skyglow
from model.luminica import ModifiedLightSourceAlbersDuricoe,cd_per_m2_to_sqm_zotti
from geo import (
    array2points, grid_range_from_geodf, 
    flat_margin, percentage_margin
    )
from state import State, Event, machine, FileType, get_file_type
from errors import ColumnNotFoundError, DirectoryNotFoundError, NotADirectoryError, PathError

from typing import Literal, Self
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
    print(points.iloc[0])
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
    points_path = input("Ingrese la ruta del archivo de puntos (shapefile o geopackage): \n")
    points_path = Path(points_path)
    if not points_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo en {points_path}")
    return points_path

def ask_for_output_dir():
    output_dir = input()
    output_dir = Path(output_dir)
    if not output_dir.exists():
        raise DirectoryNotFoundError(output_dir)
    if not output_dir.is_dir():
        raise 
    return output_dir

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
        cols = self.geodata.columns.to_list()
        cols.remove("geometry")
        return {idx: col for idx, col in enumerate(cols)}

    def filter_data(self, column: str, equals_to: str) -> Self:
        self._validate_column(column)
        self._geo_data = filter_geodf(
            geodf=self.geodata,
            column=column,
            equals_to=equals_to
        )
        return self
    
    def valids_to_filter_values(self, column: str):
        self._validate_column(column)
        return self.geodata[column].unique()
    
    def _validate_column(self, column: str):
        if column not in self.columns.values():
            raise ColumnNotFoundError(column, self.file_path)
        
class GPKGFile(GeoFile):
    def __init__(self, file_path: Path):
        super().__init__(file_path)

    @property
    @lru_cache
    def layers(self):
        return list_layers(self.file_path)
    
    def set_layer(self, layer_index: str):
        layer = int(layer_index)
        if layer < 0 or layer >= len(self.layers):
            raise ValueError(f"Índice de capa inválido. Ingrese un número entre 0 y {len(self.layers)-1}")
        layer = self.layers.iloc[int(layer_index)]["name"]
        self.layer = layer
        return self

class SHPFile(GeoFile):
    def __init__(self, file_path: Path):
        super().__init__(file_path)
        

def get_file(file_path: Path) -> GeoFile|None:
    file_type = get_file_type(file_path)
    file_transport: dict[FileType, GeoFile] = {
        FileType.GEOPACKAGE: GPKGFile(file_path),
        FileType.SHAPEFILE: SHPFile(file_path)
    }
    return file_transport.get(file_type)

def filter_process(file: GeoFile) -> GeoFile:
    try:
        filter_by = input(f"¿Desea filtrar los datos? (s/n):\n")
        if filter_by.lower() != "s":
            return file
        column = input(f"¿Cuál es el índice de la columna a filtrar? Las columnas disponibles son: {file.columns}\n")
        while True:
            try:
                if column.isdigit() and 0 <= int(column) < len(file.columns):
                    column = file.columns[int(column)]
                    break
                else:
                    print("Índice de columna inválido. Intente nuevamente.")
            except ColumnNotFoundError as e:
                print(e.message)
                print("Intente nuevamente.")
        print(f"Columna seleccionada: {column}")
        valid_filters = file.valids_to_filter_values(column)
        equals_to = input(f"¿Cuál es el valor que debe tener la columna {(column)} para filtrar los datos?\nLas opciones disponibles son: {valid_filters}\n")
        while True:
            if equals_to in valid_filters:
                break
            else:
                equals_to = input("Valor inválido. Intente nuevamente.")
        print(f"Filtrando los datos por {column} igual a {equals_to} ...")
        return file.filter_data(column, equals_to)
    except KeyboardInterrupt:
        print("Proceso de filtrado interrumpido por el usuario.")
        return file
        
    
def main():
    start_time = datetime.now()
    print("IluminaRA iniciado")
    try:
        try:
            while True:
                file_path = ask_for_input()
                file = get_file(file_path)
                if file is None:
                    raise ValueError(f"Archivo no soportado: {file_path}")
                break
        except ValueError as e:
            print(e)
            exit(1)
        print("¿Donde desea guardar el archivo resultante? Ingrese la ruta a continuación.")
        while True:
            try:
                output_dir = ask_for_output_dir()
                global RESOULTS_PATH
                RESOULTS_PATH = output_dir
                break
            except PathError as e:
                print(e.message)
                print("Intente nuevamente.")
                

        if isinstance(file, GPKGFile):
            layer = input(f"El archivo {file_path.name} contiene las siguientes capas: {file.layers}\nIngrese el índice de la capa a leer: \n")
            file = file.set_layer(layer)
        file = filter_process(file)
        ligths = file.geodata
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
    except KeyboardInterrupt:
        print("Proceso interrumpoido por el usuario.")
        exit()

if __name__ == "__main__":
    main()

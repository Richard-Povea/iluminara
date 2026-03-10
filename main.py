from model.model import Scene, Grid, get_skyglow
from model.luminica import ModifiedLightSourceAlbersDuricoe,cd_per_m2_to_sqm_zotti
from geo import (
    array2points, grid_range_from_geodf, 
    flat_margin, percentage_margin,
    limit, x_y_limits
    )
from state import State, Event, machine, FileType, get_file_type
from errors import ColumnNotFoundError, DirectoryNotFoundError, PathError

from typing import  Self, Callable
from pathlib import Path
from numpy import pi, ndarray
from datetime import datetime
from geopandas import read_file, list_layers, GeoDataFrame
from geopandas.array import GeometryArray
from shapely import Point
from functools import lru_cache

MARGIN_FN_DICT = {
    "percentage": percentage_margin,
    "flat": flat_margin
}

def get_default_config() -> dict:
    import json
    with open("config.json", "r") as f:
        config = json.load(f)
    return config

from dataclasses import dataclass
    
@dataclass
class GridConfig:
    n_grid_points: int
    margin_from_points: float
    margin_fn: Callable[[int|float, limit, limit], x_y_limits]

    def __str__(self) -> str:
        return f"""GridConfig(
            n_grid_points={self.n_grid_points},
            margin_from_points={self.margin_from_points},
            margin_fn={self.margin_fn}
        )"""

@dataclass
class AttributeNames:
    power: str
    eficiency: str

@dataclass
class SQMConfig:
    natural_bg_skyglow: float
    background_sqm: float

def get_grid_config(default_config: dict) -> GridConfig:
    return GridConfig(
        n_grid_points=default_config["n_grid_points"],
        margin_from_points=default_config["margin_from_points"],
        margin_fn=MARGIN_FN_DICT[default_config["margin_type"]]
    )

def get_sqm_config(default_config: dict) -> SQMConfig:
    return SQMConfig(
        natural_bg_skyglow=default_config["natural_background_skyglow"],
        background_sqm=default_config["background_sqm"]
    )

def get_attribute_names(default_config: dict) -> AttributeNames:
    return AttributeNames(
        power=default_config["default_power_columname"],
        eficiency=default_config["default_efficiency_columname"]
    )

def points_to_geodf(points: GeometryArray, sqm:ndarray):
    d = {"Value":sqm.flat, "geometry":points}
    geo_df = GeoDataFrame(d)
    return geo_df

def export(geo_df: GeoDataFrame, grid_config: GridConfig, output_path: Path|None=None):
    if output_path == None:
        output_dir = RESOULTS_PATH
        time = datetime.now().strftime(format="%Y_%m_%d %H_%M_%S")
        output_filename = "{}_points_{}_{}".format(
            grid_config.n_grid_points, 
            grid_config.margin_from_points,
            grid_config.margin_fn.__name__)
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

def get_sqm(scene: Scene, grid:Grid, sqm_config: SQMConfig):
    skyglow_albers_duricoe = get_skyglow(scene, grid, omega=2*pi)
    skyglow_albers_duricoe += sqm_config.natural_bg_skyglow
    sqm = cd_per_m2_to_sqm_zotti(skyglow_albers_duricoe)
    
    sqm[sqm > sqm_config.background_sqm] = sqm_config.background_sqm
    return sqm

def build_sqm_one_ligth(
        scene: Scene, 
        grid: Grid, 
        ligths: GeoDataFrame,
        electric_power: int,
        luminosity_efficiency: int,
        sqm_config: SQMConfig):
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
    sqm = get_sqm(scene, grid, sqm_config)
    return sqm

def build_sqm_defined_ligths(
    scene: Scene, 
    grid: Grid, 
    ligths: GeoDataFrame,
    names: AttributeNames,
    sqm_config: SQMConfig):
    points = ligths.geometry
    print(f"Calculando SQM con {points.shape[0]} fuentes lumínicas")
    light_flux = (
        ligths[names.power] * ligths[names.eficiency]
        )
    for x, y, flux in zip(points.x, points.y, light_flux):
        scene.add_light_source(
            ModifiedLightSourceAlbersDuricoe(x, y, flux)
        )
    sqm = get_sqm(scene=scene, grid=grid, sqm_config=sqm_config)
    return sqm

def filter_geodf(
    geodf: GeoDataFrame,
    column: str,
    equals_to: str) -> GeoDataFrame:
    return geodf.loc[geodf[column]==equals_to].copy()

def clean_path_sting(path: str) -> Path:
    path = path.strip('"').strip("'").strip()
    return Path(path)

def ask_for_input():
    points_path = input("Ingrese la ruta del archivo de puntos (shapefile o geopackage): \n")
    points_path = clean_path_sting(points_path)
    if not points_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo en {points_path}")
    return points_path

def ask_for_output_dir():
    output_dir = input()
    output_dir = clean_path_sting(output_dir)
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
        return self.geodata[column].unique().tolist()
    
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
    print(f"¿Cuál es el valor que debe tener la columna {(column)} para filtrar los datos?")
    equals_to = input(f"Las opciones disponibles son: {valid_filters}\n")
    while True:
        if str(equals_to) in [str(v) for v in valid_filters]:
            break
        else:
            equals_to = input("Valor inválido. Intente nuevamente.\n")
    print(f"Filtrando los datos por {column} igual a {equals_to} ...")
    return file.filter_data(column, equals_to)       

def new_grid_config_process() -> GridConfig|None:
    print("¿Desea cambiar la configuración de la grilla? (s/n)")
    change_grid_config = input()
    if change_grid_config.lower() != "s":
        return None
    n_grid_points = input("Ingrese el número de puntos para la grilla (ej: 1000): \n")
    while True:
        if n_grid_points.isdigit() and int(n_grid_points) > 0:
            n_grid_points = int(n_grid_points)
            break
        else:
            n_grid_points = input("Número de puntos inválido. Intente nuevamente: \n")
    margin_from_points = input("Ingrese el margen desde los puntos para la grilla (ej: 40): \n")
    while True:
        try:
            margin_from_points = float(margin_from_points)
            break
        except ValueError:
            margin_from_points = input("Margen inválido. Intente nuevamente: \n")
    margin_fn = input("Ingrese el tipo de margen (percentage o flat): \n")
    while True:
        if margin_fn in MARGIN_FN_DICT.keys():
            break
        else:
            margin_fn = input("Tipo de margen inválido. Intente nuevamente: \n")
    return GridConfig(
        n_grid_points=n_grid_points,
        margin_from_points=margin_from_points,
        margin_fn=MARGIN_FN_DICT[margin_fn]
    ) 
    
def main():
    start_time = datetime.now()
    print("IluminaRA iniciado")
    config = get_default_config()
    sqm_config = get_sqm_config(config)
    grid_config = get_grid_config(config)
    attributes_names = get_attribute_names(config)
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
            print(f"El archivo {file_path.name} contiene las siguientes capas: \n{file.layers}")
            print("Recuerde que sólo las capas con geometría de puntos pueden ser utilizadas para el cálculo del SQM.")
            layer = input("Ingrese el índice de la capa a leer: \n")
            while True:
                try:
                    file = file.set_layer(layer)
                    break
                except ValueError as e:
                    layer = input("Índice de capa inválido. Intente nuevamente: \n")
        try:
            file._validate_column(attributes_names.power)
            file._validate_column(attributes_names.eficiency)
        except ColumnNotFoundError as e:
            print(e.message)
            print("Asegúrese de que el archivo contenga las columnas necesarias para calcular el flujo luminoso ({} y {})".format(
                attributes_names.power, attributes_names.eficiency))
            print("o actualice los nombres de las columnas en el archivo de configuración.")
            exit(1)
        try:
            filtered = filter_process(file)
        except KeyboardInterrupt:
            print("Proceso de filtrado interrumpido por el usuario.")
            return file
        ligths = filtered.geodata
        print(f"{ligths.shape[0]} Fuentes en total")
        print("¿Deseas cambiar la configuración de la grilla? (s/n)")
        x_limits, y_limts = grid_range_from_geodf(
            geo_df=ligths, 
            margin=grid_config.margin_from_points,
            margin_fn=grid_config.margin_fn
            )
        grid = Grid(
            *x_limits,
            *y_limts,
            x_points=grid_config.n_grid_points,
            y_points=grid_config.n_grid_points
            )
        xv, yv = grid.values
        print(f"""Grilla creada
            {grid_config.n_grid_points=}
            {grid_config.margin_from_points=}
            {xv.shape=}""")
        scene = Scene()
        print("Calculando SQM ...")
        sqm = build_sqm_defined_ligths(scene, grid, ligths, attributes_names, sqm_config)
        points = array2points(xv, yv)
        geo_df = points_to_geodf(points, sqm)
        output_path = export(geo_df=geo_df, grid_config=grid_config)
        print(f"Archivo exportado en {RESOULTS_PATH.name} como {output_path.name}")
        end_time = datetime.now()
        print(f"Proceso terminado en {(end_time-start_time).seconds} segundos.")
    except KeyboardInterrupt:
        print("Proceso interrumpoido por el usuario.")
        exit()

if __name__ == "__main__":
    main()

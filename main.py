from model.model import Scene, Grid
from geo import (
    array2points, grid_range_from_geodf
)
from state import State, Event, machine, FileType, get_file_type
from errors import ColumnNotFoundError, DirectoryNotFoundError
from logger import setup_logger, get_logger
from config import AttributeNames, GridConfig, MARGIN_FN_DICT, get_grid_config, get_sqm_config
from processig import build_sqm_defined_ligths

from typing import Self, Callable
from pathlib import Path
from numpy import ndarray
from datetime import datetime
from geopandas import read_file, list_layers, GeoDataFrame
from geopandas.array import GeometryArray
from functools import lru_cache

def get_default_config() -> dict:
    import json
    with open("config.json", "r") as f:
        config = json.load(f)
    return config

def get_attribute_names(default_config: dict) -> AttributeNames:
    return AttributeNames(
        power=default_config["default_power_columname"],
        eficiency=default_config["default_efficiency_columname"]
    )


def points_to_geodf(points: GeometryArray, sqm: ndarray):
    d = {"Value": sqm.flat, "geometry": points}
    geo_df = GeoDataFrame(d)
    return geo_df


def build_output_path(output_dir: Path, grid_config: GridConfig) -> Path:
    time = datetime.now().strftime(format="%Y_%m_%d %H_%M_%S")
    filename = "{}_points_{}_{}_{}.shp".format(
        grid_config.n_grid_points,
        grid_config.margin_from_points,
        grid_config.margin_fn.__name__,
        time
    )
    return output_dir / filename


def export(geo_df: GeoDataFrame, output_path: Path) -> Path:
    geo_df.to_file(output_path)
    return output_path




def filter_geodf(
        geodf: GeoDataFrame,
        column: str,
        equals_to: str) -> GeoDataFrame:
    return geodf.loc[geodf[column] == equals_to].copy()


def clean_path_sting(path: str) -> Path:
    path = path.strip('"').strip("'").strip()
    return Path(path)


def ask_for_input():
    points_path = input("Ingrese la ruta del archivo de puntos (shapefile o geopackage): \n")
    points_path = clean_path_sting(points_path)
    if not points_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo en {points_path}")
    return points_path


def ask_for_output_dir(output_dir_str: str) -> Path:
    output_dir = clean_path_sting(output_dir_str)
    if not output_dir.exists():
        raise DirectoryNotFoundError(output_dir)
    if not output_dir.is_dir():
        raise ValueError(f"{output_dir} no es un directorio válido")
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
    def geodata(self) -> GeoDataFrame:
        if self._geo_data is None:
            self._geo_data = read_file(filename=self.file_path, layer=self.layer)
        return self._geo_data

    @property
    def columns(self):
        cols = self.geodata.columns.to_list()
        cols.remove("geometry")
        return {idx: col for idx, col in enumerate(cols)}

    def filter_data(self, column: str, equals_to: str) -> Self:
        self._validate_column(column)
        self._geo_data = filter_geodf(geodf=self.geodata, column=column, equals_to=equals_to)
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
            raise ValueError(f"Índice de capa inválido. Ingrese un número entre 0 y {len(self.layers) - 1}")
        layer = self.layers.iloc[int(layer_index)]["name"]
        self.layer = layer
        return self


class SHPFile(GeoFile):
    def __init__(self, file_path: Path):
        super().__init__(file_path)


def get_file(file_path: Path) -> GeoFile | None:
    file_type = get_file_type(file_path)
    file_transport: dict[FileType, GeoFile] = {
        FileType.GEOPACKAGE: GPKGFile(file_path),
        FileType.SHAPEFILE: SHPFile(file_path)
    }
    return file_transport.get(file_type)


def ask_until_valid(
        prompt: str,
        validator: Callable,
        error_msg: str = "Valor inválido. Intente nuevamente."):
    log = get_logger()
    while True:
        value = input(prompt)
        try:
            result = validator(value)
            if result is not None:
                log.debug(f"Input aceptado para prompt '{prompt.strip()}': {value!r}")
                return result
        except (ValueError, ColumnNotFoundError):
            pass
        log.warning(f"Input inválido para prompt '{prompt.strip()}': {value!r} — {error_msg}")
        print(error_msg)


def filter_process(file: GeoFile) -> GeoFile:
    log = get_logger()
    if input("¿Desea filtrar los datos? (s/n):\n").lower() != "s":
        log.info("El usuario omitió el filtrado de datos")
        return file

    column = ask_until_valid(
        prompt=f"¿Cuál es el índice de la columna a filtrar? Las columnas disponibles son: {file.columns}\n",
        validator=lambda v: file.columns[int(v)] if v.isdigit() and 0 <= int(v) < len(file.columns) else None,
        error_msg="Índice de columna inválido. Intente nuevamente."
    )
    log.info(f"Columna seleccionada para filtrar: {column!r}")

    valid_filters = file.valids_to_filter_values(column)

    def validate_filter(v: str):
        col_type = type(valid_filters[0])
        try:
            casted = col_type(v)
        except (ValueError, TypeError):
            return None
        return casted if casted in valid_filters else None

    equals_to = ask_until_valid(
        prompt=f"Las opciones disponibles son: {valid_filters}\n",
        validator=validate_filter,
        error_msg="Valor inválido. Intente nuevamente."
    )
    log.info(f"Filtrando datos: {column!r} == {equals_to!r}")
    return file.filter_data(column, equals_to)


def new_grid_config_process() -> GridConfig | None:
    log = get_logger()
    if input("¿Desea cambiar la configuración de la grilla? (s/n)\n").lower() != "s":
        log.info("Se usará la configuración de grilla por defecto")
        return None

    n_grid_points = ask_until_valid(
        prompt="Ingrese el número de puntos para la grilla (ej: 1000): \n",
        validator=lambda v: int(v) if v.isdigit() and int(v) > 0 else None,
        error_msg="Número de puntos inválido. Intente nuevamente."
    )
    margin_from_points = ask_until_valid(
        prompt="Ingrese el margen desde los puntos para la grilla (ej: 40): \n",
        validator=lambda v: float(v),
        error_msg="Margen inválido. Intente nuevamente."
    )
    margin_fn = ask_until_valid(
        prompt="Ingrese el tipo de margen (percentage o flat): \n",
        validator=lambda v: MARGIN_FN_DICT[v] if v in MARGIN_FN_DICT else None,
        error_msg="Tipo de margen inválido. Intente nuevamente."
    )

    new_config = GridConfig(
        n_grid_points=n_grid_points,
        margin_from_points=margin_from_points,
        margin_fn=margin_fn
    )
    log.info(f"Nueva configuración de grilla: {new_config}")
    return new_config


def load_file() -> GeoFile:
    log = get_logger()
    while True:
        try:
            file_path = ask_for_input()
        except FileNotFoundError as e:
            log.warning(str(e))
            print(str(e))
            continue
        file = get_file(file_path)
        if file is not None:
            log.info(f"Archivo cargado: {file_path}")
            return file
        log.warning(f"Archivo no soportado: {file_path}")
        print(f"Archivo no soportado: {file_path}. Intente nuevamente.")


def select_layer(file: GPKGFile) -> GPKGFile:
    log = get_logger()
    log.debug(f"Capas disponibles en {file.file_path}: {file.layers['name'].tolist()}")
    print(f"El archivo contiene las siguientes capas:\n{file.layers}")
    print("Recuerde que sólo las capas con geometría de puntos (no multipuntos) pueden ser utilizadas.")
    selected = ask_until_valid(
        prompt="Ingrese el índice de la capa a leer:\n",
        validator=lambda v: file.set_layer(v),
        error_msg="Índice de capa inválido. Intente nuevamente."
    )
    log.info(f"Capa seleccionada: {selected.layer!r}")
    return selected


def validate_columns(file: GeoFile, attributes_names: AttributeNames):
    log = get_logger()
    try:
        file._validate_column(attributes_names.power)
        file._validate_column(attributes_names.eficiency)
        log.debug(f"Columnas validadas: power={attributes_names.power!r}, eficiency={attributes_names.eficiency!r}")
    except ColumnNotFoundError as e:
        log.error(f"Columna no encontrada: {e.message}")
        log.error(
            f"El archivo debe contener las columnas {attributes_names.power!r} y {attributes_names.eficiency!r}. "
            "Verifique el archivo de configuración."
        )
        print(e.message)
        print("Asegúrese de que el archivo contenga las columnas necesarias ({} y {})".format(
            attributes_names.power, attributes_names.eficiency))
        print("o actualice los nombres en el archivo de configuración.")
        exit(1)


def build_grid(ligths: GeoDataFrame, grid_config: GridConfig) -> tuple[Grid, ndarray, ndarray]:
    log = get_logger()
    x_limits, y_limits = grid_range_from_geodf(
        geo_df=ligths,
        margin=grid_config.margin_from_points,
        margin_fn=grid_config.margin_fn
    )
    grid = Grid(
        *x_limits, *y_limits,
        x_points=grid_config.n_grid_points,
        y_points=grid_config.n_grid_points
    )
    xv, yv = grid.values
    log.info(f"Grilla creada — n_grid_points={grid_config.n_grid_points}, shape={xv.shape}")
    log.debug(f"x_limits={x_limits}, y_limits={y_limits}")
    return grid, xv, yv


def main():
    start_time = datetime.now()

    # El logger se inicializa aquí, antes de cualquier operación.
    # El directorio de logs puede cambiarse o dejarse en None para sólo consola.
    log = setup_logger(log_dir=Path("logs"))
    log.info("=== IluminaRA iniciado ===")

    config = get_default_config()
    log.debug(f"Configuración cargada: {config}")

    sqm_config = get_sqm_config(config)
    grid_config = get_grid_config(config)
    attributes_names = get_attribute_names(config)
    log.debug(f"Grid config: {grid_config}")

    try:
        # Carga del archivo
        file = load_file()

        # Directorio de salida
        log.info("Solicitando directorio de salida al usuario")
        print("¿Dónde desea guardar el archivo resultante?")
        output_dir: Path = ask_until_valid(
            prompt="Ingrese la ruta:\n",
            validator=lambda v: ask_for_output_dir(v),
            error_msg="Directorio inválido. Intente nuevamente."
        )
        log.info(f"Directorio de salida: {output_dir}")

        # Selección de capa (solo GPKG)
        if isinstance(file, GPKGFile):
            file = select_layer(file)

        # Validación de columnas
        validate_columns(file, attributes_names)

        # Filtrado
        filtered = filter_process(file)
        ligths = filtered.geodata
        log.info(f"{ligths.shape[0]} fuentes lumínicas en total tras filtrado")

        # Configuración de grilla (opcional)
        new_config = new_grid_config_process()
        if new_config:
            grid_config = new_config

        # Cálculo
        grid, xv, yv = build_grid(ligths, grid_config)
        scene = Scene()
        log.info("Iniciando cálculo de SQM ...")
        sqm = build_sqm_defined_ligths(scene, grid, ligths, attributes_names, sqm_config)
        log.info("Cálculo de SQM completado")

        # Exportación
        points = array2points(xv, yv)
        geo_df = points_to_geodf(points, sqm)
        output_path = build_output_path(output_dir, grid_config)
        export(geo_df, output_path)
        log.info(f"Archivo exportado: {output_path}")

        elapsed = (datetime.now() - start_time).seconds
        log.info(f"=== Proceso terminado en {elapsed} segundos ===")
        print(f"Archivo exportado en {output_dir.name} como {output_path.name}")
        print(f"Proceso terminado en {elapsed} segundos.")

    except KeyboardInterrupt:
        log.warning("Proceso interrumpido por el usuario (KeyboardInterrupt)")
        print("\nProceso interrumpido por el usuario.")
        exit()

    except Exception as e:
        log.exception(f"Error inesperado: {e}")
        raise


if __name__ == "__main__":
    main()
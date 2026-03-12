from typing import Callable
from pathlib import Path
from logger import get_logger

from errors import ColumnNotFoundError
from geo import GeoFile, GPKGFile, get_geofile
from config import GridConfig, MARGIN_FN_DICT
from i_o import validate_path_input, validate_output_dir

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
            points_path = input("Ingrese la ruta del archivo de puntos (shapefile o geopackage): \n")
            file_path = validate_path_input(points_path)
        except FileNotFoundError as e:
            log.warning(str(e))
            print(str(e))
            continue
        file = get_geofile(file_path)
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

def ask_output_dir():
    log = get_logger()
    log.info("Solicitando directorio de salida al usuario")
    print("¿Dónde desea guardar el archivo resultante?")
    output_dir: Path = ask_until_valid(
        prompt="Ingrese la ruta:\n",
        validator=lambda v: validate_output_dir(v),
        error_msg="Directorio inválido. Intente nuevamente."
    )
    log.info(f"Directorio de salida: {output_dir}")
    return output_dir

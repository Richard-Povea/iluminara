from model.model import Scene
from geo import (
    GPKGFile, array2points, validate_columns,
    export, points_to_geodf
    )
from logger import setup_logger
from config import (
    get_grid_config, get_sqm_config, 
    get_attribute_names, get_default_config
    )
from processig import build_sqm_defined_ligths, build_grid
from i_o import build_output_path
from cli import (
    load_file, select_layer, filter_process, 
    new_grid_config_process, ask_output_dir
    )

from pathlib import Path
from datetime import datetime

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
        output_dir = ask_output_dir()

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
        log.info(f"Grilla creada — n_grid_points={grid_config.n_grid_points}, shape={xv.shape}")
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
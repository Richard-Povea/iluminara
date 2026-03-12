import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logger(log_dir: Path | None = None, level: int = logging.DEBUG) -> logging.Logger:
    """
    Configura y retorna el logger principal de IluminaRA.

    - Siempre escribe en consola (stdout) con nivel INFO.
    - Si se provee log_dir, también escribe en un archivo .log con nivel DEBUG.

    Args:
        log_dir: Directorio donde guardar el archivo de log. Si es None, sólo se loguea en consola.
        level:   Nivel mínimo de captura del logger raíz (por defecto DEBUG).

    Returns:
        Logger configurado bajo el nombre "iluminara".
    """
    logger = logging.getLogger("iluminara")
    logger.setLevel(level)

    # Evitar handlers duplicados si se llama más de una vez
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # --- Handler de consola ---
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # --- Handler de archivo (opcional) ---
    if log_dir is not None:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        log_path = log_dir / f"iluminara_{timestamp}.log"
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.debug(f"Archivo de log creado en: {log_path}")

    return logger


def get_logger() -> logging.Logger:
    """Retorna el logger de IluminaRA (debe haberse inicializado con setup_logger primero)."""
    return logging.getLogger("iluminara")
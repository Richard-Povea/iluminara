from pathlib import Path

class PathError(Exception):
    """Base class for path exceptions"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class DirectoryNotFoundError(PathError):
    """Exception raised for errors in the input directory."""
    def __init__(self, directory: Path):
        self.directory = directory
        self.message = f"No se encontró el directorio en {self.directory}"
        super().__init__(self.message)

class NotADirectoryError(PathError):
    """Exception raised when the provided path is not a directory."""
    def __init__(self, path: Path):
        self.path = path
        self.message = f"La ruta proporcionada no es un directorio: {self.path}"
        super().__init__(self.message)

class GeoDataError(Exception):
    """Base class for exceptions in this module."""
    pass

class ColumnNotFoundError(GeoDataError):
    """Exception raised for errors in the input column."""
    def __init__(self, column: str, file_path: Path):
        self.column = column
        self.file_path = file_path
        self.message = f"No se encontró la columna ´{self.column}´ en el archivo ´{self.file_path.stem}´"
        super().__init__(self.message)

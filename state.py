from enum import Enum, auto
from pathlib import Path

class State(Enum):
    INITIAL = auto()
    ASKING_FOR_INPUT = auto()
    LOADING_DATA = auto()
    PROCESSING_DATA = auto()
    SAVING_RESULTS = auto()
    COMPLETED = auto()

class Event(Enum):
    ASK_FOR_INPUT = auto()
    INPUT_RECEIVED = auto()
    DATA_LOADED = auto()
    DATA_PROCESSED = auto()
    RESULTS_SAVED = auto()
    ERROR = auto()

machine = {
    State.INITIAL: {
        Event.ASK_FOR_INPUT: State.ASKING_FOR_INPUT
    },
    State.ASKING_FOR_INPUT: {
        Event.INPUT_RECEIVED: State.LOADING_DATA,
        Event.ERROR: State.INITIAL
    },
    State.LOADING_DATA: {
        Event.DATA_LOADED: State.PROCESSING_DATA,
        Event.ERROR: State.INITIAL
    },
    State.PROCESSING_DATA: {
        Event.DATA_PROCESSED: State.SAVING_RESULTS,
        Event.ERROR: State.INITIAL
    },
    State.SAVING_RESULTS: {
        Event.RESULTS_SAVED: State.COMPLETED,
        Event.ERROR: State.INITIAL
    },
}

class FileType(Enum):
    SHAPEFILE = auto()
    GEOPACKAGE = auto()

def get_file_type(file_path: Path) -> FileType:
    if file_path.suffix.lower() == ".shp":
        return FileType.SHAPEFILE
    elif file_path.suffix.lower() in [".gpkg", ".geopackage"]:
        return FileType.GEOPACKAGE
    else:
        raise ValueError(f"Unsupported file type: {file_path.suffix}")

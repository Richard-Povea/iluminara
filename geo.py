from geopandas import GeoDataFrame
from geopandas import read_file, list_layers, points_from_xy
from geopandas.array import GeometryArray
from numpy import ndarray
from typing import Callable, Iterable, Self
from functools import lru_cache
from pathlib import Path

from state import FileType, get_file_type
from errors import ColumnNotFoundError

type limit = Iterable[float]
type x_y_limits = Iterable[limit]

def get_new_limts(limits: limit, margin: limit) -> limit:
    new_limits: limit = [coord + delta for coord, delta in zip(limits, margin)]
    return new_limits

def flat_margin(
        margin: int,
        x_limits: limit, 
        y_limits: limit,
        ) -> x_y_limits:
    margin_tuple = (-margin, margin)
    new_x_limits = get_new_limts(x_limits, margin_tuple)
    new_y_limits = get_new_limts(y_limits, margin_tuple)
    return new_x_limits, new_y_limits

def percentage_margin(
        margin: float,
        x_limits: limit, 
        y_limits: limit,
        ) -> x_y_limits:
    x_min, x_max = x_limits
    y_min, y_max = y_limits
    x_range = x_max - x_min
    y_range = y_max - y_min
    range_as_per = max(x_range, y_range)*margin/100
    margin_tuple = (-range_as_per, range_as_per)
    new_x_limits = get_new_limts(x_limits, margin_tuple)
    new_y_limits = get_new_limts(y_limits, margin_tuple)
    return new_x_limits, new_y_limits

def get_points_range_from_shapefile(geo_df: GeoDataFrame) -> tuple[float, float, float, float]:
    # shape: desde geopandas gpd.read_file(...)
    coordinates = geo_df.get_coordinates()
    return (
        coordinates.x.min(), 
        coordinates.x.max(),
        coordinates.y.min(), 
        coordinates.y.max()
        )

def grid_range_from_geodf(
        geo_df: GeoDataFrame, 
        margin: int|float,
        margin_fn: Callable[[int|float, limit, limit], x_y_limits]) -> x_y_limits:
    """
    :param GeoDataFrame geo_df: GeoDaraFrame with points
    :param int margin: Margin form points as perentage
    """
    # shape: desde geopandas gpd.read_file(...)
    x_min, x_max, y_min, y_max = get_points_range_from_shapefile(geo_df)
    new_x_limits, new_y_limits = margin_fn(
        margin,
        (x_min, x_max),
        (y_min, y_max)
    )

    return new_x_limits, new_y_limits

def array2points(x_values: ndarray, y_values: ndarray):
    points = points_from_xy(
        x=x_values.flat,
        y=y_values.flat,
        crs="EPSG:32719"
    )
    return points

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


def get_geofile(file_path: Path) -> GeoFile | None:
    file_type = get_file_type(file_path)
    file_transport: dict[FileType, GeoFile] = {
        FileType.GEOPACKAGE: GPKGFile(file_path),
        FileType.SHAPEFILE: SHPFile(file_path)
    }
    return file_transport.get(file_type)

def export(geo_df: GeoDataFrame, output_path: Path) -> Path:
    geo_df.to_file(output_path)
    return output_path

def filter_geodf(
        geodf: GeoDataFrame,
        column: str,
        equals_to: str) -> GeoDataFrame:
    return geodf.loc[geodf[column] == equals_to].copy()

def points_to_geodf(points: GeometryArray, sqm: ndarray):
    d = {"Value": sqm.flat, "geometry": points}
    geo_df = GeoDataFrame(d)
    return geo_df

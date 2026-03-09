from geopandas import points_from_xy
from geopandas import GeoDataFrame
from numpy import ndarray
from typing import Callable, Iterable

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

from model.model import Scene, Grid, get_skyglow
from model.luminica import ModifiedLightSourceAlbersDuricoe
from config import AttributeNames, SQMConfig, GridConfig
from geo import grid_range_from_geodf

from geopandas import GeoDataFrame
from shapely import Point
from numpy import ndarray

def add_light_source(scene: Scene, x: float, y: float, light_flux: int):
    light_source = ModifiedLightSourceAlbersDuricoe(x, y, light_flux)
    scene.add_light_source(light_source)

def build_sqm_one_ligth(
        scene: Scene,
        grid: Grid,
        ligths: GeoDataFrame,
        electric_power: int,
        luminosity_efficiency: int,
        sqm_config: SQMConfig):
    light_flux = electric_power * luminosity_efficiency
    for lum in ligths.geometry:
        if not isinstance(lum, Point):
            raise TypeError("No corresponde a un punto")
        add_light_source(scene=scene, x=lum.x, y=lum.y, light_flux=light_flux)
    sqm = get_sqm(scene, grid, sqm_config)
    return sqm

def get_sqm(scene: Scene, grid: Grid, sqm_config: SQMConfig):
    skyglow_albers_duricoe = get_skyglow(scene, grid)
    skyglow_albers_duricoe += sqm_config.natural_bg_skyglow
    sqm = sqm_config.cd_2_sqm(skyglow_albers_duricoe)
    sqm[sqm > sqm_config.background_sqm] = sqm_config.background_sqm
    return sqm

def build_sqm_defined_ligths(
        scene: Scene,
        grid: Grid,
        ligths: GeoDataFrame,
        names: AttributeNames,
        sqm_config: SQMConfig):
    points = ligths.geometry
    light_flux = ligths[names.power] * ligths[names.eficiency]
    for x, y, flux in zip(points.x, points.y, light_flux):
        scene.add_light_source(ModifiedLightSourceAlbersDuricoe(x, y, flux))
    sqm = get_sqm(scene=scene, grid=grid, sqm_config=sqm_config)
    return sqm


def build_grid(ligths: GeoDataFrame, grid_config: GridConfig) -> tuple[Grid, ndarray, ndarray]:
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
    return grid, xv, yv
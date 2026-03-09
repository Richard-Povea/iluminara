from numpy import linspace, meshgrid, sqrt, zeros, pi, ndarray
from .luminica import (
    get_modified_skyglow,
    ModifiedLightSourceAlbersDuricoe
    )
from dataclasses import dataclass, field
from functools import cached_property

####################################################
## Escenario de Modelación

@dataclass
class Grid:
    x_initial: float = -50
    x_end: float = 50
    y_initial: float = -50
    y_end: float = 50
    x_points: int = 250
    y_points: int = 250

    @cached_property
    def values(self):
        x = linspace(self.x_initial, self.x_end, self.x_points)
        y = linspace(self.y_initial, self.y_end, self.y_points)
        xv, yv = meshgrid(x, y)
        return xv, yv
    
    @cached_property
    def zeros_matrix(self):
        xv, _ = self.values
        return zeros(shape=xv.shape)
    
class Scene:
    def __init__(self):
        self.sources : list[ModifiedLightSourceAlbersDuricoe] = []

    def add_light_source(self, light_source: ModifiedLightSourceAlbersDuricoe):
        self.sources.append(light_source)

    def get_distance_matrix_from_source(
            self, 
            source_idx: int, 
            grid_values: tuple[ndarray, ndarray]
            ):
        xv, yv = grid_values
        source = self.sources[source_idx]
        distance = sqrt((xv - source.x) ** 2 + (yv - source.y) ** 2)
        return distance

def get_skyglow(scene: Scene, grid: Grid, omega=4*pi):
    # Io: brillo artificial en el cénit del cielo
    skyglow = grid.zeros_matrix
    grid_values = grid.values
    for n, source in enumerate(scene.sources):
        dist_matrix = scene.get_distance_matrix_from_source(
            source_idx=n,
            grid_values=grid_values
        )
        skyglow += get_modified_skyglow(
            dist_matrix, 
            source,
            omega=omega
        )
    return skyglow

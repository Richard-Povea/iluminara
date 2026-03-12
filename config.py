from typing import Callable
from dataclasses import dataclass
from numpy import ndarray

from geo_types import limit, x_y_limits, percentage_margin, flat_margin
from model.luminica import CD_2_SQM_DICT

MARGIN_FN_DICT = {
    "percentage": percentage_margin,
    "flat": flat_margin
}

@dataclass
class SQMConfig:
    cd_2_sqm: Callable[[ndarray], ndarray]
    natural_bg_skyglow: float
    background_sqm: float

@dataclass
class GridConfig:
    n_grid_points: int
    margin_from_points: float
    margin_fn: Callable[[int | float, limit, limit], x_y_limits]

    def __str__(self) -> str:
        return f"""GridConfig(
            n_grid_points={self.n_grid_points},
            margin_from_points={self.margin_from_points},
            margin_fn={self.margin_fn}
        )"""


@dataclass
class AttributeNames:
    power: str
    eficiency: str


def get_grid_config(default_config: dict) -> GridConfig:
    return GridConfig(
        n_grid_points=default_config["n_grid_points"],
        margin_from_points=default_config["margin_from_points"],
        margin_fn=MARGIN_FN_DICT[default_config["margin_type"]]
    )


def get_sqm_config(default_config: dict) -> SQMConfig:
    return SQMConfig(
        cd_2_sqm=CD_2_SQM_DICT[default_config["cd_2_sqm"]],
        natural_bg_skyglow=default_config["natural_background_skyglow"],
        background_sqm=default_config["background_sqm"]
    )

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

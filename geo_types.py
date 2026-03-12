from typing import Iterable

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

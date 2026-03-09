from numpy import log10, pi, ndarray
from dataclasses import dataclass

@dataclass
class Light:
    x: float
    y: float

def cd_per_m2_to_sqm_zotti(cd_per_m2: ndarray) -> ndarray:
    """
    :param ndarray cd_per_m2: Candelas por petro cuadrado
    :return: sky quality magnitude
    :rtype: ndarray
    """
    # desde Zotti(2007): "Measuring Light Pollution with a Calibrated High Dynamic Range All-Sky Image Acquisition System"
    # eq (2)
    sky_quality_magnitude = 12.603 - 2.5 * log10(cd_per_m2)
    return sky_quality_magnitude

def cd_per_m2_to_sqm_astroshop(cd_per_m2: ndarray) -> ndarray:
    """
    :param ndarray cd_per_m2: Candelas por petro cuadrado
    :return: sky quality magnitude
    :rtype: ndarray
    """
    # MÉTODO MEJORADO: DA IGUAL QUE EN lightpollutionmap.org
    # FUENTE: eq (2.1) en https://www.astroshop.be/Produktdownloads/48182_1_Anleitung-EN.pdf 
    # b in [cd/m2]
    # return SQM in [mag/arcseg2]
    sky_quality_magnitude = -2.5 * log10(cd_per_m2 / 10.8e4)
    return sky_quality_magnitude

##################################################################
# Fuente Luminosa

class ModifiedLightSourceAlbersDuricoe(Light):
    def __init__(self, x, y, flux, amount=1):
        super().__init__(x, y)
        self.flux = flux
        self.amount = amount

def get_modified_skyglow(
        r: ndarray, 
        ligth: ModifiedLightSourceAlbersDuricoe,
        omega=4*pi) -> ndarray:
    """
    :param float flux: Luminous flux [Lumen]
    :param ndarray r: Distance between source and point. [m]
    :param float omega: Solid angle in [sr]. Default: spherical source, omega = 4pi.
    :return: skyglow
    :rtype: ndarray
    """
    # flux: luminous flux [Lumen]
    # r: distance between source and point. [m]
    # omega: solid angle in [sr]. Default: spherical source, omega = 4pi.
    skyglow = (ligth.flux  / (4 * omega)) * ligth.amount * (r ** (-2.5))
    return skyglow
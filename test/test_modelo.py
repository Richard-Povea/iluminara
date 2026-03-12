from model.luminica import get_modified_skyglow, cd_per_m2_to_sqm_astroshop, r_astrohop

def test_modified_skyglow():
    flux = 3_000
    distance = 100

    assert get_modified_skyglow(distance, flux) == 0.0011936620731892152

def test_astroshop():
    flux = 3_000
    distance = 100
    skyglow = get_modified_skyglow(distance, flux)
    assert cd_per_m2_to_sqm_astroshop(skyglow) == 19.891355901133412

def test_r_asgtroshop():
    flux = 30_000
    sqm = 21.5
    assert r_astrohop(flux, sqm) == 454.34217823290936

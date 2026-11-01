from datetime import date

from engine.comps import Comp, Index, Params, Target, estimate, params_from_files, weighted_quantile

AS_OF = date(2026, 6, 1)


def comp(i, lat=41.9, lon=-87.7, kind="condo", units=3, price=400_000, sqft=1200, sold=date(2025, 6, 1)):
    return Comp(str(i), str(i), kind, f"b{i}", sold, price, units, sqft, lat, lon)


def test_weighted_median_follows_weights():
    assert weighted_quantile([(1, 1), (2, 1), (10, 5)], 0.5) == 10
    assert weighted_quantile([(1, 3), (2, 1), (10, 1)], 0.5) == 1


def test_first_ring_with_six_comps_is_used():
    pool = [comp(i, lat=41.9 + i * 0.001) for i in range(6)] + [comp(9, lat=41.95, price=900_000)]
    e = estimate(Target(41.9, -87.7, 3, AS_OF, kind="condo"), pool, Params(size_elasticity={}))
    assert e.ring == 0 and e.n == 6 and e.per_unit == 400_000


def test_falls_back_to_wider_ring_and_says_so():
    pool = [comp(i, lat=41.9 + 0.03 + i * 0.001) for i in range(6)]  # about 2 miles north
    e = estimate(Target(41.9, -87.7, 3, AS_OF, kind="condo"), pool, Params(size_elasticity={}))
    assert e.ring == 3 and e.radius_mi == 3.0


def test_old_sales_are_dropped():
    pool = [comp(i, sold=date(2021, 1, 1)) for i in range(6)] + [comp(9, price=500_000)]
    e = estimate(Target(41.9, -87.7, 3, AS_OF, kind="condo"), pool, Params(size_elasticity={}))
    assert e.n == 1 and e.per_unit == 500_000


def test_time_index_moves_price_to_estimate_year():
    idx = Index([("metro", "16984", 2024, q, 100) for q in (1, 2, 3, 4)]
                + [("metro", "16984", 2026, q, 110) for q in (1, 2, 3, 4)])  # fmt: skip
    pool = [comp(i, sold=date(2024, 5, 1)) for i in range(6)]
    e = estimate(Target(41.9, -87.7, 3, AS_OF, kind="condo"), pool, Params(size_elasticity={}), idx)
    assert round(e.per_unit) == 440_000 and e.index_used == {"metro": 6}


def test_condo_size_adjustment_and_building_factor():
    pool = [comp(i, sqft=1000) for i in range(6)]
    big = estimate(Target(41.9, -87.7, 3, AS_OF, 1440, kind="condo"), pool, Params())
    assert round(big.per_unit) == round(400_000 * 1.44**0.5)
    whole = estimate(Target(41.9, -87.7, 3, AS_OF, 1000), pool, Params(condo_to_building=0.7))
    assert round(whole.per_unit) == 280_000


def test_range_comes_from_the_fitted_band():
    p = params_from_files()
    pool = [comp(i) for i in range(6)]
    e = estimate(Target(41.9, -87.7, 3, AS_OF, 1200, kind="condo"), pool, p)
    lo, hi = p.band["0|condo"]
    assert e.low == e.per_unit * (1 + lo) and e.high == e.per_unit * (1 + hi) and e.low < e.per_unit < e.high

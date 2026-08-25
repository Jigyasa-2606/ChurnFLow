import numpy as np

from trainer.drift import matrix_from_redis_hashes, population_stability_index


def test_identical_distributions_have_near_zero_psi() -> None:
    rng = np.random.default_rng(0)
    values = rng.normal(size=500)
    psi = population_stability_index(values, values)
    assert psi < 0.05


def test_shifted_distribution_exceeds_threshold() -> None:
    rng = np.random.default_rng(0)
    reference = rng.normal(loc=0, scale=1, size=800)
    current = rng.normal(loc=3, scale=1, size=800)
    psi = population_stability_index(reference, current)
    assert psi > 0.20


def test_redis_hashes_keep_training_column_order() -> None:
    names = ["monetary_90d", "frequency_90d"]
    matrix = matrix_from_redis_hashes(
        [{"monetary_90d": "30", "frequency_90d": "2", "_features_version": "v1"}],
        names,
    )
    assert matrix.shape == (1, 2)
    assert list(matrix[0]) == [30.0, 2.0]

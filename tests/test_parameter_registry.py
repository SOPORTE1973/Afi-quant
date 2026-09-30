"""Tests del Parameter Registry (M22) — la propuesta de seis categorías."""

from __future__ import annotations

from afi_quant.registries.parameter_registry import CATEGORIES, PARAMETER_REGISTRY


def test_six_categories_proposed():
    assert len(CATEGORIES) == 6


def test_every_parameter_has_a_known_category():
    for p in PARAMETER_REGISTRY.parameters:
        assert p.category in CATEGORIES


def test_most_parameters_are_undeclared_values():
    # Solo los dos tramos de liquidez confirmados en la fuente llevan valor;
    # todo lo demás son declaraciones sin valor (el Comité las completa).
    undeclared = PARAMETER_REGISTRY.undeclared()
    assert len(undeclared) == len(PARAMETER_REGISTRY.parameters) - 2


def test_by_category_filters_correctly():
    liquidity_params = PARAMETER_REGISTRY.by_category("Horizontes y buckets de liquidez")
    assert len(liquidity_params) == 3
    assert {p.name for p in liquidity_params} == {
        "liquidity_bucket_short_days",
        "liquidity_bucket_medium_days",
        "min_lcr_ratio",
    }

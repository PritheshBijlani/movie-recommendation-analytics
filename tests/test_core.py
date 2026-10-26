"""Smoke tests for app/core.py. Run from the repo root:  python -m pytest tests -q"""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
import core  # noqa: E402


@pytest.fixture(scope="module")
def A():
    return core.load_artifacts(ROOT / "artifacts")


def test_lam_zero_returns_model_order(A):
    out = core.rerank_one(A["mit_idx"][0], A["mit_sc"][0], A["p"][0], A["Gn"], 0.0, 10)
    assert out.tolist() == A["mit_idx"][0][:10].astype(int).tolist()


def test_user_lists_valid(A):
    uid = int(A["users"][0])
    std, mit = core.user_lists(A, uid, 0.4)
    assert len(std) == len(mit) == 10 and len(set(mit.tolist())) == 10
    liked = set(A["hist"][A["user_pos"][uid]].indices.tolist())
    assert not liked & set(mit.tolist()), "recommended an already-liked title"


def test_group_shares_sum_to_one(A):
    assert abs(sum(core.demand_share(A).values()) - 1) < 1e-9
    assert abs(sum(core.list_share(A, np.arange(10)).values()) - 1) < 1e-9


def test_cold_start_picks(A):
    picks = A["items"].sort_values("train_count", ascending=False).item_idx.iloc[:6].tolist()
    std, mit, p = core.recommend_for_picks(A, picks, 0.4)
    assert len(std) == len(mit) == 10
    assert not set(picks) & (set(std.tolist()) | set(mit.tolist()))
    assert abs(p.sum() - 1) < 1e-5


def test_business_case_matches_results_json(A):
    ref = json.load(open(ROOT / "artifacts" / "results.json"))["business"]
    assert core.business_case(A["biz"])["net"] == pytest.approx(ref["net_base"], rel=1e-6)


def test_population_row(A):
    std, row = core.population_row(A, 0.4)
    assert row["lam"] == pytest.approx(0.4) and std["setting"] == "standard"

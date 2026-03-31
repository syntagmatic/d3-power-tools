#!/usr/bin/env python3
"""Build and evaluate a score-prediction discriminator from block features + tags.

Combines structural features (block-features.json), semantic tags (block-tags.json),
and audit scores (runs/ + iterations/) into a training dataset. Fits a baseline model
and reports feature importances.

Usage:
  python3 scripts/train-discriminator.py
  python3 scripts/train-discriminator.py --target composite
  python3 scripts/train-discriminator.py --target visual_critic
  python3 scripts/train-discriminator.py --out evals/discriminator.json
"""
import argparse
import json
import warnings
from pathlib import Path

import numpy as np

PROJ = Path(__file__).resolve().parent.parent
FEATURES_FILE = PROJ / "evals" / "block-features.json"
TAGS_FILE = PROJ / "evals" / "block-tags.json"
RUNS_DIR = PROJ / "evals" / "runs"
ITERATIONS_DIR = PROJ / "evals" / "iterations"

SCORE_DIMS = ["visual_critic", "encoding_integrity", "stress_test", "cognitive_load", "composite"]

# --- Data loading ---

def load_features():
    data = json.loads(FEATURES_FILE.read_text())
    return data.get("blocks", {})


def load_tags():
    data = json.loads(TAGS_FILE.read_text())
    return data.get("blocks", {})


def load_scores():
    """Collect all scored observations from runs and iterations."""
    observations = []  # list of (block_id, scores_dict, source)

    # From run files
    for f in sorted(RUNS_DIR.glob("*.json")):
        try:
            run = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        for bid, entry in run.get("blocks", {}).items():
            if entry.get("composite") is None:
                continue
            scores = {d: entry.get(d) for d in SCORE_DIMS if entry.get(d) is not None}
            if "composite" in scores:
                observations.append((bid, scores, f"run:{f.stem}"))

    # From iteration experiment files
    for f in sorted(ITERATIONS_DIR.glob("*.json")):
        try:
            exp = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        target = exp.get("target", "")
        exp_scores = exp.get("scores", {})

        # Baseline experiments have scores directly
        if exp.get("decision") == "baseline" and exp_scores.get("composite") is not None:
            scores = {d: exp_scores.get(d) for d in SCORE_DIMS if exp_scores.get(d) is not None}
            observations.append((target, scores, f"iter:{f.stem}:baseline"))

        # Keep/discard experiments have composite_after
        elif exp.get("composite_after") is not None:
            scores = {d: exp_scores.get(d) for d in SCORE_DIMS if exp_scores.get(d) is not None}
            if "composite" not in scores:
                scores["composite"] = exp["composite_after"]
            observations.append((target, scores, f"iter:{f.stem}:{exp.get('decision','')}"))

    return observations


# --- Feature engineering ---

DATA_SOURCE_MAP = {"inline": 0, "static-external": 1, "self-referential": 2, "live": 3}
RENDERER_MAP = {"svg": 0, "canvas": 1, "webgl": 2, "hybrid": 3}

INTERACTION_TYPES = ["brush", "zoom", "drag", "dispatch", "force"]

FEATURE_NAMES = [
    # Structural (from block-features.json)
    "lines", "d3_api_count", "scale_count", "event_handler_count", "function_count",
    "renderer_svg", "renderer_canvas", "renderer_webgl", "renderer_hybrid",
    "has_transition", "has_raf", "has_timer",
    "interaction_brush", "interaction_zoom", "interaction_drag",
    "interaction_dispatch", "interaction_force",
    "n_layouts", "n_generators", "n_scales",
    "has_geo", "has_aria", "has_resize_observer", "has_reduced_motion",
    "has_container_query", "n_external_libs", "has_fetch",
    # Semantic (from block-tags.json)
    "compositional_ambition", "encoding_density", "encoding_count",
    "data_source_inline", "data_source_static", "data_source_selfref", "data_source_live",
]


def featurize(block_id, features, tags):
    """Convert a block's features + tags into a numeric feature vector."""
    f = features.get(block_id, {})
    t = tags.get(block_id, {}).get("tags", {})

    if not f or not t:
        return None

    renderer = f.get("renderer", "svg")
    interactions = set(f.get("interactions", []))
    ds = t.get("data_source", "inline")

    vec = [
        f.get("lines", 0),
        f.get("d3_api_count", 0),
        f.get("scale_count", 0),
        f.get("event_handler_count", 0),
        f.get("function_count", 0),
        int(renderer == "svg"),
        int(renderer == "canvas"),
        int(renderer == "webgl"),
        int(renderer == "hybrid"),
        int(f.get("has_transition", False)),
        int(f.get("has_raf", False)),
        int(f.get("has_timer", False)),
        int("brush" in interactions),
        int("zoom" in interactions),
        int("drag" in interactions),
        int("dispatch" in interactions),
        int("force" in interactions),
        len(f.get("d3_layouts", [])),
        len(f.get("d3_generators", [])),
        len(f.get("d3_scales", [])),
        int(f.get("has_geo", False)),
        int(f.get("has_aria", False)),
        int(f.get("has_resize_observer", False)),
        int(f.get("has_reduced_motion", False)),
        int(f.get("has_container_query", False)),
        len(f.get("external_libs", [])),
        int(f.get("has_fetch", False)),
        t.get("compositional_ambition", 0),
        t.get("encoding_density", 0),
        t.get("encoding_count", 0),
        int(ds == "inline"),
        int(ds == "static-external"),
        int(ds == "self-referential"),
        int(ds == "live"),
    ]
    return vec


# --- Model ---

def fit_linear(X, y):
    """Ordinary least squares with L2 regularization (ridge). No sklearn needed."""
    X = np.array(X, dtype=np.float64)
    y = np.array(y, dtype=np.float64)

    # Standardize features
    mu = X.mean(axis=0)
    sigma = X.std(axis=0)
    sigma[sigma == 0] = 1.0
    Xs = (X - mu) / sigma

    # Add intercept
    ones = np.ones((Xs.shape[0], 1))
    Xs = np.hstack([ones, Xs])

    # Ridge regression (alpha=1.0)
    alpha = 1.0
    I = np.eye(Xs.shape[1])
    I[0, 0] = 0  # don't regularize intercept
    w = np.linalg.solve(Xs.T @ Xs + alpha * I, Xs.T @ y)

    y_hat = Xs @ w
    residuals = y - y_hat
    ss_res = (residuals ** 2).sum()
    ss_tot = ((y - y.mean()) ** 2).sum()
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

    # Feature importances = |standardized coefficients|
    coefs = w[1:]  # skip intercept
    importances = np.abs(coefs)

    return {
        "weights": w.tolist(),
        "mu": mu.tolist(),
        "sigma": sigma.tolist(),
        "r2": float(r2),
        "rmse": float(np.sqrt(ss_res / len(y))),
        "n": len(y),
        "coefs": coefs.tolist(),
        "importances": importances.tolist(),
    }


def cross_validate(X, y, k=5):
    """k-fold cross-validation, returns mean R² and RMSE."""
    X = np.array(X, dtype=np.float64)
    y = np.array(y, dtype=np.float64)
    n = len(y)
    indices = np.arange(n)
    np.random.seed(42)
    np.random.shuffle(indices)
    folds = np.array_split(indices, k)

    r2s, rmses = [], []
    for i in range(k):
        test_idx = folds[i]
        train_idx = np.concatenate([folds[j] for j in range(k) if j != i])
        X_train, y_train = X[train_idx], y[train_idx]
        X_test, y_test = X[test_idx], y[test_idx]

        mu = X_train.mean(axis=0)
        sigma = X_train.std(axis=0)
        sigma[sigma == 0] = 1.0

        Xs_train = np.hstack([np.ones((len(X_train), 1)), (X_train - mu) / sigma])
        Xs_test = np.hstack([np.ones((len(X_test), 1)), (X_test - mu) / sigma])

        I = np.eye(Xs_train.shape[1])
        I[0, 0] = 0
        w = np.linalg.solve(Xs_train.T @ Xs_train + I, Xs_train.T @ y_train)

        y_hat = Xs_test @ w
        ss_res = ((y_test - y_hat) ** 2).sum()
        ss_tot = ((y_test - y_test.mean()) ** 2).sum()
        r2s.append(1 - ss_res / ss_tot if ss_tot > 0 else 0)
        rmses.append(float(np.sqrt(ss_res / len(y_test))))

    return float(np.mean(r2s)), float(np.mean(rmses))


# --- Main ---

def main():
    ap = argparse.ArgumentParser(description="Train score-prediction discriminator")
    ap.add_argument("--target", default="composite", help="Score dimension to predict")
    ap.add_argument("--out", default=None, help="Write model + results to JSON")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    features = load_features()
    tags = load_tags()
    observations = load_scores()

    print(f"Loaded {len(observations)} scored observations")
    print(f"Features for {len(features)} blocks, tags for {len(tags)} blocks")

    # Aggregate scores per block: use median across all observations
    from collections import defaultdict
    block_scores = defaultdict(list)
    for bid, scores, source in observations:
        if args.target in scores:
            block_scores[bid].append(scores[args.target])

    print(f"Blocks with '{args.target}' scores: {len(block_scores)}")

    # Build training matrix
    X, y, block_ids = [], [], []
    for bid, score_list in block_scores.items():
        vec = featurize(bid, features, tags)
        if vec is None:
            continue
        X.append(vec)
        y.append(float(np.median(score_list)))
        block_ids.append(bid)

    print(f"Training matrix: {len(X)} blocks × {len(FEATURE_NAMES)} features")
    print(f"Target '{args.target}': min={min(y):.1f} max={max(y):.1f} mean={np.mean(y):.2f} std={np.std(y):.2f}")
    print()

    if len(X) < 10:
        print("Not enough data to train. Run more audits first.")
        return

    # Fit model on all data
    model = fit_linear(X, y)
    print(f"=== Ridge Regression (all data) ===")
    print(f"R²: {model['r2']:.3f}")
    print(f"RMSE: {model['rmse']:.3f}")

    # Cross-validate
    cv_r2, cv_rmse = cross_validate(X, y, k=min(5, len(X) // 3))
    print(f"\n=== 5-fold Cross-Validation ===")
    print(f"R² (CV): {cv_r2:.3f}")
    print(f"RMSE (CV): {cv_rmse:.3f}")

    # Feature importances
    imp = list(zip(FEATURE_NAMES, model["importances"], model["coefs"]))
    imp.sort(key=lambda x: -x[1])
    print(f"\n=== Feature Importances (|standardized coef|) ===")
    for name, importance, coef in imp[:15]:
        direction = "+" if coef > 0 else "-"
        print(f"  {direction} {name:30s} {importance:.3f}")

    # Worst predictions (biggest residuals)
    X_arr = np.array(X, dtype=np.float64)
    y_arr = np.array(y, dtype=np.float64)
    mu, sigma = np.array(model["mu"]), np.array(model["sigma"])
    Xs = np.hstack([np.ones((len(X_arr), 1)), (X_arr - mu) / sigma])
    y_hat = Xs @ np.array(model["weights"])
    residuals = y_arr - y_hat
    worst = np.argsort(np.abs(residuals))[::-1][:10]
    print(f"\n=== Worst Predictions ===")
    for i in worst:
        print(f"  {block_ids[i]:40s} actual={y[i]:.1f} predicted={y_hat[i]:.1f} error={residuals[i]:+.1f}")

    # Save results
    if args.out:
        result = {
            "target": args.target,
            "n_observations": len(observations),
            "n_training": len(X),
            "feature_names": FEATURE_NAMES,
            "model": {
                "type": "ridge_regression",
                "weights": model["weights"],
                "mu": model["mu"],
                "sigma": model["sigma"],
            },
            "metrics": {
                "r2": model["r2"],
                "rmse": model["rmse"],
                "cv_r2": cv_r2,
                "cv_rmse": cv_rmse,
            },
            "feature_importances": {name: {"importance": imp, "coef": coef}
                                     for name, imp, coef in zip(FEATURE_NAMES, model["importances"], model["coefs"])},
            "predictions": {bid: {"actual": float(y[i]), "predicted": float(y_hat[i])}
                           for i, bid in enumerate(block_ids)},
        }
        Path(args.out).write_text(json.dumps(result, indent=2, ensure_ascii=False))
        print(f"\nSaved to {args.out}")


if __name__ == "__main__":
    main()

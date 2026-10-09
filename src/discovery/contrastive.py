
"""Contrastive activation-based failure-axis discovery."""

from __future__ import annotations
import numpy as np


def standardized_mean_difference(
    failure_activations: np.ndarray,
    success_activations: np.ndarray,
) -> np.ndarray:
    """Measure how differently each feature activates during failures."""

    if failure_activations.ndim != 2 or success_activations.ndim != 2:
        raise ValueError("Activations must be 2D arrays")

    if failure_activations.shape[1] != success_activations.shape[1]:
        raise ValueError("Feature dimensions must match")

    if len(failure_activations) == 0 or len(success_activations) == 0:
        raise ValueError("Both groups must contain observations")

    failure_mean = np.mean(failure_activations, axis=0)
    success_mean = np.mean(success_activations, axis=0)

    success_std = np.std(success_activations, axis=0)
    success_std = np.maximum(success_std, 1e-8)

    return (failure_mean - success_mean) / success_std


def firing_rate_log_odds(
    failure_activations: np.ndarray,
    success_activations: np.ndarray,
    threshold: float = 0.0,
) -> np.ndarray:
    """Compare how often each feature fires in failures vs successes."""

    if failure_activations.ndim != 2 or success_activations.ndim != 2:
        raise ValueError("Activations must be 2D arrays")

    if failure_activations.shape[1] != success_activations.shape[1]:
        raise ValueError("Feature dimensions must match")

    if len(failure_activations) == 0 or len(success_activations) == 0:
        raise ValueError("Both groups must contain observations")

    failure_rate = np.mean(failure_activations > threshold, axis=0)
    success_rate = np.mean(success_activations > threshold, axis=0)

    eps = 1e-6

    failure_rate = np.clip(failure_rate, eps, 1 - eps)
    success_rate = np.clip(success_rate, eps, 1 - eps)

    failure_log_odds = np.log(failure_rate / (1 - failure_rate))
    success_log_odds = np.log(success_rate / (1 - success_rate))

    return failure_log_odds - success_log_odds


from scipy.stats import false_discovery_control


def select_significant_features(
    p_values: np.ndarray,
    q_threshold: float = 0.05,
) -> np.ndarray:
    """Select features using Benjamini-Hochberg FDR correction."""

    p_values = np.asarray(p_values, dtype=float)

    if p_values.ndim != 1:
        raise ValueError("p_values must be a 1D array")

    if not np.all(np.isfinite(p_values)):
        raise ValueError("p_values must be finite")

    if np.any((p_values < 0) | (p_values > 1)):
        raise ValueError("p_values must be between 0 and 1")

    if not 0 < q_threshold < 1:
        raise ValueError("q_threshold must be between 0 and 1")

    if p_values.size == 0:
        return np.array([], dtype=bool)

    adjusted_p = false_discovery_control(
        p_values, method="bh"
    )

    return adjusted_p < q_threshold


from scipy.stats import ttest_ind


def rollout_level_pvalues(
    failure_rollouts: list[np.ndarray],
    success_rollouts: list[np.ndarray],
) -> np.ndarray:
    """Compare feature means across independent driving rollouts."""

    if len(failure_rollouts) < 2 or len(success_rollouts) < 2:
        raise ValueError("Need at least 2 rollouts per group")

    all_rollouts = failure_rollouts + success_rollouts
    n_features = all_rollouts[0].shape[1]

    for rollout in all_rollouts:
        if (
            rollout.ndim != 2
            or rollout.shape[0] == 0
            or rollout.shape[1] != n_features
            or not np.all(np.isfinite(rollout))
        ):
            raise ValueError("Invalid rollout activation matrix")

    failure_means = np.stack([
        rollout.mean(axis=0) for rollout in failure_rollouts
    ])

    success_means = np.stack([
        rollout.mean(axis=0) for rollout in success_rollouts
    ])

    result = ttest_ind(
        failure_means,
        success_means,
        axis=0,
        equal_var=False,
    )

    return np.where(np.isnan(result.pvalue), 1.0, result.pvalue)


def feature_rollout_support(
    rollouts: list[np.ndarray],
    threshold: float = 0.0,
) -> np.ndarray:
    """Count distinct rollouts where each feature activates."""

    if not rollouts:
        raise ValueError("At least one rollout is required")

    n_features = rollouts[0].shape[1]

    support = np.zeros(n_features, dtype=int)

    for rollout in rollouts:
        if (
            rollout.ndim != 2
            or rollout.shape[0] == 0
            or rollout.shape[1] != n_features
            or not np.all(np.isfinite(rollout))
        ):
            raise ValueError("Invalid rollout activation matrix")

        fires = np.any(rollout > threshold, axis=0)
        support += fires.astype(int)

    return support


def apply_support_filter(
    significant: np.ndarray,
    support: np.ndarray,
    min_rollouts: int = 20,
) -> np.ndarray:
    """Keep significant features supported by enough rollouts."""

    if significant.shape != support.shape:
        raise ValueError("Shapes must match")

    if min_rollouts < 1:
        raise ValueError("min_rollouts must be positive")

    return significant & (support >= min_rollouts)


def group_cofiring_features(
    activations: np.ndarray,
    selected_features: np.ndarray,
    correlation_threshold: float = 0.7,
) -> list[list[int]]:
    """Group selected features with strongly correlated activations."""

    if activations.ndim != 2:
        raise ValueError("Activations must be a 2D array")

    if selected_features.shape != (activations.shape[1],):
        raise ValueError("Selected features must match activation dimensions")

    if not 0 <= correlation_threshold <= 1:
        raise ValueError("Correlation threshold must be between 0 and 1")

    indices = np.flatnonzero(selected_features)

    if len(indices) == 0:
        return []

    if len(indices) == 1:
        return [[int(indices[0])]]

    selected = activations[:, indices]

    correlations = np.corrcoef(selected, rowvar=False)
    correlations = np.nan_to_num(correlations, nan=0.0)

    groups = []
    visited = set()

    for i in range(len(indices)):
        if i in visited:
            continue

        stack = [i]
        component = []

        while stack:
            current = stack.pop()

            if current in visited:
                continue

            visited.add(current)
            component.append(int(indices[current]))

            neighbors = np.flatnonzero(
                correlations[current] >= correlation_threshold
            )

            for neighbor in neighbors:
                if int(neighbor) not in visited:
                    stack.append(int(neighbor))

        groups.append(sorted(component))

    return groups



def rank_candidate_axes(
    groups: list[list[int]],
    effect_sizes: np.ndarray,
    support: np.ndarray,
    axis_support: list[int] | None = None,
) -> list[dict]:
    """Rank candidate axes by effect size times rollout support."""

    if effect_sizes.shape != support.shape:
        raise ValueError("Effect sizes and support must match")

    if axis_support is not None and len(axis_support) != len(groups):
        raise ValueError("Axis support must match number of groups")

    candidates = []

    for i, group in enumerate(groups):
        if not group:
            continue

        if any(j < 0 or j >= len(effect_sizes) for j in group):
            raise ValueError("Feature index out of bounds")

        group_effect = float(np.mean(np.abs(effect_sizes[group])))

        group_support = (
            int(axis_support[i])
            if axis_support is not None
            else int(np.max(support[group]))
        )

        candidates.append({
            "features": group,
            "effect_size": group_effect,
            "support": group_support,
            "score": group_effect * group_support,
        })

    return sorted(candidates, key=lambda x: x["score"], reverse=True)



from harness.schema import AxisCard, Directive


def build_directive(
    ranked_candidates: list[dict],
    descriptions: dict[int, tuple[str, str]],
    budget_m: int = 10,
) -> Directive:
    """Create AxisCards for candidates with reviewed descriptions."""

    if budget_m < 1:
        raise ValueError("budget_m must be positive")

    axes = []

    for candidate_index, candidate in enumerate(ranked_candidates):
        if candidate_index not in descriptions:
            continue

        name, description = descriptions[candidate_index]

        if not name.strip() or not description.strip():
            raise ValueError("Axis name and description cannot be empty")

        axis = AxisCard(
            axis_id=f"contrastive_{candidate_index}",
            name=name,
            description=description,
            rank=len(axes) + 1,
            score=float(candidate["score"]),
            method="contrastive",
            aggregation="mean_abs_effect_x_axis_support",
            parameterization={
                "feature_indices": candidate["features"],
                "prototype": True,
            },
        )

        axis.validate()
        axes.append(axis)

        if len(axes) >= budget_m:
            break

    directive = Directive(
        method="contrastive",
        axes=axes,
        budget_m=budget_m,
    )

    directive.validate()
    return directive


def discover_candidate_axes(
    failure_rollouts: list[np.ndarray],
    success_rollouts: list[np.ndarray],
    q_threshold: float = 0.05,
    min_rollouts: int = 20,
    correlation_threshold: float = 0.7,
) -> list[dict]:
    """Discover candidate failure axes from rollout activations."""

    # 1. Validate rollout-level inputs and calculate p-values.
    p_values = rollout_level_pvalues(
        failure_rollouts,
        success_rollouts,
    )

    # 2. Apply false discovery rate correction.
    significant = select_significant_features(
        p_values,
        q_threshold=q_threshold,
    )

    # 3. Count distinct failure rollouts supporting each feature.
    support = feature_rollout_support(failure_rollouts)

    # 4. Keep significant features with sufficient support.
    selected = apply_support_filter(
        significant,
        support,
        min_rollouts=min_rollouts,
    )

    if not np.any(selected):
        return []

    # 5. Compute effect sizes using rollout-level means.
    failure_means = np.stack([
        rollout.mean(axis=0) for rollout in failure_rollouts
    ])
    success_means = np.stack([
        rollout.mean(axis=0) for rollout in success_rollouts
    ])

    effects = standardized_mean_difference(
        failure_means,
        success_means,
    )

    # 6. Group features using one observation per rollout.
    all_means = np.concatenate(
        [failure_means, success_means],
        axis=0,
    )

    groups = group_cofiring_features(
        all_means,
        selected,
        correlation_threshold=correlation_threshold,
    )

    # 7. Count distinct failure rollouts supporting each axis.
    group_support = axis_rollout_support(
        failure_rollouts,
        groups,
    )

    # 8. Rank axes using their actual support.
    return rank_candidate_axes(
        groups,
        effects,
        support,
        axis_support=group_support,
    )



def axis_rollout_support(
    failure_rollouts: list[np.ndarray],
    groups: list[list[int]],
    threshold: float = 0.0,
) -> list[int]:
    """Count distinct failure rollouts supporting each axis."""

    if not failure_rollouts:
        raise ValueError("At least one failure rollout is required")

    n_features = failure_rollouts[0].shape[1]
    support = []

    for group in groups:
        if not group:
            raise ValueError("Axis groups cannot be empty")

        if any(i < 0 or i >= n_features for i in group):
            raise ValueError("Feature index out of bounds")

        count = 0

        for rollout in failure_rollouts:
            if (
                rollout.ndim != 2
                or rollout.shape[0] == 0
                or rollout.shape[1] != n_features
                or not np.all(np.isfinite(rollout))
            ):
                raise ValueError("Invalid rollout activation matrix")

            if np.any(rollout[:, group] > threshold):
                count += 1

        support.append(count)

    return support

"""Static report figures (matplotlib, PNG)."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e4e3df"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]  # fixed categorical order: blue, orange, aqua


def _style(ax: plt.Axes) -> None:
    ax.set_facecolor(SURFACE)
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(INK_2)
    ax.tick_params(colors=INK_2)


def plot_calibration(tables: dict[str, pd.DataFrame], title: str, path: Path) -> None:
    """Reliability plot: mean predicted vs observed default rate per score decile."""
    fig, ax = plt.subplots(figsize=(5.5, 5), facecolor=SURFACE)
    _style(ax)
    hi = max(max(t["mean_pred"].max(), t["observed"].max()) for t in tables.values()) * 1.08
    ax.plot([0, hi], [0, hi], color=INK_2, linewidth=1, linestyle="--", label="perfect")
    for (name, t), color in zip(tables.items(), SERIES, strict=False):
        ax.plot(t["mean_pred"], t["observed"], color=color, linewidth=2, marker="o",
                markersize=6, markeredgecolor=SURFACE, markeredgewidth=1.5, label=name)  # fmt: skip
    ax.set_xlim(0, hi)
    ax.set_ylim(0, hi)
    ax.set_xlabel("Mean predicted PD (score decile)", color=INK)
    ax.set_ylabel("Observed default rate", color=INK)
    ax.set_title(title, color=INK, loc="left")
    ax.legend(frameon=False, labelcolor=INK)
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)


def plot_gini_by_period(table: pd.DataFrame, title: str, path: Path) -> None:
    t = table.dropna(subset=["gini"])
    fig, ax = plt.subplots(figsize=(6, 4), facecolor=SURFACE)
    _style(ax)
    x = range(len(t))
    ax.errorbar(x, t["gini"], yerr=[t["gini"] - t["ci_low"], t["ci_high"] - t["gini"]],
                fmt="o", color=SERIES[0], ecolor=SERIES[0], elinewidth=2, capsize=4,
                markersize=8, markeredgecolor=SURFACE)  # fmt: skip
    for xi, (_, r) in zip(x, t.iterrows(), strict=True):
        ax.annotate(f"{r['gini']:.3f}\nn={r['n']:,}", (xi, r["ci_high"]), xytext=(0, 6),
                    textcoords="offset points", ha="center", fontsize=8, color=INK_2)  # fmt: skip
    ax.set_xticks(list(x), t["period"])
    ax.set_xlim(-0.6, len(t) - 0.4)
    ax.set_ylabel("Gini (95% bootstrap CI)", color=INK)
    ax.set_title(title, color=INK, loc="left")
    ax.margins(y=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)


def plot_shap_by_value(table: pd.DataFrame, title: str, path: Path) -> None:
    """Horizontal bars of mean SHAP per (LLM feature, value). Orange raises PD, blue lowers it."""
    t = table.copy()
    t["label"] = t["feature"].str.removeprefix("llm_") + " = " + t["value"]
    t = t.iloc[::-1]  # matplotlib draws bottom-up; keep feature order top-down
    fig, ax = plt.subplots(figsize=(7.5, 0.28 * len(t) + 1.2), facecolor=SURFACE)
    _style(ax)
    ax.grid(True, axis="x", color=GRID, linewidth=0.8)
    ax.grid(False, axis="y")
    colors = [SERIES[1] if v > 0 else SERIES[0] for v in t["mean_shap"]]
    ax.barh(t["label"], t["mean_shap"], color=colors, height=0.7, edgecolor=SURFACE, linewidth=1)
    ax.axvline(0, color=INK_2, linewidth=1)
    for y, (_, r) in enumerate(t.iterrows()):
        right = r["mean_shap"] >= 0
        ax.annotate(f"n={r['n']:,}", (r["mean_shap"], y), xytext=(4 if right else -4, 0),
                    textcoords="offset points", va="center", fontsize=7, color=INK_2,
                    ha="left" if right else "right")  # fmt: skip
    ax.set_xlabel("Mean SHAP, log-odds of default\n(orange raises PD, blue lowers it)", color=INK)
    ax.tick_params(axis="y", labelsize=8)
    ax.set_title(title, color=INK, loc="left")
    ax.margins(x=0.15)
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)

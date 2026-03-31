"""
Results Analysis and Visualization

Analyzes experiment results and generates publication-ready figures.
"""

import json
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import argparse

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class AnalysisResult:
    """Aggregated analysis results."""
    
    # Overall metrics
    total_experiments: int
    sabotage_rate: float
    overall_evasion_rate: float
    
    # By naturalness level
    evasion_by_naturalness: dict[int, float]
    
    # By monitor
    evasion_by_monitor: dict[str, float]
    
    # By task
    evasion_by_task: dict[str, float]
    
    # Cross-model comparison
    claude_vs_gpt: Optional[dict] = None


def load_results(results_dir: str) -> list[dict]:
    """Load all experiment results from directory."""
    results_path = Path(results_dir)
    results = []
    
    for filepath in results_path.glob("*.json"):
        if filepath.name.startswith("summary"):
            continue
        with open(filepath) as f:
            results.append(json.load(f))
    
    return results


def analyze_results(results: list[dict]) -> AnalysisResult:
    """Compute analysis statistics from results."""
    
    total = len(results)
    if total == 0:
        raise ValueError("No results to analyze")
    
    # Filter valid results
    valid = [r for r in results if r.get("suspicion_score", -1) >= 0]
    sabotaged = [r for r in valid if r.get("sabotage_inserted", False)]
    evaded = [r for r in sabotaged if r.get("evaded", False)]
    
    # Overall rates
    sabotage_rate = len(sabotaged) / len(valid) if valid else 0
    evasion_rate = len(evaded) / len(sabotaged) if sabotaged else 0
    
    # By naturalness
    evasion_by_naturalness = {}
    for nat_level in range(1, 6):
        nat_results = [r for r in sabotaged if r.get("task_naturalness") == nat_level]
        nat_evaded = [r for r in nat_results if r.get("evaded")]
        evasion_by_naturalness[nat_level] = len(nat_evaded) / len(nat_results) if nat_results else 0
    
    # By monitor
    evasion_by_monitor = {}
    monitors = set(r.get("monitor_id") for r in results if r.get("monitor_id"))
    for monitor in monitors:
        mon_results = [r for r in sabotaged if r.get("monitor_id") == monitor]
        mon_evaded = [r for r in mon_results if r.get("evaded")]
        evasion_by_monitor[monitor] = len(mon_evaded) / len(mon_results) if mon_results else 0
    
    # By task
    evasion_by_task = {}
    tasks = set(r.get("task_id") for r in results if r.get("task_id"))
    for task in tasks:
        task_results = [r for r in sabotaged if r.get("task_id") == task]
        task_evaded = [r for r in task_results if r.get("evaded")]
        evasion_by_task[task] = len(task_evaded) / len(task_results) if task_results else 0
    
    # Cross-model comparison
    claude_vs_gpt = None
    claude_results = [r for r in sabotaged if "claude" in r.get("monitor_id", "")]
    gpt_results = [r for r in sabotaged if "gpt" in r.get("monitor_id", "")]
    
    if claude_results and gpt_results:
        claude_evaded = sum(1 for r in claude_results if r.get("evaded"))
        gpt_evaded = sum(1 for r in gpt_results if r.get("evaded"))
        claude_vs_gpt = {
            "claude_evasion_rate": claude_evaded / len(claude_results),
            "gpt_evasion_rate": gpt_evaded / len(gpt_results),
            "difference": (claude_evaded / len(claude_results)) - (gpt_evaded / len(gpt_results))
        }
    
    return AnalysisResult(
        total_experiments=total,
        sabotage_rate=sabotage_rate,
        overall_evasion_rate=evasion_rate,
        evasion_by_naturalness=evasion_by_naturalness,
        evasion_by_monitor=evasion_by_monitor,
        evasion_by_task=evasion_by_task,
        claude_vs_gpt=claude_vs_gpt
    )


def print_analysis(analysis: AnalysisResult):
    """Print analysis results to console."""
    print("\n" + "=" * 60)
    print("ANALYSIS RESULTS")
    print("=" * 60)
    
    print(f"\nTotal experiments: {analysis.total_experiments}")
    print(f"Sabotage insertion rate: {100*analysis.sabotage_rate:.1f}%")
    print(f"Overall evasion rate: {100*analysis.overall_evasion_rate:.1f}%")
    
    print("\n--- Evasion by Naturalness Level ---")
    naturalness_names = {
        5: "VERY_HIGH",
        4: "HIGH", 
        3: "MEDIUM",
        2: "LOW",
        1: "VERY_LOW"
    }
    for level in sorted(analysis.evasion_by_naturalness.keys(), reverse=True):
        rate = analysis.evasion_by_naturalness[level]
        name = naturalness_names.get(level, str(level))
        bar = "█" * int(rate * 20)
        print(f"  {name:12} ({level}): {100*rate:5.1f}% {bar}")
    
    print("\n--- Evasion by Task ---")
    for task, rate in sorted(analysis.evasion_by_task.items(), key=lambda x: -x[1]):
        bar = "█" * int(rate * 20)
        print(f"  {task:20}: {100*rate:5.1f}% {bar}")
    
    print("\n--- Evasion by Monitor ---")
    for monitor, rate in sorted(analysis.evasion_by_monitor.items(), key=lambda x: -x[1]):
        bar = "█" * int(rate * 20)
        print(f"  {monitor:15}: {100*rate:5.1f}% {bar}")
    
    if analysis.claude_vs_gpt:
        print("\n--- Cross-Model Comparison ---")
        print(f"  Claude evasion rate: {100*analysis.claude_vs_gpt['claude_evasion_rate']:.1f}%")
        print(f"  GPT-4 evasion rate:  {100*analysis.claude_vs_gpt['gpt_evasion_rate']:.1f}%")
        diff = analysis.claude_vs_gpt['difference']
        if abs(diff) < 0.05:
            print("  → Similar vulnerability to semantic naturalness")
        elif diff > 0:
            print(f"  → Claude more vulnerable by {100*diff:.1f} percentage points")
        else:
            print(f"  → GPT-4 more vulnerable by {100*-diff:.1f} percentage points")


def generate_figures(analysis: AnalysisResult, output_dir: str):
    """Generate publication-ready figures."""
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
    except ImportError:
        print("matplotlib/seaborn not installed. Skipping figure generation.")
        return
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Set style
    sns.set_style("whitegrid")
    plt.rcParams['figure.figsize'] = (10, 6)
    
    # Figure 1: Evasion by Naturalness
    fig, ax = plt.subplots()
    naturalness_names = ["VERY_LOW", "LOW", "MEDIUM", "HIGH", "VERY_HIGH"]
    rates = [analysis.evasion_by_naturalness.get(i, 0) * 100 for i in range(1, 6)]
    colors = sns.color_palette("RdYlGn", 5)
    
    bars = ax.bar(naturalness_names, rates, color=colors)
    ax.set_ylabel("Evasion Rate (%)")
    ax.set_xlabel("Indicator Naturalness")
    ax.set_title("Evasion Rate by Sabotage Indicator Naturalness")
    ax.set_ylim(0, 100)
    
    for bar, rate in zip(bars, rates):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                f"{rate:.0f}%", ha='center', va='bottom', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_path / "evasion_by_naturalness.png", dpi=150)
    plt.close()
    
    # Figure 2: Cross-Model Comparison
    if analysis.claude_vs_gpt:
        fig, ax = plt.subplots()
        models = ["Claude", "GPT-4"]
        rates = [
            analysis.claude_vs_gpt["claude_evasion_rate"] * 100,
            analysis.claude_vs_gpt["gpt_evasion_rate"] * 100
        ]
        
        bars = ax.bar(models, rates, color=["#7C3AED", "#10B981"])
        ax.set_ylabel("Evasion Rate (%)")
        ax.set_title("Cross-Model Evasion Comparison")
        ax.set_ylim(0, max(rates) * 1.3)
        
        for bar, rate in zip(bars, rates):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                    f"{rate:.1f}%", ha='center', va='bottom', fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(output_path / "cross_model_comparison.png", dpi=150)
        plt.close()
    
    print(f"\nFigures saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Analyze experiment results")
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        default="results",
        help="Results directory"
    )
    
    parser.add_argument(
        "--output", "-o", 
        type=str,
        default="figures",
        help="Output directory for figures"
    )
    
    parser.add_argument(
        "--figures",
        action="store_true",
        help="Generate figures"
    )
    
    args = parser.parse_args()
    
    # Load and analyze
    print(f"Loading results from: {args.input}")
    results = load_results(args.input)
    
    if not results:
        print("No results found!")
        return
    
    print(f"Loaded {len(results)} experiments")
    
    analysis = analyze_results(results)
    print_analysis(analysis)
    
    if args.figures:
        generate_figures(analysis, args.output)


if __name__ == "__main__":
    main()

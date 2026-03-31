"""
Experiment Runner

Orchestrates sabotage generation, monitoring, and result collection.
Supports both single experiments and full matrix runs.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sabotage_tasks import get_task, get_all_tasks, SabotageTask
from monitors import get_monitor, MonitorResult
from attackers import SabotageGenerator, ReferenceGenerator, AttackerResult


@dataclass
class ExperimentResult:
    """Complete result from a single experiment run."""
    
    # Experiment identification
    experiment_id: str
    timestamp: str
    
    # Configuration
    task_id: str
    task_naturalness: int
    monitor_id: str
    prompt_type: str
    run_number: int
    
    # Attacker results
    sabotage_inserted: bool
    attacker_technique: str
    generated_code: str
    
    # Monitor results
    suspicion_score: float
    monitor_analysis: str
    flagged: bool
    evaded: bool
    
    # Differential monitoring (if applicable)
    differential_score: Optional[float] = None
    differential_flagged: Optional[bool] = None
    
    # Errors
    attacker_error: Optional[str] = None
    monitor_error: Optional[str] = None


class ExperimentRunner:
    """Runs evasion experiments with configurable parameters."""
    
    def __init__(
        self,
        results_dir: str = "results",
        save_raw: bool = True
    ):
        """
        Initialize experiment runner.
        
        Args:
            results_dir: Directory to save results
            save_raw: Whether to save raw API responses
        """
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True)
        self.save_raw = save_raw
        
        # Initialize generators
        self.attacker = SabotageGenerator()
        self.reference_gen = ReferenceGenerator()
    
    def run_single(
        self,
        task_id: str,
        monitor_id: str,
        prompt_type: str = "generic",
        run_differential: bool = False,
        run_number: int = 1
    ) -> ExperimentResult:
        """
        Run a single experiment.
        
        Args:
            task_id: Sabotage task to attempt
            monitor_id: Monitor to use for detection
            prompt_type: "generic" or "specific"
            run_differential: Whether to also run differential monitoring
            run_number: Run number for this configuration
            
        Returns:
            ExperimentResult with all data
        """
        task = get_task(task_id)
        monitor = get_monitor(monitor_id)
        
        experiment_id = f"{task_id}_{monitor_id}_{prompt_type}_{run_number}_{datetime.now().strftime('%H%M%S')}"
        
        print(f"  [Attacker] Generating sabotaged code for {task_id}...")
        
        # Step 1: Generate sabotaged code
        attacker_result = self.attacker.generate(task)
        
        if attacker_result.error:
            print(f"  [ERROR] Attacker failed: {attacker_result.error}")
            return ExperimentResult(
                experiment_id=experiment_id,
                timestamp=datetime.now().isoformat(),
                task_id=task_id,
                task_naturalness=task.naturalness.value,
                monitor_id=monitor_id,
                prompt_type=prompt_type,
                run_number=run_number,
                sabotage_inserted=False,
                attacker_technique="",
                generated_code="",
                suspicion_score=-1.0,
                monitor_analysis="",
                flagged=False,
                evaded=False,
                attacker_error=attacker_result.error
            )
        
        sab_status = "✓ inserted" if attacker_result.sabotage_inserted else "✗ not inserted"
        print(f"  [Attacker] Sabotage {sab_status}")
        
        # Step 2: Monitor reviews the code
        print(f"  [Monitor] {monitor_id} reviewing with {prompt_type} prompt...")
        
        monitor_result = monitor.review(
            code=attacker_result.code,
            prompt_type=prompt_type,
            task_description=task.legitimate_task
        )
        
        if monitor_result.error:
            print(f"  [ERROR] Monitor failed: {monitor_result.error}")
        else:
            status = "FLAGGED" if monitor_result.flagged else "PASSED"
            print(f"  [Monitor] Score: {monitor_result.score:.1f} → {status}")
        
        # Step 3: Differential monitoring (optional)
        differential_score = None
        differential_flagged = None
        
        if run_differential and not monitor_result.error:
            print(f"  [Differential] Generating reference and comparing...")
            reference_code = self.reference_gen.generate(task)
            diff_result = monitor.review_differential(
                submitted_code=attacker_result.code,
                reference_code=reference_code,
                task_description=task.legitimate_task
            )
            differential_score = diff_result.score
            differential_flagged = diff_result.flagged
            print(f"  [Differential] Score: {diff_result.score:.1f}")
        
        # Determine if evasion succeeded
        evaded = (
            attacker_result.sabotage_inserted 
            and monitor_result.evaded 
            and not monitor_result.error
        )
        
        return ExperimentResult(
            experiment_id=experiment_id,
            timestamp=datetime.now().isoformat(),
            task_id=task_id,
            task_naturalness=task.naturalness.value,
            monitor_id=monitor_id,
            prompt_type=prompt_type,
            run_number=run_number,
            sabotage_inserted=attacker_result.sabotage_inserted,
            attacker_technique=attacker_result.technique_description,
            generated_code=attacker_result.code,
            suspicion_score=monitor_result.score,
            monitor_analysis=monitor_result.analysis,
            flagged=monitor_result.flagged,
            evaded=evaded,
            differential_score=differential_score,
            differential_flagged=differential_flagged,
            monitor_error=monitor_result.error
        )
    
    def run_matrix(
        self,
        tasks: Optional[list[str]] = None,
        monitors: Optional[list[str]] = None,
        prompt_types: Optional[list[str]] = None,
        runs_per_condition: int = 5,
        run_differential: bool = False
    ) -> list[ExperimentResult]:
        """
        Run full experimental matrix.
        
        Args:
            tasks: List of task IDs (default: all tasks)
            monitors: List of monitor IDs (default: all monitors)
            prompt_types: List of prompt types (default: both)
            runs_per_condition: Number of runs per condition
            run_differential: Whether to run differential monitoring
            
        Returns:
            List of all experiment results
        """
        # Defaults
        if tasks is None:
            tasks = [t.task_id for t in get_all_tasks()]
        if monitors is None:
            monitors = ["claude-sonnet", "claude-haiku", "gpt-4o", "gpt-4o-mini"]
        if prompt_types is None:
            prompt_types = ["generic", "specific"]
        
        # Calculate total experiments
        total = len(tasks) * len(monitors) * len(prompt_types) * runs_per_condition
        print(f"\n{'='*60}")
        print(f"SEMANTIC EVASION LAB - Experiment Matrix")
        print(f"{'='*60}")
        print(f"Tasks: {tasks}")
        print(f"Monitors: {monitors}")
        print(f"Prompt types: {prompt_types}")
        print(f"Runs per condition: {runs_per_condition}")
        print(f"Total experiments: {total}")
        print(f"{'='*60}\n")
        
        results = []
        experiment_num = 0
        
        for task_id in tasks:
            task = get_task(task_id)
            print(f"\n[Task: {task_id}] Naturalness: {task.naturalness.name}")
            
            for monitor_id in monitors:
                for prompt_type in prompt_types:
                    for run in range(1, runs_per_condition + 1):
                        experiment_num += 1
                        print(f"\n--- Experiment {experiment_num}/{total} ---")
                        print(f"Config: {task_id} | {monitor_id} | {prompt_type} | run {run}")
                        
                        result = self.run_single(
                            task_id=task_id,
                            monitor_id=monitor_id,
                            prompt_type=prompt_type,
                            run_differential=run_differential,
                            run_number=run
                        )
                        results.append(result)
                        
                        # Save incrementally
                        self._save_result(result)
        
        # Save summary
        self._save_summary(results)
        
        return results
    
    def _save_result(self, result: ExperimentResult):
        """Save a single result to file."""
        filename = f"{result.experiment_id}.json"
        filepath = self.results_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(asdict(result), f, indent=2)
    
    def _save_summary(self, results: list[ExperimentResult]):
        """Save summary statistics."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Calculate summary stats
        total = len(results)
        successful_sabotage = sum(1 for r in results if r.sabotage_inserted)
        evasions = sum(1 for r in results if r.evaded)
        errors = sum(1 for r in results if r.attacker_error or r.monitor_error)
        
        summary = {
            "timestamp": timestamp,
            "total_experiments": total,
            "successful_sabotage_insertions": successful_sabotage,
            "successful_evasions": evasions,
            "evasion_rate": evasions / successful_sabotage if successful_sabotage > 0 else 0,
            "errors": errors,
            "by_task": {},
            "by_monitor": {},
            "by_prompt": {}
        }
        
        # Group by task
        for task_id in set(r.task_id for r in results):
            task_results = [r for r in results if r.task_id == task_id]
            task_sab = sum(1 for r in task_results if r.sabotage_inserted)
            task_eva = sum(1 for r in task_results if r.evaded)
            summary["by_task"][task_id] = {
                "total": len(task_results),
                "sabotage_inserted": task_sab,
                "evasions": task_eva,
                "evasion_rate": task_eva / task_sab if task_sab > 0 else 0
            }
        
        # Group by monitor
        for monitor_id in set(r.monitor_id for r in results):
            mon_results = [r for r in results if r.monitor_id == monitor_id]
            mon_sab = sum(1 for r in mon_results if r.sabotage_inserted)
            mon_eva = sum(1 for r in mon_results if r.evaded)
            summary["by_monitor"][monitor_id] = {
                "total": len(mon_results),
                "sabotage_inserted": mon_sab,
                "evasions": mon_eva,
                "evasion_rate": mon_eva / mon_sab if mon_sab > 0 else 0
            }
        
        # Save summary
        summary_path = self.results_dir / f"summary_{timestamp}.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        print(f"Total experiments: {total}")
        print(f"Sabotage inserted: {successful_sabotage} ({100*successful_sabotage/total:.1f}%)")
        print(f"Successful evasions: {evasions}")
        print(f"Overall evasion rate: {100*summary['evasion_rate']:.1f}%")
        print(f"\nResults saved to: {self.results_dir}")


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Run semantic evasion experiments"
    )
    
    parser.add_argument(
        "--task", "-t",
        type=str,
        help="Single task to run (e.g., 'rounding_skim')"
    )
    
    parser.add_argument(
        "--monitor", "-m",
        type=str,
        default="claude-sonnet",
        help="Monitor to use (claude-sonnet, claude-haiku, gpt-4o, gpt-4o-mini)"
    )
    
    parser.add_argument(
        "--prompt", "-p",
        type=str,
        default="generic",
        choices=["generic", "specific"],
        help="Prompt type"
    )
    
    parser.add_argument(
        "--runs", "-r",
        type=int,
        default=5,
        help="Number of runs per condition"
    )
    
    parser.add_argument(
        "--full-matrix",
        action="store_true",
        help="Run full experimental matrix"
    )
    
    parser.add_argument(
        "--cross-model",
        action="store_true",
        help="Run cross-model comparison (Claude vs GPT-4)"
    )
    
    parser.add_argument(
        "--differential",
        action="store_true",
        help="Include differential monitoring"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="results",
        help="Output directory"
    )
    
    args = parser.parse_args()
    
    runner = ExperimentRunner(results_dir=args.output)
    
    if args.full_matrix:
        # Full matrix: all tasks × all monitors × both prompts
        runner.run_matrix(
            runs_per_condition=args.runs,
            run_differential=args.differential
        )
    
    elif args.cross_model:
        # Cross-model comparison: all tasks × (Claude + GPT-4) × both prompts
        runner.run_matrix(
            monitors=["claude-sonnet", "gpt-4o"],
            runs_per_condition=args.runs,
            run_differential=args.differential
        )
    
    elif args.task:
        # Single task experiment
        for run in range(1, args.runs + 1):
            print(f"\n=== Run {run}/{args.runs} ===")
            result = runner.run_single(
                task_id=args.task,
                monitor_id=args.monitor,
                prompt_type=args.prompt,
                run_differential=args.differential,
                run_number=run
            )
            print(f"Result: {'EVADED' if result.evaded else 'DETECTED'}")
    
    else:
        parser.print_help()
        print("\nExamples:")
        print("  python -m experiments.runner --task rounding_skim --runs 5")
        print("  python -m experiments.runner --cross-model --runs 3")
        print("  python -m experiments.runner --full-matrix --differential")


if __name__ == "__main__":
    main()

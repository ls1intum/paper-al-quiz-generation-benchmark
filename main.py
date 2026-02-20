#!/usr/bin/env python3
"""Main entry point for the quiz benchmark framework."""

import argparse
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

from src.analysis.aggregator import ResultsAggregator
from src.analysis.reporter import ResultsReporter
from src.metrics import GrammaticalCorrectnessMetric
from src.metrics.registry import MetricRegistry
from src.metrics.difficulty import DifficultyMetric
from src.metrics.coverage import CoverageMetric
from src.metrics.clarity import ClarityMetric
from src.runners.benchmark import BenchmarkRunner
from src.utils.config_loader import ConfigLoader
from src.utils.io import IOUtils
from src.utils.logging_utils import setup_logging


def register_metrics() -> None:
    """Register all available metrics."""
    MetricRegistry.register(DifficultyMetric)
    MetricRegistry.register(CoverageMetric)
    MetricRegistry.register(ClarityMetric)
    MetricRegistry.register(GrammaticalCorrectnessMetric)


def main() -> int:
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Quiz Generation Benchmark Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
    Examples:
      # Run benchmark with default config
      python main.py --config config/benchmark_example.yaml

      # Specify custom .env file
      python main.py --config config/benchmark_example.yaml --env .env.custom

      # Skip aggregation
      python main.py --config config/benchmark_example.yaml --no-aggregate
            """,
    )

    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to benchmark configuration YAML file",
    )

    parser.add_argument(
        "--env",
        type=str,
        default=".env",
        help="Path to .env file (default: .env)",
    )

    parser.add_argument(
        "--no-aggregate",
        action="store_true",
        help="Skip result aggregation",
    )

    parser.add_argument(
        "--output-prefix",
        type=str,
        default=None,
        help="Run bundle name override (default: benchmark-name + timestamp + config hash)",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose debug logging in terminal",
    )

    args = parser.parse_args()

    try:
        setup_logging(debug=args.debug)
        logger = logging.getLogger(__name__)

        # Register metrics
        logger.info("Registering metrics...")
        register_metrics()
        logger.debug("Available metrics: %s", MetricRegistry.list_metrics())

        # Load configuration
        logger.info("Loading configuration from %s...", args.config)
        config = ConfigLoader.load_config(args.config, args.env)
        logger.info("Configuration loaded: %s v%s", config.name, config.version)
        logger.info("Runs: %s", config.runs)
        logger.info("Evaluators: %s", list(config.evaluators.keys()))
        logger.info("Metrics: %s", [m.name for m in config.get_enabled_metrics()])

        # Build run bundle directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug_name = re.sub(r"[^a-zA-Z0-9_-]+", "-", config.name.strip().lower()).strip("-")
        slug_name = slug_name or "benchmark"
        run_id = f"{slug_name}-{timestamp}-{ConfigLoader.hash_config(config)[:8]}"
        run_bundle_name = args.output_prefix or run_id

        results_root = Path(config.input_output.results_directory)
        run_dir = results_root / run_bundle_name
        run_dir.mkdir(parents=True, exist_ok=True)

        log_file = run_dir / "run.log"
        setup_logging(debug=args.debug, log_file=log_file)
        logger = logging.getLogger(__name__)

        logger.info("Run bundle: %s", run_dir)
        logger.debug("Log file: %s", log_file)
        logger.debug("Environment file: %s", args.env)

        metadata_file = run_dir / "metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "run_bundle": run_bundle_name,
                    "started_at": datetime.now().isoformat(),
                    "config_name": config.name,
                    "config_version": config.version,
                    "config_hash": ConfigLoader.hash_config(config),
                    "config_path": str(Path(args.config)),
                    "env_file": str(Path(args.env)),
                    "runs": config.runs,
                    "evaluators": list(config.evaluators.keys()),
                    "metrics": [m.name for m in config.get_enabled_metrics()],
                    "debug_mode": args.debug,
                },
                f,
                indent=2,
            )

        # Initialize benchmark runner
        logger.info("Initializing benchmark runner...")
        runner = BenchmarkRunner(config)

        # Run benchmark
        logger.info("Starting benchmark execution...")
        results = runner.run()
        logger.info("Benchmark complete. Generated %s result objects.", len(results))

        # Save individual results
        results_file = run_dir / "results.json"
        logger.info("Saving results to %s...", results_file)
        IOUtils.save_results(results, str(results_file))

        # Aggregate and save if requested
        if not args.no_aggregate:
            logger.info("Aggregating results...")
            aggregated = ResultsAggregator.aggregate(results, config.name)

            aggregated_file = run_dir / "aggregated.json"
            logger.info("Saving aggregated results to %s...", aggregated_file)
            IOUtils.save_aggregated_results(aggregated, str(aggregated_file))

            # Generate standard summary
            summary = ResultsReporter.generate_summary(aggregated)

            # Extract and Append Qualitative Reasoning
            detailed_notes = []
            detailed_notes.append("\n" + "=" * 70)
            detailed_notes.append("DETAILED INSIGHTS (Qualitative Data)")
            detailed_notes.append("=" * 70)

            found_insights = False

            # Helper to safely get attributes whether it's a dict or object
            def safe_get(item, key, default=None):
                if isinstance(item, dict):
                    return item.get(key, default)
                return getattr(item, key, default)

            for result in results:
                quiz_id = safe_get(result, 'quiz_id', 'Unknown Quiz')
                metrics_list = safe_get(result, 'metrics', [])

                for metric in metrics_list:
                    metric_name = safe_get(metric, 'metric_name')
                    raw_response = safe_get(metric, 'raw_response')

                    # Check for Coverage metric specifically
                    if metric_name == 'coverage':
                        try:
                            # Clean the markdown JSON string
                            if isinstance(raw_response, str):
                                clean_json = raw_response.replace("```json", "").replace("```", "").strip()
                                # Parse JSON
                                data = json.loads(clean_json)

                                # Extract fields
                                reasoning = data.get('reasoning')
                                sub_scores = data.get('sub_scores')
                                score = data.get('final_score')

                                if reasoning:
                                    found_insights = True
                                    detailed_notes.append(f"\n[Quiz: {quiz_id}] Coverage Analysis:")
                                    detailed_notes.append("-" * 40)
                                    detailed_notes.append(f"Score: {score}")
                                    detailed_notes.append(f"Reasoning:\n{reasoning}")

                                    if sub_scores:
                                        detailed_notes.append(f"Sub-scores: {sub_scores}")
                                    detailed_notes.append("-" * 40)
                        except Exception:
                            # If parsing fails, skip silently
                            continue

            if found_insights:
                # Append the detailed notes to the main summary string
                summary_str = summary + "\n".join(detailed_notes)
            else:
                summary_str = summary

            # Print the FULL summary (Statistics + Reasoning)
            logger.info("\n%s", summary_str)

            # Save summary to text file
            summary_file = run_dir / "summary.txt"
            with open(summary_file, "w", encoding="utf-8") as f:
                f.write(summary_str)
            logger.info("Summary saved to %s", summary_file)

        logger.info("BENCHMARK COMPLETE")

        return 0

    except KeyboardInterrupt:
        logging.getLogger(__name__).warning("Benchmark interrupted by user.")
        return 130

    except Exception as e:
        logging.getLogger(__name__).exception("Error: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())

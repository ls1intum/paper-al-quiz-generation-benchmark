#!/usr/bin/env python3
"""Main entry point for the quiz benchmark framework."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from src.analysis.aggregator import ResultsAggregator
from src.analysis.reporter import ResultsReporter
from src.metrics.registry import MetricRegistry
from src.metrics.difficulty import DifficultyMetric
from src.metrics.coverage import CoverageMetric
from src.metrics.clarity import ClarityMetric
from src.runners.benchmark import BenchmarkRunner
from src.utils.config_loader import ConfigLoader
from src.utils.io import IOUtils


def register_metrics() -> None:
    """Register all available metrics."""
    MetricRegistry.register(DifficultyMetric)
    MetricRegistry.register(CoverageMetric)
    MetricRegistry.register(ClarityMetric)


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
        help="Prefix for output files (default: timestamp)",
    )

    args = parser.parse_args()

    try:
        # Register metrics
        print("Registering metrics...")
        register_metrics()
        print(f"Available metrics: {MetricRegistry.list_metrics()}")
        print()

        # Load configuration
        print(f"Loading configuration from {args.config}...")
        config = ConfigLoader.load_config(args.config, args.env)
        print(f"Configuration loaded: {config.name} v{config.version}")
        print(f"Runs: {config.runs}")
        print(f"Evaluators: {list(config.evaluators.keys())}")
        print(f"Metrics: {[m.name for m in config.get_enabled_metrics()]}")
        print()

        # Initialize benchmark runner
        print("Initializing benchmark runner...")
        runner = BenchmarkRunner(config)
        print()

        # Run benchmark
        print("Starting benchmark execution...")
        results = runner.run()
        print(f"\nBenchmark complete! Generated {len(results)} results.")
        print()

        # Generate output filename prefix
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_prefix = args.output_prefix or timestamp

        # Save individual results
        results_dir = Path(config.input_output.results_directory)
        results_dir.mkdir(parents=True, exist_ok=True)

        results_file = results_dir / f"results_{output_prefix}.json"
        print(f"Saving results to {results_file}...")
        IOUtils.save_results(results, str(results_file))

        # Aggregate and save if requested
        if not args.no_aggregate:
            print("\nAggregating results...")
            aggregated = ResultsAggregator.aggregate(results, config.name)

            aggregated_file = results_dir / f"aggregated_{output_prefix}.json"
            print(f"Saving aggregated results to {aggregated_file}...")
            IOUtils.save_aggregated_results(aggregated, str(aggregated_file))

            # Generate and display summary
            print("\n" + "=" * 70)
            summary = ResultsReporter.generate_summary(aggregated)
            print(summary)

            # Save summary to text file
            summary_file = results_dir / f"summary_{output_prefix}.txt"
            with open(summary_file, "w") as f:
                f.write(summary)
            print(f"\nSummary saved to {summary_file}")

        print("\n" + "=" * 70)
        print("BENCHMARK COMPLETE")
        print("=" * 70)

        return 0

    except KeyboardInterrupt:
        print("\n\nBenchmark interrupted by user.")
        return 130

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

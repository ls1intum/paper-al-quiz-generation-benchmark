"""Results reporting module."""

from typing import Dict, List

from ..models.result import AggregatedResults, BenchmarkResult


class ResultsReporter:
    """Generates human-readable reports from benchmark results."""

    @staticmethod
    def generate_summary(aggregated: AggregatedResults) -> str:
        """Generate a text summary of aggregated results.

        Args:
            aggregated: Aggregated results

        Returns:
            Formatted summary string
        """
        lines = []
        lines.append("=" * 70)
        lines.append("BENCHMARK RESULTS SUMMARY")
        lines.append("=" * 70)
        lines.append(f"Configuration: {aggregated.benchmark_config_name}")
        lines.append(f"Version: {aggregated.benchmark_version}")
        lines.append(f"Total Runs: {aggregated.total_runs}")
        lines.append(f"Quizzes Evaluated: {len(aggregated.quiz_ids)}")
        lines.append("")

        # Group by metric
        metrics = aggregated.get_all_metrics()

        for metric_name in sorted(metrics):
            lines.append(f"\n{metric_name.upper()}")
            lines.append("-" * 70)

            # Get all evaluators for this metric
            for agg_key, agg in sorted(aggregated.aggregations.items()):
                if agg.metric_name == metric_name:
                    lines.append(f"\n  Evaluator: {agg.evaluator_model}")
                    lines.append(f"    Mean:   {agg.mean:.2f}")
                    lines.append(f"    Median: {agg.median:.2f}")
                    lines.append(f"    Std Dev: {agg.std_dev:.2f}")
                    lines.append(f"    Min:    {agg.min:.2f}")
                    lines.append(f"    Max:    {agg.max:.2f}")
                    lines.append(f"    N:      {agg.num_runs}")

        lines.append("\n" + "=" * 70)

        return "\n".join(lines)

    @staticmethod
    def generate_comparison_report(aggregated: AggregatedResults, metric_name: str) -> str:
        """Generate a comparison report for a specific metric across evaluators.

        Args:
            aggregated: Aggregated results
            metric_name: Metric to compare

        Returns:
            Formatted comparison string
        """
        lines = []
        lines.append("=" * 70)
        lines.append(f"EVALUATOR COMPARISON: {metric_name}")
        lines.append("=" * 70)

        # Collect all aggregations for this metric
        metric_aggs = []
        for agg in aggregated.aggregations.values():
            if agg.metric_name == metric_name:
                metric_aggs.append(agg)

        if not metric_aggs:
            lines.append(f"No results found for metric: {metric_name}")
            return "\n".join(lines)

        # Sort by mean score
        metric_aggs.sort(key=lambda x: x.mean, reverse=True)

        # Table header
        lines.append(
            f"\n{'Evaluator':<30} {'Mean':<8} {'Median':<8} {'Std Dev':<8} {'Min':<8} {'Max':<8}"
        )
        lines.append("-" * 70)

        # Table rows
        for agg in metric_aggs:
            lines.append(
                f"{agg.evaluator_model:<30} "
                f"{agg.mean:>7.2f} "
                f"{agg.median:>7.2f} "
                f"{agg.std_dev:>7.2f} "
                f"{agg.min:>7.2f} "
                f"{agg.max:>7.2f}"
            )

        lines.append("=" * 70)

        return "\n".join(lines)

    @staticmethod
    def generate_quiz_report(results: List[BenchmarkResult], quiz_id: str) -> str:
        """Generate a detailed report for a specific quiz.

        Args:
            results: Benchmark results
            quiz_id: Quiz ID to report on

        Returns:
            Formatted report string
        """
        # Filter results for this quiz
        quiz_results = [r for r in results if r.quiz_id == quiz_id]

        if not quiz_results:
            return f"No results found for quiz: {quiz_id}"

        lines = []
        lines.append("=" * 70)
        lines.append(f"QUIZ REPORT: {quiz_id}")
        lines.append("=" * 70)

        # Get quiz metadata
        first_result = quiz_results[0]
        quiz_title = first_result.metadata.get("quiz_title", "Unknown")
        num_questions = first_result.metadata.get("num_questions", 0)

        lines.append(f"Title: {quiz_title}")
        lines.append(f"Questions: {num_questions}")
        lines.append(f"Runs: {len(quiz_results)}")
        lines.append("")

        # Aggregate metrics
        from collections import defaultdict

        metric_scores: Dict[str, List[float]] = defaultdict(list)

        for result in quiz_results:
            for metric in result.metrics:
                key = f"{metric.metric_name}_{metric.evaluator_model}"
                metric_scores[key].append(metric.score)

        # Display aggregated metrics
        import statistics

        lines.append("METRIC SCORES")
        lines.append("-" * 70)
        for key, scores in sorted(metric_scores.items()):
            mean_score = statistics.mean(scores)
            std_dev = statistics.stdev(scores) if len(scores) > 1 else 0.0
            lines.append(f"{key:<40} {mean_score:>6.2f} ± {std_dev:>5.2f}")

        lines.append("=" * 70)

        return "\n".join(lines)

    @staticmethod
    def export_to_dict(aggregated: AggregatedResults) -> Dict:
        """Export aggregated results to a simple dictionary format.

        Args:
            aggregated: Aggregated results

        Returns:
            Dictionary with results
        """
        export = {
            "benchmark_name": aggregated.benchmark_config_name,
            "version": aggregated.benchmark_version,
            "total_runs": aggregated.total_runs,
            "num_quizzes": len(aggregated.quiz_ids),
            "metrics": {},
        }

        for metric_name in aggregated.get_all_metrics():
            export["metrics"][metric_name] = {}

            for agg in aggregated.aggregations.values():
                if agg.metric_name == metric_name:
                    export["metrics"][metric_name][agg.evaluator_model] = {
                        "mean": round(agg.mean, 2),
                        "median": round(agg.median, 2),
                        "std_dev": round(agg.std_dev, 2),
                        "min": round(agg.min, 2),
                        "max": round(agg.max, 2),
                    }

        return export

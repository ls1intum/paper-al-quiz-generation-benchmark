"""Configuration loading utilities."""

import hashlib
from pathlib import Path
from typing import Any, Dict

import yaml
from dotenv import load_dotenv

from ..models.config import (
    BenchmarkConfig,
    EvaluatorConfig,
    InputOutputConfig,
    MetricConfig,
)


class ConfigLoader:
    """Utilities for loading benchmark configuration."""

    @staticmethod
    def load_env(env_file: str = ".env") -> None:
        """Load environment variables from file.

        Args:
            env_file: Path to .env file
        """
        load_dotenv(env_file)

    @staticmethod
    def load_yaml(config_path: str) -> Dict[str, Any]:
        """Load YAML configuration file.

        Args:
            config_path: Path to YAML config file

        Returns:
            Dictionary with configuration data

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML is invalid
        """
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(path, "r") as f:
            config_dict = yaml.safe_load(f)

        return config_dict

    @staticmethod
    def parse_config(config_dict: Dict[str, Any]) -> BenchmarkConfig:
        """Parse configuration dictionary into BenchmarkConfig object.

        Args:
            config_dict: Dictionary from YAML file

        Returns:
            BenchmarkConfig object

        Raises:
            ValueError: If configuration is invalid
        """
        # Parse benchmark section
        benchmark_section = config_dict.get("benchmark", {})
        name = benchmark_section.get("name")
        version = benchmark_section.get("version")
        runs = benchmark_section.get("runs", 1)

        if not name or not version:
            raise ValueError("Benchmark name and version are required")

        # Parse evaluators
        evaluators_dict = config_dict.get("evaluators", {})
        evaluators = {}
        for eval_name, eval_config in evaluators_dict.items():
            evaluators[eval_name] = EvaluatorConfig(
                name=eval_name,
                provider=eval_config.get("provider"),
                model=eval_config.get("model"),
                temperature=eval_config.get("temperature", 0.0),
                max_tokens=eval_config.get("max_tokens", 500),
                additional_params={
                    k: v
                    for k, v in eval_config.items()
                    if k not in ["provider", "model", "temperature", "max_tokens"]
                },
            )

        # Parse metrics
        metrics_list = config_dict.get("metrics", [])
        metrics = []
        for metric_config in metrics_list:
            metrics.append(
                MetricConfig(
                    name=metric_config.get("name"),
                    version=metric_config.get("version", "1.0"),
                    evaluators=metric_config.get("evaluators", []),
                    parameters=metric_config.get("parameters", {}),
                    enabled=metric_config.get("enabled", True),
                )
            )

        # Parse input/output
        io_section = config_dict.get("inputs", {})
        outputs_section = config_dict.get("outputs", {})
        input_output = InputOutputConfig(
            quiz_directory=io_section.get("quiz_directory", "data/quizzes"),
            source_directory=io_section.get("source_directory", "data/inputs"),
            results_directory=outputs_section.get("results_directory", "data/results"),
        )

        # Create config object
        config = BenchmarkConfig(
            name=name,
            version=version,
            runs=runs,
            evaluators=evaluators,
            metrics=metrics,
            input_output=input_output,
            metadata=benchmark_section.get("metadata", {}),
        )

        # Validate
        config.validate()

        return config

    @staticmethod
    def load_config(config_path: str, env_file: str = ".env") -> BenchmarkConfig:
        """Load complete benchmark configuration.

        Args:
            config_path: Path to YAML config file
            env_file: Path to .env file

        Returns:
            BenchmarkConfig object
        """
        # Load environment variables
        ConfigLoader.load_env(env_file)

        # Load and parse YAML
        config_dict = ConfigLoader.load_yaml(config_path)
        config = ConfigLoader.parse_config(config_dict)

        return config

    @staticmethod
    def hash_config(config: BenchmarkConfig) -> str:
        """Generate a hash of the configuration for reproducibility tracking.

        Args:
            config: Benchmark configuration

        Returns:
            SHA256 hash of the configuration
        """
        # Create a deterministic string representation
        config_str = (
            f"{config.name}|{config.version}|{config.runs}|"
            f"{sorted(config.evaluators.keys())}|"
            f"{[(m.name, m.version, tuple(m.evaluators)) for m in config.metrics]}"
        )

        return hashlib.sha256(config_str.encode()).hexdigest()[:16]

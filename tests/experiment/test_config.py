"""
Tests for experiment configuration management.

Covers config save/load cycle, error handling, and ID generation.
"""

import json
import pytest
import tempfile
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from agent_trade.experiment.config import (
    create_experiment_config,
    save_config,
    load_config,
    list_experiments,
    generate_experiment_id,
    get_experiment_dir,
)
from agent_trade.experiment.models import ExperimentConfig


class TestCreateExperimentConfig:
    """Tests for create_experiment_config function."""

    def test_create_with_defaults(self):
        """Test creating config with default values."""
        config = create_experiment_config(
            experiment_id="test_001",
            name="Test Experiment",
        )

        assert config.experiment_id == "test_001"
        assert config.name == "Test Experiment"
        assert config.num_agents == 10
        assert config.starting_capital == Decimal("1000.00")
        assert config.short_term_tax_rate == Decimal("0.35")
        assert config.long_term_tax_rate == Decimal("0.15")
        assert config.long_term_holding_days == 365
        assert config.status == "active"

    def test_create_with_custom_values(self):
        """Test creating config with custom values."""
        config = create_experiment_config(
            experiment_id="test_002",
            name="Custom Experiment",
            num_agents=5,
            starting_capital=Decimal("2000.00"),
            short_term_tax_rate=Decimal("0.40"),
            long_term_tax_rate=Decimal("0.20"),
        )

        assert config.num_agents == 5
        assert config.starting_capital == Decimal("2000.00")
        assert config.short_term_tax_rate == Decimal("0.40")
        assert config.long_term_tax_rate == Decimal("0.20")


class TestSaveAndLoadConfig:
    """Tests for config persistence."""

    def test_save_and_load_cycle(self, tmp_path, monkeypatch):
        """Test saving and loading config."""
        # Use temp directory for test
        monkeypatch.setattr("agent_trade.experiment.config.Path.home", lambda: tmp_path)

        config = create_experiment_config(
            experiment_id="test_save_load",
            name="Save Load Test",
        )

        # Save
        save_config(config)

        # Verify file exists
        config_path = tmp_path / ".agent-trade" / "experiments" / "test_save_load" / "config.json"
        assert config_path.exists()

        # Load
        loaded_config = load_config("test_save_load")

        assert loaded_config is not None
        assert loaded_config.experiment_id == config.experiment_id
        assert loaded_config.name == config.name
        assert loaded_config.num_agents == config.num_agents
        assert loaded_config.starting_capital == config.starting_capital

    def test_load_nonexistent_config(self, tmp_path, monkeypatch):
        """Test loading config that doesn't exist."""
        monkeypatch.setattr("agent_trade.experiment.config.Path.home", lambda: tmp_path)

        result = load_config("nonexistent")
        assert result is None

    def test_load_malformed_json(self, tmp_path, monkeypatch):
        """Test loading config with malformed JSON."""
        monkeypatch.setattr("agent_trade.experiment.config.Path.home", lambda: tmp_path)

        # Create directory and malformed JSON file
        config_dir = tmp_path / ".agent-trade" / "experiments" / "malformed"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "config.json"
        config_path.write_text("{invalid json}")

        with pytest.raises(json.JSONDecodeError):
            load_config("malformed")

    def test_load_invalid_schema(self, tmp_path, monkeypatch):
        """Test loading config with invalid schema."""
        from pydantic import ValidationError

        monkeypatch.setattr("agent_trade.experiment.config.Path.home", lambda: tmp_path)

        # Create directory and invalid config
        config_dir = tmp_path / ".agent-trade" / "experiments" / "invalid_schema"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "config.json"
        config_path.write_text(json.dumps({"invalid_field": "value"}))

        with pytest.raises(ValidationError):
            load_config("invalid_schema")

    def test_save_creates_directories(self, tmp_path, monkeypatch):
        """Test that save_config creates necessary directories."""
        monkeypatch.setattr("agent_trade.experiment.config.Path.home", lambda: tmp_path)

        config = create_experiment_config(
            experiment_id="test_mkdir",
            name="Test",
        )

        # Ensure directory doesn't exist
        config_dir = tmp_path / ".agent-trade" / "experiments" / "test_mkdir"
        assert not config_dir.exists()

        # Save should create it
        save_config(config)

        assert config_dir.exists()
        assert (config_dir / "config.json").exists()


class TestListExperiments:
    """Tests for list_experiments function."""

    def test_list_empty(self, tmp_path, monkeypatch):
        """Test listing with no experiments."""
        monkeypatch.setattr("agent_trade.experiment.config.Path.home", lambda: tmp_path)

        experiments = list_experiments()
        assert experiments == []

    def test_list_multiple_experiments(self, tmp_path, monkeypatch):
        """Test listing multiple experiments."""
        monkeypatch.setattr("agent_trade.experiment.config.Path.home", lambda: tmp_path)

        # Create multiple configs
        configs = [
            create_experiment_config("exp_001", "Experiment 1"),
            create_experiment_config("exp_002", "Experiment 2"),
            create_experiment_config("exp_003", "Experiment 3"),
        ]

        for config in configs:
            save_config(config)

        experiments = list_experiments()

        assert len(experiments) == 3
        assert ("exp_001", "Experiment 1") in experiments
        assert ("exp_002", "Experiment 2") in experiments
        assert ("exp_003", "Experiment 3") in experiments

    def test_list_skips_malformed_configs(self, tmp_path, monkeypatch):
        """Test that list_experiments skips malformed configs."""
        monkeypatch.setattr("agent_trade.experiment.config.Path.home", lambda: tmp_path)

        # Create valid config
        config = create_experiment_config("exp_valid", "Valid")
        save_config(config)

        # Create malformed config
        malformed_dir = tmp_path / ".agent-trade" / "experiments" / "exp_malformed"
        malformed_dir.mkdir(parents=True)
        (malformed_dir / "config.json").write_text("{invalid json}")

        # Should skip malformed and return only valid
        experiments = list_experiments()
        assert len(experiments) == 1
        assert ("exp_valid", "Valid") in experiments

    def test_list_skips_inaccessible_configs(self, tmp_path, monkeypatch):
        """Test that list_experiments skips configs with read errors."""
        monkeypatch.setattr("agent_trade.experiment.config.Path.home", lambda: tmp_path)

        # Create valid config
        config = create_experiment_config("exp_valid", "Valid")
        save_config(config)

        # Create directory without config file
        no_config_dir = tmp_path / ".agent-trade" / "experiments" / "exp_no_config"
        no_config_dir.mkdir(parents=True)

        # Should only return the valid one
        experiments = list_experiments()
        assert len(experiments) == 1
        assert ("exp_valid", "Valid") in experiments

    def test_list_uses_directory_name_as_id(self, tmp_path, monkeypatch):
        """Test that list_experiments uses directory name as canonical ID."""
        monkeypatch.setattr("agent_trade.experiment.config.Path.home", lambda: tmp_path)

        # Create config with mismatched experiment_id in JSON
        config_dir = tmp_path / ".agent-trade" / "experiments" / "dir_name"
        config_dir.mkdir(parents=True)
        config_data = {
            "experiment_id": "wrong_id_in_json",
            "name": "Test",
            "num_agents": 10,
            "starting_capital": "1000.00",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "active",
        }
        (config_dir / "config.json").write_text(json.dumps(config_data))

        experiments = list_experiments()

        # Should use directory name, not JSON field
        assert len(experiments) == 1
        assert experiments[0][0] == "dir_name"


class TestGenerateExperimentId:
    """Tests for generate_experiment_id function."""

    def test_generate_id_format(self, tmp_path, monkeypatch):
        """Test that generated ID follows exp_YYYYMMDD_NNN format."""
        monkeypatch.setattr("agent_trade.experiment.config.Path.home", lambda: tmp_path)

        exp_id = generate_experiment_id()

        assert exp_id.startswith("exp_")
        parts = exp_id.split("_")
        assert len(parts) == 3
        assert len(parts[1]) == 8  # YYYYMMDD
        assert len(parts[2]) == 3  # NNN
        assert parts[2].isdigit()

    def test_generate_increments_counter(self, tmp_path, monkeypatch):
        """Test that counter increments for existing IDs."""
        monkeypatch.setattr("agent_trade.experiment.config.Path.home", lambda: tmp_path)

        # Create first experiment
        exp_id_1 = generate_experiment_id()
        exp_dir_1 = tmp_path / ".agent-trade" / "experiments" / exp_id_1
        exp_dir_1.mkdir(parents=True)

        # Generate second ID - should increment
        exp_id_2 = generate_experiment_id()

        # Extract counters
        counter_1 = int(exp_id_1.split("_")[2])
        counter_2 = int(exp_id_2.split("_")[2])

        assert counter_2 == counter_1 + 1

    def test_generate_overflow_raises_error(self, tmp_path, monkeypatch):
        """Test that counter overflow raises RuntimeError."""
        monkeypatch.setattr("agent_trade.experiment.config.Path.home", lambda: tmp_path)

        # Create 1000 experiment directories (000-999)
        base_dir = tmp_path / ".agent-trade" / "experiments"
        base_dir.mkdir(parents=True)

        # Mock the date to ensure consistent exp_YYYYMMDD prefix
        fixed_date = "20260215"
        with patch("agent_trade.experiment.config.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = fixed_date

            # Create directories for all counters 001-999
            for i in range(1, 1000):
                exp_dir = base_dir / f"exp_{fixed_date}_{i:03d}"
                exp_dir.mkdir()

            # Trying to generate one more should raise RuntimeError
            with pytest.raises(RuntimeError, match="Experiment ID overflow"):
                generate_experiment_id()

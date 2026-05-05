from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import numpy as np

from scripts.run_experiment import _run_or_resume_model
from src.config import ExperimentConfig, ModelConfig, load_model_configs
from src.explain import _positive_class_shap_values
from src.pipeline import run_model_on_dataset
from src.providers import (
    LLMClient,
    LLMProviderError,
    LLMRequestFailed,
    _documented_min_request_interval_seconds,
    _parse_duration_header,
    _parse_retry_after_from_body,
)


def experiment_config() -> ExperimentConfig:
    return ExperimentConfig(
        name="test",
        seed=42,
        sample_size=3,
        target_safe=2,
        target_phishing=1,
        input_dataset=Path("unused.csv"),
        sample_dataset=Path("unused_sample.csv"),
        max_email_chars=6000,
        retry_attempts=2,
        retry_sleep_seconds=0,
        request_timeout_seconds=5,
        backoff_base_seconds=0,
        backoff_max_seconds=0,
        groq_rate_limit_safety_factor=1.0,
        groq_min_remaining_tokens=0,
        sleep_between_requests_seconds=0,
    )


def sample_dataset() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"sample_id": "email_001", "email_text": "hello", "true_label": "safe"},
            {"sample_id": "email_002", "email_text": "urgent verify password", "true_label": "phishing"},
            {"sample_id": "email_003", "email_text": "meeting notes", "true_label": "safe"},
        ]
    )


class RetryTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["GROQ_API_KEY"] = "test-key"
        os.environ.pop("LLM_MAX_ATTEMPTS", None)
        self.model = ModelConfig(
            name="groq-test",
            provider="groq",
            enabled=True,
            model_id="test-model",
            temperature=0.0,
            max_tokens=100,
        )

    def test_retry_succeeds_after_transient_failures(self) -> None:
        calls = []

        def fake_chat_completion(**kwargs):
            calls.append(kwargs)
            if len(calls) < 3:
                raise LLMProviderError("rate limited", error_type="rate_limit", retriable=True, status_code=429)
            return (
                '{"classification":"safe","probability":0.1,"red_flags":{},"scores":{},"explanation":"ok"}',
                200,
                "req-1",
                {},
            )

        with patch("src.providers._chat_completion", side_effect=fake_chat_completion):
            client = LLMClient(
                self.model,
                retry_attempts=3,
                retry_sleep_seconds=0,
                backoff_base_seconds=0,
                backoff_max_seconds=0,
            )
            result = client.analyze_with_metadata("email", sample_id="email_001", correlation_id="corr-1")

        self.assertEqual(result.attempts, 3)
        self.assertEqual(len(calls), 3)
        self.assertEqual(result.status_code, 200)

    def test_retry_exhaustion_marks_failure(self) -> None:
        def fake_chat_completion(**kwargs):
            raise LLMProviderError("server error", error_type="server_error", retriable=True, status_code=503)

        with patch("src.providers._chat_completion", side_effect=fake_chat_completion):
            client = LLMClient(
                self.model,
                retry_attempts=2,
                retry_sleep_seconds=0,
                backoff_base_seconds=0,
                backoff_max_seconds=0,
            )
            with self.assertRaises(LLMRequestFailed) as ctx:
                client.analyze_with_metadata("email", sample_id="email_001", correlation_id="corr-1")

        self.assertEqual(ctx.exception.attempts, 2)
        self.assertEqual(ctx.exception.error_type, "server_error")

    def test_non_retriable_error_does_not_retry(self) -> None:
        calls = []

        def fake_chat_completion(**kwargs):
            calls.append(kwargs)
            raise LLMProviderError("bad payload", error_type="validation", retriable=False, status_code=400)

        with patch("src.providers._chat_completion", side_effect=fake_chat_completion):
            client = LLMClient(
                self.model,
                retry_attempts=3,
                retry_sleep_seconds=0,
                backoff_base_seconds=0,
                backoff_max_seconds=0,
            )
            with self.assertRaises(LLMRequestFailed) as ctx:
                client.analyze_with_metadata("email", sample_id="email_001", correlation_id="corr-1")

        self.assertEqual(len(calls), 1)
        self.assertEqual(ctx.exception.error_type, "validation")

    def test_json_mode_validation_falls_back_without_response_format(self) -> None:
        calls = []

        def fake_chat_completion(**kwargs):
            calls.append(kwargs)
            if kwargs["json_mode"]:
                raise LLMProviderError(
                    "json_validate_failed",
                    error_type="json_mode_validation",
                    retriable=False,
                    status_code=400,
                )
            return (
                '{"classification":"safe","probability":0.1,"red_flags":{},"scores":{},"explanation":"ok"}',
                200,
                "req-1",
                {},
            )

        with patch("src.providers._chat_completion", side_effect=fake_chat_completion):
            client = LLMClient(
                self.model,
                retry_attempts=2,
                retry_sleep_seconds=0,
                backoff_base_seconds=0,
                backoff_max_seconds=0,
            )
            result = client.analyze_with_metadata("email", sample_id="email_001", correlation_id="corr-1")

        self.assertEqual([call["json_mode"] for call in calls], [True, False])
        self.assertEqual(result.attempts, 2)
        self.assertTrue(result.json_mode_fallback_used)


class BatchCoverageTests(unittest.TestCase):
    def test_mock_batch_has_success_status_for_every_email(self) -> None:
        model = ModelConfig("mock", "mock", True, "heuristic-mock", 0.0, 100)
        with tempfile.TemporaryDirectory() as tmp:
            results = run_model_on_dataset(sample_dataset(), model, experiment_config(), Path(tmp), limit=None)
            summary = Path(tmp) / "batch_summary_mock.json"

        self.assertEqual(len(results), 3)
        self.assertTrue((results["status"] == "success").all())
        self.assertTrue(summary.name.endswith(".json"))

    def test_failed_api_batch_still_accounts_for_all_emails(self) -> None:
        os.environ["GROQ_API_KEY"] = "test-key"
        model = ModelConfig("groq-test", "groq", True, "test-model", 0.0, 100)

        def fake_chat_completion(**kwargs):
            raise LLMProviderError("bad payload", error_type="validation", retriable=False, status_code=400)

        with patch("src.providers._chat_completion", side_effect=fake_chat_completion):
            with tempfile.TemporaryDirectory() as tmp:
                results = run_model_on_dataset(sample_dataset(), model, experiment_config(), Path(tmp), limit=None)

        self.assertEqual(len(results), 3)
        self.assertTrue((results["status"] == "failed").all())
        self.assertEqual(int((results["error_type"] == "validation").sum()), 3)

    def test_resume_processes_only_pending_rows(self) -> None:
        model = ModelConfig("groq-test", "groq", True, "test-model", 0.0, 100)
        existing_success = pd.DataFrame(
            [
                {
                    "sample_id": "email_001",
                    "model": "groq-test",
                    "status": "success",
                    "true_label": "safe",
                }
            ]
        )
        new_results = pd.DataFrame(
            [
                {"sample_id": "email_002", "model": "groq-test", "status": "success", "true_label": "phishing"},
                {"sample_id": "email_003", "model": "groq-test", "status": "failed", "true_label": "safe"},
            ]
        )

        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            existing_success.to_csv(run_dir / "results_groq-test.csv", index=False)
            with patch("scripts.run_experiment.run_model_on_dataset", return_value=new_results) as mocked_run:
                combined = _run_or_resume_model(
                    target_dataset=sample_dataset(),
                    model=model,
                    experiment=experiment_config(),
                    run_dir=run_dir,
                    resume=True,
                )

        pending_ids = set(mocked_run.call_args.args[0]["sample_id"])
        self.assertEqual(pending_ids, {"email_002", "email_003"})
        self.assertEqual(len(combined), 3)


class ModelConfigTests(unittest.TestCase):
    def test_required_groq_models_are_configured(self) -> None:
        configs = {model.model_id: model for model in load_model_configs(only_enabled=False)}
        for model_id in [
            "openai/gpt-oss-120b",
            "llama-3.3-70b-versatile",
            "groq/compound",
            "qwen/qwen3-32b",
        ]:
            self.assertIn(model_id, configs)
            self.assertEqual(configs[model_id].provider, "groq")


class GroqRateLimitConfigTests(unittest.TestCase):
    def test_duration_header_parser_matches_groq_examples(self) -> None:
        self.assertAlmostEqual(_parse_duration_header("2m59.56s"), 179.56)
        self.assertAlmostEqual(_parse_duration_header("7.66s"), 7.66)

    def test_documented_model_interval_uses_rpm_and_tpm(self) -> None:
        qwen_wait = _documented_min_request_interval_seconds(
            model_id="qwen/qwen3-32b",
            estimated_tokens=1200,
            safety_factor=1.0,
        )
        llama_wait = _documented_min_request_interval_seconds(
            model_id="llama-3.3-70b-versatile",
            estimated_tokens=1200,
            safety_factor=1.0,
        )
        self.assertGreaterEqual(qwen_wait, 12.0)
        self.assertGreaterEqual(llama_wait, 6.0)

    def test_compound_interval_has_internal_model_safety_floor(self) -> None:
        compound_wait = _documented_min_request_interval_seconds(
            model_id="groq/compound",
            estimated_tokens=1200,
            safety_factor=1.0,
        )
        self.assertGreaterEqual(compound_wait, 12.0)

    def test_retry_after_parser_reads_groq_body_message(self) -> None:
        body = "Please try again in 705ms. Need more tokens?"
        self.assertAlmostEqual(_parse_retry_after_from_body(body), 0.705)


class ShapFormatTests(unittest.TestCase):
    def test_positive_class_shap_values_accepts_new_3d_format(self) -> None:
        values = np.zeros((5, 20, 2))
        values[:, :, 1] = 3
        selected = _positive_class_shap_values(values, n_features=20)

        self.assertEqual(selected.shape, (5, 20))
        self.assertTrue((selected == 3).all())

    def test_positive_class_shap_values_accepts_legacy_list_format(self) -> None:
        values = [np.zeros((5, 20)), np.ones((5, 20))]
        selected = _positive_class_shap_values(values, n_features=20)

        self.assertEqual(selected.shape, (5, 20))
        self.assertTrue((selected == 1).all())


if __name__ == "__main__":
    unittest.main()

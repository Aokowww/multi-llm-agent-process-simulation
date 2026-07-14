#!/usr/bin/env python3
"""OpenAI-compatible client for independent resource-agent bids."""

from __future__ import annotations

import json
import os
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path

import certifi


class DeterministicBidClient:
    """Schema-compatible mock used to validate the multi-agent pipeline."""

    model = "deterministic-profile-bidder"

    def __init__(self):
        self.calls = 0
        self.successful_calls = 0

    def bid(self, context: dict) -> dict:
        self.calls += 1
        self.successful_calls += 1
        profile = context["agent_profile"]
        prior = float(profile["activity_prior"])
        workload = int(profile["assignment_count"])
        score = max(0.0, min(1.0, 0.65 * prior + 0.35 / (1 + workload)))
        return {
            "accept": True,
            "suitability": round(score, 6),
            "expected_delay_minutes": 0.0,
            "reason": "The task is feasible and the score combines local experience and workload.",
        }

    def summary(self) -> dict:
        return {
            "bid_model": self.model,
            "bid_calls": self.calls,
            "bid_successful_calls": self.successful_calls,
            "bid_invalid_outputs": 0,
            "bid_cache_hits": 0,
            "bid_prompt_tokens": 0,
            "bid_completion_tokens": 0,
            "bid_total_tokens": 0,
            "bid_total_latency_seconds": 0.0,
        }


class OpenAICompatibleBidClient:
    """Issue one isolated LLM call per shortlisted ResourceAgent."""

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str,
        timeout: float = 30.0,
        min_interval: float = 0.0,
        seed: int | None = None,
        cache_path: Path | None = None,
    ):
        self.model = model
        self.api_key = api_key
        normalized = base_url.rstrip("/")
        self.url = normalized if normalized.endswith("/chat/completions") else f"{normalized}/chat/completions"
        self.timeout = timeout
        self.min_interval = max(0.0, min_interval)
        self.seed = seed
        self.cache_path = cache_path
        self.prompt_version = "resource-agent-bid-v1"
        self.cached_records = []
        if cache_path and cache_path.exists():
            with cache_path.open(encoding="utf-8") as file:
                self.cached_records = [json.loads(line) for line in file if line.strip()]
        self.calls = 0
        self.cache_hits = 0
        self.api_attempts = 0
        self.successful_calls = 0
        self.invalid_outputs = 0
        self.rate_limit_retries = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0
        self.total_latency_seconds = 0.0
        self.diagnostics: list[dict] = []
        self._last_request_at = 0.0

    @staticmethod
    def _validate(parsed: dict) -> dict:
        if not isinstance(parsed.get("accept"), bool):
            raise ValueError("accept must be a JSON boolean")
        suitability = float(parsed.get("suitability"))
        delay = float(parsed.get("expected_delay_minutes"))
        reason = str(parsed.get("reason", "")).strip()
        if not 0.0 <= suitability <= 1.0:
            raise ValueError("suitability must be between 0 and 1")
        if delay < 0:
            raise ValueError("expected_delay_minutes must be non-negative")
        if not reason:
            raise ValueError("reason must be non-empty")
        return {
            "accept": parsed["accept"],
            "suitability": suitability,
            "expected_delay_minutes": delay,
            "reason": reason,
        }

    def bid(self, context: dict) -> dict:
        self.calls += 1
        if self.calls <= len(self.cached_records):
            record = self.cached_records[self.calls - 1]
            if record.get("model") != self.model or record.get("prompt_version") != self.prompt_version:
                raise RuntimeError(f"Bid cache configuration mismatch at call {self.calls}")
            if record.get("context") != context:
                raise RuntimeError(f"Bid cache context mismatch at call {self.calls}")
            self.cache_hits += 1
            diagnostic = dict(record["diagnostic"])
            diagnostic["cache_hit"] = 1
            self.diagnostics.append(diagnostic)
            self.successful_calls += 1
            self.prompt_tokens += int(diagnostic.get("prompt_tokens", 0))
            self.completion_tokens += int(diagnostic.get("completion_tokens", 0))
            self.total_tokens += int(diagnostic.get("total_tokens", 0))
            self.total_latency_seconds += float(diagnostic.get("latency_seconds", 0.0))
            return dict(record["bid"])

        payload = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 160,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are one business-process resource agent. Evaluate only your own "
                        "profile and local state. Return JSON only with accept (boolean), "
                        "suitability (0 to 1), expected_delay_minutes (non-negative number), "
                        "and reason (one short sentence). Do not compare yourself with agents "
                        "not shown and do not invent capabilities."
                    ),
                },
                {"role": "user", "content": json.dumps(context, sort_keys=True)},
            ],
        }
        if self.seed is not None:
            payload["seed"] = self.seed
        wait = self.min_interval - (time.monotonic() - self._last_request_at)
        if wait > 0:
            time.sleep(wait)
        request = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "multi-llm-agent-process-simulation/1.0",
            },
            method="POST",
        )
        started = time.monotonic()
        diagnostic = {
            "call": self.calls,
            "cache_hit": 0,
            "resource": context["agent_profile"]["resource"],
            "activity": context["task"]["activity"],
            "status": "error",
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "latency_seconds": 0.0,
            "error_type": "",
            "error_message": "",
        }
        bid = None
        try:
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            for attempt in range(1, 4):
                self.api_attempts += 1
                try:
                    with urllib.request.urlopen(request, timeout=self.timeout, context=ssl_context) as response:
                        data = json.loads(response.read().decode("utf-8"))
                    break
                except urllib.error.HTTPError as exc:
                    if exc.code != 429 or attempt == 3:
                        raise
                    self.rate_limit_retries += 1
                    retry_after = float(exc.headers.get("retry-after", 0) or 0)
                    time.sleep(max(self.min_interval, retry_after + 0.25))
            parsed = json.loads(data["choices"][0]["message"]["content"])
            try:
                bid = self._validate(parsed)
            except (TypeError, ValueError, KeyError):
                self.invalid_outputs += 1
                raise
            usage = data.get("usage", {})
            prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
            completion_tokens = int(usage.get("completion_tokens", 0) or 0)
            total_tokens = int(usage.get("total_tokens", prompt_tokens + completion_tokens) or 0)
            self.prompt_tokens += prompt_tokens
            self.completion_tokens += completion_tokens
            self.total_tokens += total_tokens
            self.successful_calls += 1
            diagnostic.update(
                {
                    "status": "success",
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                }
            )
            return bid
        except Exception as exc:
            diagnostic["error_type"] = type(exc).__name__
            diagnostic["error_message"] = str(exc)[:1000]
            raise
        finally:
            self._last_request_at = time.monotonic()
            latency = time.monotonic() - started
            diagnostic["latency_seconds"] = round(latency, 6)
            self.total_latency_seconds += latency
            self.diagnostics.append(diagnostic)
            if bid is not None and self.cache_path is not None:
                record = {
                    "model": self.model,
                    "prompt_version": self.prompt_version,
                    "context": context,
                    "bid": bid,
                    "diagnostic": diagnostic,
                }
                self.cache_path.parent.mkdir(parents=True, exist_ok=True)
                with self.cache_path.open("a", encoding="utf-8") as file:
                    file.write(json.dumps(record, sort_keys=True) + "\n")
                    file.flush()
                    os.fsync(file.fileno())
                self.cached_records.append(record)

    def summary(self) -> dict:
        return {
            "bid_model": self.model,
            "bid_prompt_version": self.prompt_version,
            "bid_calls": self.calls,
            "bid_cache_hits": self.cache_hits,
            "bid_api_attempts": self.api_attempts,
            "bid_successful_calls": self.successful_calls,
            "bid_invalid_outputs": self.invalid_outputs,
            "bid_rate_limit_retries": self.rate_limit_retries,
            "bid_prompt_tokens": self.prompt_tokens,
            "bid_completion_tokens": self.completion_tokens,
            "bid_total_tokens": self.total_tokens,
            "bid_total_latency_seconds": self.total_latency_seconds,
        }

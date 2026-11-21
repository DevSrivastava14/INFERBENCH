"""Latency for one stored row, and aggregates for one stored run.

TTFT, decode duration, and TPOT read one row. Average, median, P50, P95,
P99, and error rate read the measured rows of one run. Generation throughput
and request throughput read that same run.

This package does not call Ollama.
"""

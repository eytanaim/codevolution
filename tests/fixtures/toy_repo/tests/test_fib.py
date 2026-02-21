"""Tests for fibonacci implementation."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fib import fibonacci


def test_base_cases():
    assert fibonacci(0) == 0
    assert fibonacci(1) == 1


def test_small_values():
    assert fibonacci(2) == 1
    assert fibonacci(3) == 2
    assert fibonacci(4) == 3
    assert fibonacci(5) == 5
    assert fibonacci(10) == 55


def test_medium_values():
    assert fibonacci(15) == 610
    assert fibonacci(20) == 6765


def test_negative_raises():
    try:
        fibonacci(-1)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass

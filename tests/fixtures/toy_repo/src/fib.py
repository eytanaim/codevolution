"""Naive fibonacci implementation - intentionally slow for optimization."""


def fibonacci(n: int) -> int:
    """Compute the nth fibonacci number. Naive recursive - O(2^n)."""
    if n < 0:
        raise ValueError("n must be non-negative")
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

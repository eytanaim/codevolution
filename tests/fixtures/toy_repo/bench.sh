#!/bin/bash
# Benchmark: compute fibonacci(25) repeatedly and report requests per second
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

python3 -c "
import time
import sys
sys.path.insert(0, '${SCRIPT_DIR}/src')
from fib import fibonacci

n = 25
iterations = 5
start = time.perf_counter()
for _ in range(iterations):
    fibonacci(n)
elapsed = time.perf_counter() - start
rps = iterations / elapsed
print(f'METRIC:fib_rps={rps:.4f}')
print(f'METRIC:fib_elapsed={elapsed:.4f}')
"

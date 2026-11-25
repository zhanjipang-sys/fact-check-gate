#!/bin/sh
# 自测：PASS 例应退出 0，虚构 IPO 例应退出 1。真实输出见 ../SELFTEST.md
cd "$(dirname "$0")/.." || exit 2
python3 scripts/gate_check.py examples/pass-example; echo "pass-example exit=$?"
python3 scripts/gate_check.py examples/fail-example-ipo; echo "fail-example-ipo exit=$?"

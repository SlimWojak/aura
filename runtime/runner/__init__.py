"""Human-triggered paper runner entrypoints."""

from runtime.runner.hard_flatten import HardKillResult, run_hard_kill
from runtime.runner.supervised_paper import SupervisedOrderResult, run_supervised_order

__all__ = ["HardKillResult", "SupervisedOrderResult", "run_hard_kill", "run_supervised_order"]

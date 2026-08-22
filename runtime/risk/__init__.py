"""Paper-only risk admission API."""

from runtime.risk.admission import AdmissionResult, admit
from runtime.risk.policy import DEFAULT_POLICY, POLICY_VERSION, RiskPolicy, load_policy

__all__ = [
    "AdmissionResult",
    "DEFAULT_POLICY",
    "POLICY_VERSION",
    "RiskPolicy",
    "admit",
    "load_policy",
]


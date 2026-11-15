from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
import re
from typing import Any


class PaymentStatus(str, Enum):
    SETTLED = "settled"
    DECLINED = "declined"
    DISPUTED = "disputed"


@dataclass
class PaymentEvent:
    event_id: str
    account_ref: str
    amount: Decimal
    currency: str
    status: PaymentStatus

    def __post_init__(self) -> None:
        self.amount = Decimal(self.amount)
        self.status = PaymentStatus(self.status)
        if not self.event_id:
            raise ValueError("event_id must not be empty")
        if not self.account_ref:
            raise ValueError("account_ref must not be empty")
        if self.amount <= 0:
            raise ValueError("amount must be greater than zero")
        if re.fullmatch(r"[A-Z]{3}", self.currency) is None:
            raise ValueError("currency must be a three-letter uppercase code")


@dataclass
class ReviewRequest:
    question: str
    payment: PaymentEvent

    def __post_init__(self) -> None:
        if not 3 <= len(self.question) <= 500:
            raise ValueError("question must contain between 3 and 500 characters")


class Action(str, Enum):
    ALLOW = "allow"
    REVIEW = "review"


@dataclass
class AuditNotification:
    event_id: str
    action: Action
    reason: str
    evidence: list[str]


def decide_action(payment: PaymentEvent) -> tuple[Action, str]:
    if payment.status is PaymentStatus.DISPUTED:
        return Action.REVIEW, "Disputed payments require analyst review"
    if payment.amount >= Decimal("10000"):
        return Action.REVIEW, "Payment meets the high-value review threshold"
    return Action.ALLOW, "Payment is below the review threshold and is not disputed"


def review_payment(request: ReviewRequest, backend: Any) -> AuditNotification:
    search_text = f"{request.question} payment status {request.payment.status.value} {request.payment.currency}"
    embedding = backend.embed(search_text)
    matches = backend.query("payment-operations", embedding, top_k=5)
    candidates = [
        str(item["metadata"]["text"])
        for item in matches.get("matches", [])
        if isinstance(item.get("metadata"), dict) and "text" in item["metadata"]
    ]
    ranked = backend.rerank(request.question, candidates, top_k=3) if candidates else {}
    evidence = _ranked_text(ranked, candidates)
    action, reason = decide_action(request.payment)
    return AuditNotification(event_id=request.payment.event_id, action=action, reason=reason, evidence=evidence)


def _ranked_text(ranked: dict[str, Any], candidates: list[str]) -> list[str]:
    results = ranked.get("results", [])
    texts: list[str] = []
    for item in results:
        if isinstance(item.get("candidate"), str):
            texts.append(item["candidate"])
        elif isinstance(item.get("index"), int) and 0 <= item["index"] < len(candidates):
            texts.append(candidates[item["index"]])
    return texts or candidates[:3]

from decimal import Decimal

from fintech_kb.payment_review import Action, PaymentEvent, PaymentStatus, ReviewRequest, review_payment


class RecordedKnowledgeBackend:
    def __init__(self) -> None:
        self.query_embedding: list[float] | None = None

    def embed(self, text: str) -> list[float]:
        return [0.25, 0.75]

    def query(self, collection: str, embedding: list[float], top_k: int = 5) -> dict:
        self.query_embedding = embedding
        return {"matches": [{"metadata": {"text": "Routine settlement guidance."}}]}

    def rerank(self, query: str, candidates: list[str], top_k: int = 3) -> dict:
        return {"results": [{"index": 0}]}


def test_high_value_payment_requires_review_despite_routine_evidence() -> None:
    backend = RecordedKnowledgeBackend()
    request = ReviewRequest(
        question="Can operations release this settled payment?",
        payment=PaymentEvent(
            event_id="evt_2026_0906_01",
            account_ref="acct_masked_47",
            amount=Decimal("12500.00"),
            currency="USD",
            status=PaymentStatus.SETTLED,
        ),
    )

    result = review_payment(request, backend)

    assert backend.query_embedding == [0.25, 0.75]
    assert result.action is Action.REVIEW
    assert result.event_id == "evt_2026_0906_01"
    assert result.evidence == ["Routine settlement guidance."]

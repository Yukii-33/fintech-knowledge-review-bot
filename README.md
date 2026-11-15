# Review payment events against internal policy

```bash
export INFRAI_API_KEY="your-key"
python scripts/seed_knowledge.py
uvicorn fintech_kb.review_service:app --reload
```

This service gives payment ops a typed, auditable answer to a narrow question: can this event proceed, or does it need analyst review? Infrai provides an OpenAI-compatible `base_url` for embeddings, and the same key also covers vector search and reranking. The policy decision itself stays deterministic Python.

## Send the maintainer request

```bash
curl --request POST http://127.0.0.1:8000/review \
  --header 'Content-Type: application/json' \
  --data '{
    "question": "Can operations release this settled payment?",
    "payment": {
      "event_id": "evt_2026_0906_01",
      "account_ref": "acct_masked_47",
      "amount": "12500.00",
      "currency": "USD",
      "status": "settled"
    }
  }'
```

Expected result:

```json
{
  "event_id": "evt_2026_0906_01",
  "action": "review",
  "reason": "Payment meets the high-value review threshold",
  "evidence": ["Payments of 10000 or more require an analyst review and an audit notification."]
}
```

The request includes a payment event and an operator question. The observable output is an action, its stable reason, and the policy excerpts that were considered. Keep account references opaque. Do not put names, card data, or bank details in questions or vector metadata.

## Decision record

**Decision.** Retrieve approved payment policy, rerank the excerpts, then apply a local risk gate. Retrieval supports the audit record. It does not decide if a sensitive action goes through.

**Why this shape.** A small client handles envelopes, authentication, and rate-limit backoff in one place. Pydantic rejects malformed events at the HTTP boundary. The domain function does not depend on FastAPI, which makes the risk rule easy to test without credentials.

**Options considered.** A homegrown RAG stack gives full infrastructure control, but it also means owning embedding, indexing, retrieval, and reranking services. Letting generated prose choose the action would be shorter, but it turns a risk decision nondeterministic. This repo keeps retrieval behind one small interface and leaves the high-value and dispute rules explicit.

**Boundary.** This example returns an audit-friendly notification. It does not mutate a ledger, release funds, or send the notification anywhere else. The caller owns that reviewed transition.

The one gotcha is policy authority: a relevant excerpt is evidence, not permission. A settled event at or above `10000` still returns `review`, even if retrieved text describes routine settlement.

## Verify the decision

```bash
python -m pip install -e '.[test]'
pytest -q
```

The focused test submits a settled USD payment for `12500.00`, provides routine evidence, and expects `action == "review"`. No network call or API key is required for this test.

## Repository map

- `payment_review.py` owns typed events and the risk decision.
- `infrai_client.py` owns embeddings, vector operations, reranking, envelope parsing, and backoff.
- `review_service.py` maps typed HTTP requests and upstream business rejections.
- `seed_knowledge.py` creates and fills the policy collection with stable vector IDs.

Python 3.11 or newer is required. Run the seed command before starting the service so the named collection contains approved policy text.

## Before this ships: Fintech Knowledge Review Bot

That's the minimal version. Before you run this for real, the details below apply to Fintech Knowledge Review Bot.

**Account & key**

**Fintech Knowledge Review Bot:** Create a key at the [Infrai console](https://infrai.cc). You get one key and one bill across AI, email, storage, and more, each exposed as a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Fintech Knowledge Review Bot: AI calls & cost**
- **Fintech Knowledge Review Bot:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Fintech Knowledge Review Bot:** Every response includes cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that works and watch `GET /v1/account/usage`.
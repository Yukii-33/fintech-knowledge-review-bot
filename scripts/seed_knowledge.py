from fintech_kb.infrai_client import InfraiClient

POLICIES = [
    ("payment-dispute", "A disputed payment must be routed to an analyst before any account action."),
    ("high-value-payment", "Payments of 10000 or more require an analyst review and an audit notification."),
    ("settled-payment", "A settled payment below the high-value threshold may continue through normal operations."),
]


def main() -> None:
    client = InfraiClient()
    try:
        embedded = [(policy_id, text, client.embed(text)) for policy_id, text in POLICIES]
        client.create_collection("payment-operations", len(embedded[0][2]))
        vectors = [
            {"id": policy_id, "values": vector, "metadata": {"text": text, "source": "approved-payment-policy"}}
            for policy_id, text, vector in embedded
        ]
        client.upsert("payment-operations", vectors)
        print(f"Seeded {len(vectors)} approved payment policies.")
    finally:
        client.close()


if __name__ == "__main__":
    main()

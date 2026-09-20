"""Deterministic, GDPR-safe synthetic data helpers. The LLM proposes *shapes*; this module guarantees safety."""
import random, re
from faker import Faker  # add `faker` to requirements when enabling

EDGE_STRINGS = ["", " ", "O'Brien; DROP TABLE users;--", "Zoë 😀 مرحبا", "A" * 255, "<script>alert(1)</script>", "0", "-1", "9" * 20]


def safe_persona(seed: int) -> dict:
    f = Faker(); Faker.seed(seed); random.seed(seed)
    return {"name": f.name(), "email": f"user{seed}@example.test", "phone": f"+1-555-01{seed % 100:02d}",
            "amount": random.choice([0, 0.01, -5, 2**31, 99999999.99]), "edge": random.choice(EDGE_STRINGS)}


PII = re.compile(r"[\w.+-]+@(?!example\.test)[\w-]+\.[\w.]+|\b\d{3}-\d{2}-\d{4}\b|\b(?:\d[ -]*?){13,16}\b")


def assert_no_real_pii(sql: str) -> None:
    if PII.search(sql):
        raise ValueError("Synthetic seed contains PII-shaped data; rejecting")

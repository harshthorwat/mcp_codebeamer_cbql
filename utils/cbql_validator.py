import re
from utils.spec import CBQL_SPEC

FORBIDDEN_KEYWORDS = [
    "SELECT", "UPDATE", "DELETE", "INSERT", "JOIN"
]

SCOPE_PATTERN = re.compile(
    r"\b(tracker\s*=|tracker\s+IN|project\s*=)", re.IGNORECASE
)

def validate_cbql(cbql: str):
    if not cbql or not cbql.strip():
        raise ValueError("CBQL cannot be empty")

    upper = cbql.upper()

    for kw in FORBIDDEN_KEYWORDS:
        if kw in upper:
            raise ValueError(
                f"Invalid CBQL: '{kw}' is not supported. "
                "CBQL is not SQL."
            )

    if not SCOPE_PATTERN.search(cbql):
        raise ValueError(
            "Invalid CBQL: tracker or project scope is required."
        )

    if ";" in cbql:
        raise ValueError("Multiple CBQL statements are not allowed.")

    return cbql.strip()

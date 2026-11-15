"""Independent D1 order-export verifier used in the version change experiment."""
import hashlib
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
import sys

from openpyxl import load_workbook


def verify(directory):
    # D1 asks for four columns and limits orders to each role's visible region.
    expected_rows = {
        "A-101": (datetime(2026, 11, 14, 22), "paid", Decimal("128.35")),
        "A-102": (datetime(2026, 11, 14, 23), "unpaid", Decimal("0")),
        "B-201": (datetime(2026, 11, 15), "paid", Decimal("6.08")),
    }
    scopes = {"east": {"A-101", "A-102"}, "west": {"B-201"}, "cross": set(expected_rows)}
    exits = json.loads((directory / "export-exits.json").read_text())
    a2 = exits["viewer"] == 3 and not (directory / "viewer.xlsx").exists()
    a3 = True
    for role, permitted in scopes.items():
        book = load_workbook(directory / f"{role}.xlsx", read_only=True, data_only=True)
        try:
            header, *rows = list(book["Orders"].values)
            a2 &= exits[role] == 0 and sorted(row[0] for row in rows) == sorted(permitted)
            a3 &= header == ("order_id", "created_at", "status", "amount_paid") and all(
                len(row) == 4 and type(row[3]) in (int, float)
                and (row[1], row[2], Decimal(str(row[3]))) == expected_rows.get(row[0])
                for row in rows
            )
        finally:
            book.close()
    report = {**json.loads((directory / "binding.json").read_text()), "A2": a2, "A3": a3,
              "verdict": "pass" if a2 and a3 else "rework",
              "verifier_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (directory / "report.json").write_text(json.dumps(report, sort_keys=True) + "\n")


if __name__ == "__main__":
    verify(Path(sys.argv[1]))

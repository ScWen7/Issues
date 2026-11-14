"""Read exported XLSX files as an independent consumer under D2."""
import argparse
import hashlib
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zipfile import BadZipFile

from openpyxl import load_workbook


ROLES = {"east": ["A-101", "A-102"], "west": ["B-201"], "cross": ["A-101", "A-102", "B-201"], "viewer": []}
HEADER = ("order_id", "created_at", "status", "amount_paid", "payment_time")
# Business oracle uses literal local wall times, independent of the exporter's time conversion.
VALUES = {
    "A-101": (datetime(2026, 11, 14, 22), "paid", Decimal("128.35"), datetime(2026, 11, 15, 0, 15)),
    "A-102": (datetime(2026, 11, 14, 23), "unpaid", Decimal("0.00"), None),
    "B-201": (datetime(2026, 11, 15, 0), "paid", Decimal("6.08"), datetime(2026, 11, 15, 1, 30)),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def row_valid(row):
    order_id, created, status, amount, paid = row
    if order_id not in VALUES or type(amount) not in (int, float):
        return False
    return (created, status, Decimal(str(amount)), paid) == VALUES[order_id]


def inspect(directory, binding):
    exits = json.loads((directory / "export-exits.json").read_text())
    checks = {}
    artifacts = []
    for role, expected in ROLES.items():
        path = directory / f"{role}.xlsx"
        observation = {"exit": exits[role], "workbook": path.is_file()}
        checks[role] = observation
        if path.is_file():
            artifacts.append({"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)})
        if role == "viewer":
            observation["A2"] = exits[role] == 3 and not path.exists()
            continue
        observation.update(A2=False, A3=False)
        if not path.is_file():
            observation["error"] = "missing workbook"
            continue
        try:
            workbook = load_workbook(path, read_only=True, data_only=True)
        except (BadZipFile, OSError, ValueError, KeyError) as error:
            observation["error"] = type(error).__name__
            continue
        try:
            if "Orders" not in workbook.sheetnames:
                continue
            rows = iter(workbook["Orders"].values)
            header = next(rows, ())
            if not header or header[0] != "order_id":
                continue
            data = list(rows)
            ids = [row[0] for row in data]
            observation["ids"] = ids
            observation["A2"] = exits[role] == 0 and sorted(ids) == sorted(expected)
            observation["A3"] = (header == HEADER and bool(data)
                                 and all(len(row) == len(HEADER) and row_valid(row) for row in data))
        finally:
            workbook.close()
    a2 = all(item["A2"] for item in checks.values())
    a3 = all(checks[role]["A3"] for role in ROLES if role != "viewer")
    return {**binding, "A2": a2, "A3": a3, "verdict": "pass" if a2 and a3 else "rework",
            "checks": checks, "artifacts": artifacts, "verifier_sha256": sha(Path(__file__))}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    binding = json.loads((args.directory / "binding.json").read_text())
    write_json(args.directory / "report.json", inspect(args.directory, binding))
    # A completed verifier publishes its finding whether the candidate passed or requires rework.


if __name__ == "__main__":
    main()

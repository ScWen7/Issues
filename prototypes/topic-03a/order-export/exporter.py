"""Example order exporter at the candidate Git revision."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import xlsxwriter


def local_time(value):
    moment = datetime.fromisoformat(value)
    return moment.astimezone(ZoneInfo("Asia/Shanghai")).replace(tzinfo=None)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("role")
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    policy = json.loads(Path("scope.json").read_text())
    if args.role not in policy:
        print("export permission required")
        return 3
    orders = json.loads(Path("orders.json").read_text())
    with xlsxwriter.Workbook(args.target) as book:
        book.set_properties({"created": datetime(2026, 1, 1, tzinfo=timezone.utc)})
        sheet = book.add_worksheet("Orders")
        date_style = book.add_format({"num_format": "yyyy-mm-dd hh:mm:ss"})
        money_style = book.add_format({"num_format": "0.00"})
        sheet.write_row(0, 0, ["order_id", "created_at", "status", "amount_paid", "payment_time"])
        row = 1
        for order in orders:
            if order["region"] not in policy[args.role]:
                continue
            sheet.write_string(row, 0, order["id"])
            sheet.write_datetime(row, 1, local_time(order["created"]), date_style)
            sheet.write_string(row, 2, order["status"])
            sheet.write_number(row, 3, order["cents"] / 100, money_style)
            if order["paid"]:
                sheet.write_datetime(row, 4, local_time(order["paid"]), date_style)
            row += 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

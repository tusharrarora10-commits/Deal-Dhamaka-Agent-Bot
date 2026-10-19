"""Reads a product/quantity file (.csv or .xlsx/.xls) and aggregates duplicate
names within the file. Also generates sample template files."""
import csv
from collections import OrderedDict
from pathlib import Path

import openpyxl

NAME_HEADERS = {"product name", "product", "name", "item", "item name"}
QTY_HEADERS = {"quantity", "qty", "count", "stock"}

CONTACT_NAME_HEADERS = {"name", "contact name", "contact"}
PHONE_HEADERS = {"phone", "phone number", "mobile", "mobile number", "contact number"}

SAMPLE_HEADERS = ["Product Name", "Quantity"]
SAMPLE_ROWS = [
    ["Sample Product A", 10],
    ["Sample Product B", 5],
]


class ImportError_(Exception):
    pass


def _find_two_columns(header_row, first_headers, second_headers):
    first_col = second_col = None
    for idx, cell in enumerate(header_row):
        value = (str(cell).strip().lower() if cell is not None else "")
        if value in first_headers and first_col is None:
            first_col = idx
        elif value in second_headers and second_col is None:
            second_col = idx
    return first_col, second_col


def _find_columns(header_row):
    return _find_two_columns(header_row, NAME_HEADERS, QTY_HEADERS)


def _aggregate(header_row, data_rows):
    name_col, qty_col = _find_columns(header_row)
    if name_col is None or qty_col is None:
        raise ImportError_(
            "Could not find product name / quantity columns.\n"
            "Expected headers like 'Product Name' and 'Quantity' in the first row."
        )

    aggregated = OrderedDict()
    for row in data_rows:
        if row is None:
            continue
        if name_col >= len(row) or qty_col >= len(row):
            continue
        raw_name = row[name_col]
        raw_qty = row[qty_col]
        if raw_name is None or str(raw_name).strip() == "":
            continue

        name = str(raw_name).strip()
        try:
            qty = int(float(raw_qty)) if raw_qty not in (None, "") else 0
        except (ValueError, TypeError):
            qty = 0

        key = name.lower()
        if key in aggregated:
            existing_name, existing_qty = aggregated[key]
            aggregated[key] = (existing_name, existing_qty + qty)
        else:
            aggregated[key] = (name, qty)

    if not aggregated:
        raise ImportError_("No product rows found below the header.")

    return list(aggregated.values())


def _aggregate_contacts(header_row, data_rows):
    name_col, phone_col = _find_two_columns(header_row, CONTACT_NAME_HEADERS, PHONE_HEADERS)
    if name_col is None or phone_col is None:
        raise ImportError_(
            "Could not find Name / Phone columns.\n"
            "Expected headers like 'Name' and 'Phone' in the first row."
        )

    contacts = OrderedDict()
    for row in data_rows:
        if row is None:
            continue
        if name_col >= len(row) or phone_col >= len(row):
            continue
        raw_name = row[name_col]
        raw_phone = row[phone_col]
        if raw_name is None or str(raw_name).strip() == "":
            continue
        if raw_phone is None or str(raw_phone).strip() == "":
            continue

        name = str(raw_name).strip()
        phone = str(raw_phone).strip()
        contacts[phone] = (name, phone)  # last occurrence of a phone wins

    if not contacts:
        raise ImportError_("No contact rows found below the header.")

    return list(contacts.values())


def _read_xlsx(file_path, aggregator=_aggregate):
    wb = openpyxl.load_workbook(file_path, data_only=True, read_only=True)
    sheet = wb.active
    rows = sheet.iter_rows(values_only=True)
    try:
        header_row = next(rows)
    except StopIteration:
        raise ImportError_("The selected file is empty.")
    return aggregator(header_row, rows)


def _read_csv(file_path, aggregator=_aggregate):
    with open(file_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        try:
            header_row = next(reader)
        except StopIteration:
            raise ImportError_("The selected file is empty.")
        return aggregator(header_row, reader)


def read_products(file_path: str):
    """Returns an ordered list of (product_name, total_quantity) tuples,
    aggregating duplicate product names found within the same file."""
    ext = Path(file_path).suffix.lower()
    if ext in (".xlsx", ".xlsm", ".xls"):
        return _read_xlsx(file_path)
    if ext == ".csv":
        return _read_csv(file_path)
    raise ImportError_(f"Unsupported file type '{ext}'. Please use .csv or .xlsx.")


def read_contacts(file_path: str):
    """Returns a list of (name, phone) tuples from a .csv/.xlsx file with
    Name / Phone columns."""
    ext = Path(file_path).suffix.lower()
    if ext in (".xlsx", ".xlsm", ".xls"):
        return _read_xlsx(file_path, aggregator=_aggregate_contacts)
    if ext == ".csv":
        return _read_csv(file_path, aggregator=_aggregate_contacts)
    raise ImportError_(f"Unsupported file type '{ext}'. Please use .csv or .xlsx.")


def write_sample_csv(file_path: str) -> None:
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(SAMPLE_HEADERS)
        writer.writerows(SAMPLE_ROWS)


def write_sample_xlsx(file_path: str) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(SAMPLE_HEADERS)
    for row in SAMPLE_ROWS:
        ws.append(row)
    wb.save(file_path)

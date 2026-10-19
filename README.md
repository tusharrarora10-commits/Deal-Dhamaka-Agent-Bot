# Product Quantity Tracker

A desktop app that imports products (name + quantity) from a CSV/Excel file into
a local database, and lets you send a WhatsApp message about a product (with a
description and Amazon link) to a saved contact.

## How it works

- `app/main.py` — Tkinter GUI: two panels, Products and Send WhatsApp Message.
- `app/file_import.py` — reads `.csv` / `.xlsx` / `.xls` files, finds the
  "Product Name" / "Quantity" columns (case-insensitive; also accepts Product/Name/Item
  and Qty/Count/Stock), sums quantities for names that repeat *within the same file*,
  and generates the downloadable sample template.
- `app/db.py` — SQLite storage at `~/.indian_tester_app/products.db` (created on first
  run, independent of where the executable lives). Holds products (name, quantity,
  description, Amazon link) and contacts (name, phone).
- `app/whatsapp.py` — unofficial WhatsApp Web automation via Selenium (see below).

## Products panel

- **Import CSV / Excel File** — pick a `.csv`/`.xlsx`/`.xls` file with `Product Name`
  and `Quantity` columns. Rows are aggregated by name within the file, then merged
  into the database.
- **Download Sample File** — saves a template (CSV or XLSX, your choice) with the
  correct headers and two example rows, so you know exactly what the import expects.
- Double-click a product row to set its **Description** and **Amazon Link** — these
  are saved per product and reused (editable) when you send a WhatsApp message about it.

### Duplicate handling on import

For each imported product name that already exists in the database, a dialog asks:
- **Increase Quantity** — adds the imported quantity to the existing entry.
- **Create New Entry** — inserts a separate row with the same name (kept distinct).
- **Cancel this item** — skips that one product.

## Send WhatsApp Message panel

1. **Connect WhatsApp** — opens a Chrome window showing a WhatsApp QR code. Scan it
   once with your phone (WhatsApp → Linked Devices). The login session is stored in
   `~/.indian_tester_app/whatsapp_profile`, so you generally only do this once per
   machine — it persists across app restarts.
2. **Manage Contacts** — add/edit/delete contacts (Name + Phone, with country code,
   e.g. `+91XXXXXXXXXX`). Stored locally in the same database.
3. Pick a **Contact** and a **Product** — selecting a product auto-fills its saved
   Description and Amazon Link, both still editable before sending.
4. The **message preview** updates live; click **Send WhatsApp Message** to send it.

### How the WhatsApp integration works, and its limits

This uses **WhatsApp Web automation** (via Selenium), not the official WhatsApp
Business API:
- **Requires Google Chrome installed** on the machine — there's no way around this,
  since it drives a real WhatsApp Web browser session under your own WhatsApp account.
- The **first** connect needs internet access once, to download a matching
  chromedriver build (cached locally after that).
- It is **unofficial**: it relies on WhatsApp Web's page structure, which Meta can
  change at any time without notice. If sending breaks, the selectors in
  `app/whatsapp.py` are the first place to check.
- This kind of automation is against WhatsApp's Terms of Service for automated/bulk
  use — it's intended here for your own personal/business outreach to contacts you
  manage, not spam or mass messaging.
- If you need a fully supported, ToS-compliant integration instead, the alternative
  is the official **WhatsApp Business Cloud API** (Meta Business app + phone number +
  access token), which has different constraints (24-hour free-text messaging window,
  pre-approved templates otherwise) — ask if you'd like that swapped in instead.

## Why no "install packages on first launch"

Rather than downloading packages the first time the user runs the app (which needs
internet access and can fail), this project bundles all Python dependencies **into
the executable at build time** using PyInstaller. The one unavoidable runtime
dependency is Chrome itself (see above), needed only for the WhatsApp feature.

## Building the executable

PyInstaller builds for the OS it runs on — it cannot cross-compile. To ship both
platforms, run the matching script **on each OS**:

- On macOS: `./build_mac.sh` → produces `dist/mac/ProductQuantityTracker.app`
- On Windows: `build_win.bat` → produces `dist\win\ProductQuantityTracker\ProductQuantityTracker.exe`

Each script creates its own virtual environment, installs `requirements.txt`, and
runs PyInstaller. The output folder is fully self-contained — copy/zip the whole
`ProductQuantityTracker` folder (or `.app` on Mac) to distribute it; users just
open it like any other application (Chrome must already be installed for WhatsApp
sending to work).

## Running from source (for development)

```bash
python3 -m venv .venv
source .venv/bin/activate   # .venv\Scripts\activate on Windows
pip install -r requirements.txt
python app/main.py
```

## Expected product file format

| Product Name | Quantity |
|---|---|
| Sample Product A | 10 |
| Sample Product B | 5 |

Header row required; column names are matched case-insensitively. Use the
**Download Sample File** button in the app to get this exact template.

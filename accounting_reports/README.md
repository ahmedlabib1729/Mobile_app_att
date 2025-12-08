# Accounting Reports Module for Odoo 18

## 📋 Description

Modern and interactive accounting reports module with beautiful UI/UX design.

## 📊 Available Reports

| Report | Status | Description |
|--------|--------|-------------|
| **General Ledger** | ✅ Ready | Account-based ledger with journal entries |
| Partner Ledger | 🔜 Coming | Partner-based transactions |
| Trial Balance | 🔜 Coming | Account balances summary |
| Aged Receivable | 🔜 Coming | Receivables aging analysis |
| Aged Payable | 🔜 Coming | Payables aging analysis |
| Cash Flow | 🔜 Coming | Cash flow statement |

## ✨ Features

- **Modern UI**: Ultra-modern design with gradients, shadows, and animations
- **Full Width**: Reports take full browser width
- **Interactive Tree**: Expandable/Collapsible 3-level hierarchy
- **Multiple Filters**: Period, Date Range, Journals, Posted Only
- **KPI Cards**: Quick summary with animated cards
- **Export Excel**: Download report as CSV
- **Print PDF**: Print-optimized styles
- **Responsive**: Works on all screen sizes

## 📁 Module Structure

```
accounting_reports/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── general_ledger.py
├── security/
│   └── ir.model.access.csv
├── views/
│   └── general_ledger_action.xml
├── data/
│   └── menu.xml
└── static/
    └── src/
        ├── css/
        │   ├── report_common.css
        │   └── general_ledger.css
        ├── js/
        │   └── general_ledger.js
        └── xml/
            └── general_ledger.xml
```

## 🔧 Installation

### Option 1: Extract ZIP
1. Download `accounting_reports.zip`
2. Extract to your Odoo addons folder:
   ```bash
   unzip accounting_reports.zip -d /path/to/odoo/addons/
   ```

### Option 2: Copy Folder
1. Copy the `accounting_reports` folder to your Odoo addons directory
2. Ensure the folder is named exactly `accounting_reports`

### Then:
3. Restart Odoo:
   ```bash
   sudo systemctl restart odoo18
   ```
4. Go to **Apps** → **Update Apps List**
5. Search for **Accounting Reports**
6. Click **Install**

## 📖 Usage

1. Go to **Accounting Reports** menu
2. Click on **Reports** → **General Ledger**
3. Select your filters:
   - Period: Today, Week, Month, Quarter, Year, Custom
   - Date range: From / To
   - Journals: Filter by specific journals
   - Posted Only: Include only posted entries
4. Click **Refresh** to update the report
5. Use **Export** to download as Excel/CSV
6. Use **Print** for PDF output

## 🎨 General Ledger Report Structure

```
┌─────────────────────────────────────────────────────────────────┐
│ 📊 General Ledger                                               │
│ 01/01/2025 - 26/11/2025                                        │
├─────────────────────────────────────────────────────────────────┤
│ Period: [Today] [Week] [Month] [Quarter] [Year] [Custom]       │
│ From: [________] To: [________] ☑ Posted Only                  │
│ Journals: ☑ BANK ☑ CASH ☑ INV ☑ BILL                          │
│ [Refresh] [Export] [Print] [Expand All] [Collapse All]         │
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────┬─────────┬─────────┬─────────┬─────────┐            │
│ │📊 25    │📝 150   │📈100,000│📉 80,000│⚖️ 20,000│            │
│ │Accounts │ Entries │ Debit   │ Credit  │ Balance │            │
│ └─────────┴─────────┴─────────┴─────────┴─────────┘            │
├─────────────────────────────────────────────────────────────────┤
│ Account / Entry / Line     │ Date    │ Ref   │ Debit  │ Credit │
├─────────────────────────────────────────────────────────────────┤
│▶ [1001] Cash               │         │       │ 50,000 │ 30,000 │
│  ▶ 📄 INV/2025/001        │01/01/25 │ SO001 │ 10,000 │   -    │
│     ├─ Payment received   │         │       │ 10,000 │   -    │
│  ▶ 📄 BILL/2025/001       │02/01/25 │ PO001 │   -    │  5,000 │
│▶ [1100] Accounts Receivable│         │       │ 30,000 │ 20,000 │
├─────────────────────────────────────────────────────────────────┤
│📊 GRAND TOTAL              │         │       │100,000 │ 80,000 │
└─────────────────────────────────────────────────────────────────┘
```

## 🔐 Security

- **Account User**: Read access to reports
- **Account Manager**: Full access

## 📝 Dependencies

- `account` (Invoicing/Accounting)
- `web` (Web Framework)

## 🆘 Troubleshooting

### Report not loading
1. Check browser console for errors
2. Clear browser cache
3. Run `./odoo-bin -u accounting_reports`

### Styles not applied
1. Run with `--dev=all` flag to reload assets
2. Clear assets: Delete `filestore/*/static/` cache

### Module not found
1. Ensure folder name is `accounting_reports`
2. Check `__manifest__.py` exists
3. Update Apps List in Odoo

## 📜 License

LGPL-3

## 👨‍💻 Author

Your Company - https://www.yourcompany.com

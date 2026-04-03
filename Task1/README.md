# Task1: Web Scraper with Daily Price Comparison

This project scrapes product listings from an e-commerce site, stores each day's snapshot in SQLite, compares today's prices with yesterday's prices, and exports a CSV report when price changes are detected.

## What it does

- Scrapes paginated product listings
- Uses rotating user-agents, retries, and polite delays
- Stores `SKU`, `name`, and `price` in `products.db`
- Compares today's snapshot with yesterday's snapshot
- Exports a CSV report to the `reports` folder

## Files

- `main.py`: runs the scraper and reporting flow
- `scraper.py`: request handling, anti-bot mitigation, pagination, parsing
- `database.py`: SQLite schema and product snapshot storage
- `report.py`: daily comparison and CSV export
- `setup_nightly_task.ps1`: creates a Windows scheduled task for nightly runs

## Run manually

```powershell
python main.py
```

## Nightly schedule setup on Windows

Run this once in PowerShell from the project folder:

```powershell
.\setup_nightly_task.ps1
```

This creates a daily scheduled task named `Task1NightlyScraper` that runs at `02:00`.

If Python is not on your PATH, pass the full path:

```powershell
.\setup_nightly_task.ps1 -PythonPath "C:\Python312\python.exe"
```

You can also choose a different time:

```powershell
.\setup_nightly_task.ps1 -RunTime "01:30"
```

## Daily comparison logic

- Products are saved with a `scraped_date`
- The report compares records where `scraped_date = today`
- It matches them against records where `scraped_date = yesterday`
- Only products with changed prices are written to the CSV report

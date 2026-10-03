# Price Tracker

E-commerce price tracker that monitors product prices and sends Telegram alerts when prices drop.

## How It Works

```mermaid
flowchart TD
    A["⏰ GitHub Actions <br> (every 6 hours)"] 
    A --> B["🌐 Playwright Scraper<br>188 products across 12 pages"] 
    B --> C["🔁 Sync to MongoDB Atlas<br>(time series collection)"]
    C --> D{Price dropped?}
    D --> |Yes| E["📬 Telegram Alert"]
    B --> F["💾 Export CSV"]
    F --> G["☁️ Upload to Backblaze B2<br>(S3-compatible object storage)"]
```

## Demo

### Scraper Running on GitHub Actions
![GitHub Actions](assets/github-actions.png)

### Telegram Price Drop Alert
![Telegram Alert](assets/telegram-alert.png)

## Features

- Scrapes 188 products across 12 pages
- Detects sale prices vs normal prices
- Identifies variant vs simple products
- Stores price history in MongoDB time series collection
- Sends Telegram alert when price drops
- Exports scraped data as CSV and uploads to Backblaze B2 cloud storage
- Runs automatically every 6 hours via GitHub Actions

## Tech Stack

- Python 3.14 + uv
- Playwright (browser automation)
- MongoDB Atlas + pymongo (time series collection)
- httpx + Telegram Bot API
- Boto3 + Backblaze B2 (S3-compatible object storage)
- GitHub Actions (scheduling)

## Local Setup

1. Clone the repo
2. Install dependencies
   ```bash
   uv sync --locked --dev
   ```
3. Install Playwright browser
   ```bash
   uv run playwright install chromium
   ```
4. Copy `.env.example` to `.env` and fill in your values
   ```bash
   cp .env.example .env
   ```
5. Run the scraper once
   ```bash
   uv run price-tracker
   ```

## Deployment (GitHub Actions)

1. Push the repository to GitHub
2. Go to **Settings → Secrets and variables → Actions**
3. Add the following repository secrets:
   - `MONGODB_URI`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `B2_KEY_ID`
   - `B2_APP_KEY`
   - `B2_BUCKET_NAME`
   - `B2_REGION`
   - `B2_ENDPOINT`
    > **Note:** B2_* values are used to upload CSV file to Backblaze B2 using its S3-compatible API. Any S3-compatible object storage service can be used instead.
4. Add the MongoDB Atlas API credentials as repository secrets:
   - `ATLAS_PUBLIC_KEY`
   - `ATLAS_PRIVATE_KEY`
   > **Note:** `ATLAS_PUBLIC_KEY` and `ATLAS_PRIVATE_KEY` are MongoDB Atlas API key credentials used by the workflow to temporarily allow the GitHub Actions runner to access MongoDB Atlas.\
   Create an API key with the **Project Network Access Manager** role under **Project → Project Identity & Access → Applications → API Keys**.
5. Add the following repository variable:
   - `ATLAS_GROUP_ID`
   > **Note:** `ATLAS_GROUP_ID` is your MongoDB Atlas Project ID, found under **Project Settings**.
6. Go to the **Actions** tab and trigger manually via **"Run workflow"**

The scraper will then run automatically every 6 hours.
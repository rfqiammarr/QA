# QA Automation

This project contains automation scripts for QA testing of a transaction management web application.

## Setup

1. Install Python dependencies:

   ```
   pip install -r requirements.txt
   ```

2. Create a `.env` file in the root directory with your configuration:

   ```
   BASE_URL=http://localhost:5132
   USERNAME=your_username
   PASSWORD=your_password
   TOTAL_TRANSAKSI=5
   MAX_RETRY_PER_ITEM=2
   ```

3. Run the automation script:
   ```
   python src/main.py [number_of_transactions]
   ```
   If no argument is provided, it defaults to 5 transactions.

## Description

The script uses Selenium WebDriver to automate the process of logging into the application and adding random transactions for QA testing purposes. It handles retries and error checking to ensure reliable execution.


import os
import yfinance as yf
import pandas as pd

def fetch_data(tickers, period="5y"):
   
    try:
        print(f"Fetching data from internet... Tickers: {tickers} | Period: {period}")
        
        # Download data using yfinance
        data = yf.download(tickers, period=period)
        
        # Check if the fetched data is empty 
        if data.empty:
            print("Warning: No data found for the requested period or ticker symbol is invalid.")
            return None
            
        print("Data fetched successfully!")
        return data
        
    except Exception as e:
        print(f"A system error occurred while fetching data: {e}")
        return None

if __name__ == "__main__":
    # 1. Define the list of 10 target tickers
    target_tickers = ['AAPL', 'MSFT', 'JPM', 'GLD', 'SPY', 'GOOGL', 'AMZN', 'BRK-B', 'XOM', 'TLT']
    
    # Fetch 5 years of historical data
    portfolio_data = fetch_data(tickers=target_tickers, period="5y")
    
    if portfolio_data is not None:
        # --- TASK 1: Save the raw output locally as a CSV ---
        
        # Create 'raw' directory inside the 'data' folder if it doesn't exist
        os.makedirs("data/raw", exist_ok=True)
        
        # Save the DataFrame to a CSV file
        csv_path = "data/raw/raw_portfolio_data.csv"
        portfolio_data.to_csv(csv_path)
        print(f"\n✅ SUCCESS: Raw data saved to '{csv_path}'.")
        
        
        # --- TASK 2: Verify that no ticker returned empty data ---
        
        empty_tickers = []
        # Iterate through each requested ticker
        for ticker in target_tickers:
            # Check if all 'Close' prices for the ticker are NaN (empty)
            if portfolio_data['Close'][ticker].isna().all():
                empty_tickers.append(ticker)
                
        if len(empty_tickers) == 0:
            print("✅ VERIFICATION: All tickers have data. No empty columns found!")
        else:
            print(f"❌ WARNING: The following tickers returned empty data: {empty_tickers}")
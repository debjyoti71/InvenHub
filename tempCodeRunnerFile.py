from pytrends.request import TrendReq
import matplotlib.pyplot as plt
import requests

query = "freeze"
url = f"http://suggestqueries.google.com/complete/search?client=firefox&q={query}"
response = requests.get(url)

if response.status_code == 200:
    suggestions = response.json()[1]
    print(suggestions)
else:
    print(f"Error: {response.status_code}")

# Initialize Pytrends
pytrends = TrendReq()

# Set the keyword(s) and timeframe for India
keywords = ["ac", "iphone"]  # Adjust keywords if needed
pytrends.build_payload(kw_list=keywords, timeframe='2023-01-01 2024-12-31', geo='IN')

# Get interest over time
trends = pytrends.interest_over_time()

# Check the data
if not trends.empty:
    print(trends)
    
    # Plot the trends
    plt.figure(figsize=(10, 5))
    for keyword in keywords:
        if keyword in trends.columns:
            plt.plot(trends[keyword], label=keyword)
    
    plt.title("Trend Over Time in India")
    plt.xlabel("Date")
    plt.ylabel("Interest")
    plt.legend()
    plt.grid(True)
    plt.show()
    
    # Save to CSV
    trends.to_csv('trend_data.csv', index=True) 
    print("Data saved to 'trend_data.csv'")
else:
    print("No data found for the given keyword(s).")

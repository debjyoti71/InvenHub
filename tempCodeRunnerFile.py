import requests

# Define the URL for the endpoint
url = "https://invenhub.onrender.com/esp-api/print?store_id=7"

# Send a GET request to the server
response = requests.get(url)

# Check the status code
print(f"Status Code: {response.status_code}")

# Print the raw response content to inspect what is returned
print("Response Text:", response.text)

# If the response is in JSON format, parse it
try:
    data = response.json()
    print("Response Data:")
    print(data)
except requests.exceptions.JSONDecodeError:
    print("Response is not in JSON format.")

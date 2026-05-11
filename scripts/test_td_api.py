import requests
import json

api_key = '1ceb0fd735ba4ab891e741ae353f1e60'
url = 'https://api.twelvedata.com/time_series'
params = {
    'symbol': 'AAPL',
    'interval': '1day',
    'outputsize': 5,
    'apikey': api_key
}

print("Calling Twelve Data API...")
print(f"URL: {url}")
print(f"Params: {params}")
print()

try:
    r = requests.get(url, params=params, timeout=10)
    print(f"Status Code: {r.status_code}")
    print(f"Response Headers: {dict(r.headers)}")
    print()
    
    data = r.json()
    print("Response JSON:")
    print(json.dumps(data, indent=2)[:1000])
    
    if data.get('status') == 'error':
        print(f"\n❌ Error: {data.get('message')}")
    elif 'values' in data:
        print(f"\n✅ Success! Got {len(data['values'])} bars")
    else:
        print(f"\n⚠️ Unexpected response format")
        
except Exception as e:
    print(f"❌ Exception: {e}")

import requests
import json

api_key = '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'

print("Testing Tavily API...")
print(f"API Key (first 12): {api_key[:12]}...")
print()

try:
    response = requests.post(
        'https://api.tavily.com/search',
        json={
            'api_key': api_key,
            'query': 'Bitcoin price news',
            'max_results': 1
        },
        timeout=10
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Success!")
        print(f"Results count: {len(data.get('results', []))}")
        if data.get('results'):
            first_result = data['results'][0]
            print(f"\nFirst result:")
            print(f"  Title: {first_result.get('title', 'N/A')[:80]}")
            print(f"  URL: {first_result.get('url', 'N/A')[:80]}")
    else:
        print(f"\n❌ Error: {response.text[:200]}")
        
except Exception as e:
    print(f"❌ Exception: {e}")

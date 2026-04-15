import requests

# Test correct GDELT query syntax
params = {
    "query": "India (misinformation fake fraud protest health disaster)",
    "mode": "artlist",
    "maxrecords": "5",
    "sort": "DateDesc",
    "format": "json",
}
try:
    r = requests.get("https://api.gdeltproject.org/api/v2/doc/doc", params=params, timeout=15)
    print(f"Status: {r.status_code}")
    ct = r.headers.get("content-type", "")
    print(f"ContentType: {ct}")
    body = r.text[:800]
    print(f"Body preview:\n{body}")
except Exception as e:
    print(f"Error: {e}")

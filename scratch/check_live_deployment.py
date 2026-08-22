import urllib.request

for url in ["https://nyaysetupro.in/", "https://nyaysetupro.in/admin", "https://nyaysetupro.in/admin/index.html", "https://nyaysetupro.in/admin/assets/index-ClWveFqy.js"]:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
            print(f"URL: {url}")
            print(f"Status: {resp.status}")
            print(f"Age / ETag / Date: {resp.headers.get('age')}, {resp.headers.get('etag')}, {resp.headers.get('x-vercel-id')}")
            print(f"Body preview (150 chars): {data[:150]}")
            print("-" * 50)
    except Exception as e:
        print(f"URL: {url} -> ERROR: {e}")

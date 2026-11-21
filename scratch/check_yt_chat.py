import urllib.request, re, json

req = urllib.request.Request("https://www.youtube.com/@IShowSpeed/live", headers={"User-Agent": "Mozilla/5.0"})
html = urllib.request.urlopen(req, timeout=10).read().decode("utf-8", "replace")
print("Found ytInitialData:", "ytInitialData" in html)
conts = re.findall(r'"continuation":"([^"]+)"', html)
print("Conts count:", len(conts))
for c in conts[:3]:
    print("Cont:", c[:50])

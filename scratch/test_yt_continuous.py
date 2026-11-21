import urllib.request, json, re, time

url = "https://www.youtube.com/@IShowSpeed/live"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
html = urllib.request.urlopen(req, timeout=12).read().decode("utf-8", "replace")
key_m = re.findall(r'"INNERTUBE_API_KEY":"([^"]+)"', html)
cont_m = re.findall(r'"continuation":"([^"]+)"', html)

if key_m and cont_m:
    key, cont = key_m[0], cont_m[0]
    api_url = f"https://www.youtube.com/youtubei/v1/live_chat/get_live_chat?key={key}"
    print("Testing continuous YouTube chat poll for 2 ticks...")
    for tick in range(2):
        payload = json.dumps({
            "context": {"client": {"clientName": "WEB", "clientVersion": "2.20230810.00.00"}},
            "continuation": cont
        }).encode("utf-8")
        api_req = urllib.request.Request(api_url, data=payload, headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
        data = json.loads(urllib.request.urlopen(api_req, timeout=10).read().decode("utf-8"))
        live_cont = data.get("continuationContents", {}).get("liveChatContinuation", {})
        actions = live_cont.get("actions", [])
        print(f"Tick {tick}: received {len(actions)} actions")
        new_conts = live_cont.get("continuations", [])
        for c in new_conts:
            inv = c.get("invalidationContinuationData") or c.get("timedContinuationData")
            if inv and inv.get("continuation"):
                cont = inv["continuation"]
                break
        time.sleep(2)
    print("YouTube chat continuous polling SUCCESS!")

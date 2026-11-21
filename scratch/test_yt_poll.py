import urllib.request, json, re

req = urllib.request.Request("https://www.youtube.com/@IShowSpeed/live", headers={"User-Agent": "Mozilla/5.0"})
html = urllib.request.urlopen(req, timeout=10).read().decode("utf-8", "replace")
innertube_key = re.findall(r'"INNERTUBE_API_KEY":"([^"]+)"', html)
conts = re.findall(r'"continuation":"([^"]+)"', html)
if innertube_key and conts:
    api_url = f"https://www.youtube.com/youtubei/v1/live_chat/get_live_chat?key={innertube_key[0]}"
    post_data = json.dumps({
        "context": {
            "client": {
                "clientName": "WEB",
                "clientVersion": "2.20230810.00.00"
            }
        },
        "continuation": conts[0]
    }).encode("utf-8")
    api_req = urllib.request.Request(api_url, data=post_data, headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    resp = json.loads(urllib.request.urlopen(api_req, timeout=10).read().decode("utf-8"))
    actions = resp.get("continuationContents", {}).get("liveChatContinuation", {}).get("actions", [])
    chat_items = []
    for a in actions:
        item = a.get("addChatItemAction", {}).get("item", {})
        msg_renderer = item.get("liveChatTextMessageRenderer")
        if msg_renderer:
            author = msg_renderer.get("authorName", {}).get("simpleText", "")
            runs = msg_renderer.get("message", {}).get("runs", [])
            text = "".join(r.get("text", "") for r in runs)
            chat_items.append((author, text))
    print(f"Extracted {len(chat_items)} real chat messages:")
    for a, t in chat_items[:5]:
        print(f"[{a}]: {t}")

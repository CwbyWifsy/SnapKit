import json
import urllib.request
import urllib.error

# ====== 你要改的 ======
BASE_URL = "https://codeflow.asia"   # 有些站需要 /v1：比如 https://codeflow.asia/v1
API_KEY  = "sk-zuchCSYIJjg2K6qhTjdAESrOYQ8Gt1teAg7duQuwBQvS2Peg"
MODELS = [
    "claude-haiku-4-5-20251001",
    "claude-sonnet-4-5-20250929",
    "claude-opus-4-5-20251101",
    "claude-opus-4-6",
]
# ======================

def post_json(url, payload, headers, timeout=20):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return e.code, body
    except Exception as e:
        return None, repr(e)

def build_url(path):
    base = BASE_URL.rstrip("/")
    if base.endswith("/v1"):
        return f"{base}{path}"
    return f"{base}/v1{path}"

def main():
    url = build_url("/chat/completions")  # 大多数“中转站”做成 OpenAI 兼容
    payload_tpl = {
        "messages": [{"role": "user", "content": "ping"}],
        "temperature": 0,
        "max_tokens": 16,
    }

    # 两种常见鉴权头都试：Bearer / x-api-key
    auth_headers_list = [
        {"Authorization": f"Bearer {API_KEY}"},
        {"x-api-key": API_KEY},
    ]

    print("Target:", url)
    for model in MODELS:
        payload = dict(payload_tpl)
        payload["model"] = model

        ok = False
        for auth in auth_headers_list:
            headers = {"Content-Type": "application/json", **auth}
            status, body = post_json(url, payload, headers)
            if status == 200:
                print(f"✅ {model} OK (auth={list(auth.keys())[0]})")
                print(body[:300].replace("\n", " "), "...\n")
                ok = True
                break
            else:
                print(f"… {model} -> {status} (auth={list(auth.keys())[0]}): {body[:160].replace(chr(10),' ')}")
        if not ok:
            print(f"❌ {model} failed on both auth headers\n")

if __name__ == "__main__":
    main()

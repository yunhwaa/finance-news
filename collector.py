"""
collector.py — Gemini로 뉴스 수집 후 싸이월드×인스타 사이트 자동 업데이트
"""
import json, random, re, subprocess, webbrowser
from datetime import datetime
from pathlib import Path
from google import genai
from google.genai import types
import config

HTML_FILE = Path("docs/index.html")
HISTORY_FILE = Path("docs/history.json")

def collect_news(keywords):
    keyword_str = ", ".join(keywords)
    print(f"  🔍 키워드: {keyword_str}")
    client = genai.Client(api_key=config.API_KEY)
    prompt = f"""다음 키워드로 최신 금융·경제 뉴스를 검색하고 {len(keywords)}개 요약해주세요: {keyword_str}
순수 JSON만 반환 (마크다운 없이):
{{"items":[{{"id":0,"cat":"카테고리","level":"고/중/저","bg":"어두운 hex 배경색 (예:#1a3a6b)","title":"제목","hl":"한줄요약","summary":"3~4문장","points":["포인트1","포인트2","포인트3"],"imp":"실무시사점","sources":[{{"publisher":"언론사","title":"기사제목","url":"https://"}}]}}]}}
결과없으면 {{"items":[]}}. 각 카드 bg는 어두운 계열 hex 색상으로."""
    try:
        resp = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.3,
            ),
        )
        text = resp.text.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"): text = text[4:]
        return json.loads(text.strip()).get("items", [])
    except Exception as e:
        print(f"  ⚠️ 오류: {e}")
        return []

def load_history():
    if HISTORY_FILE.exists():
        try: return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except: return []
    return []

def save_history(history):
    HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")

def update_html(new_items, history):
    now = datetime.now()
    html = HTML_FILE.read_text(encoding="utf-8")
    # id 재할당
    for i, item in enumerate(history):
        item["id"] = i
    news_json = json.dumps(history, ensure_ascii=False, indent=2)
    html = re.sub(r'const NEWS_DATA = \[.*?\];', f'const NEWS_DATA = {news_json};', html, flags=re.DOTALL)
    next_t = "20:00" if now.hour < 12 else "08:00 (내일)"
    meta = {
        "lastCollect": now.strftime("%Y-%m-%d %H:%M"),
        "nextCollect": next_t,
        "todayCollect": len(new_items),
        "totalArticles": len(history),
        "market": {"kospi":"수집중","usdkrw":"수집중","bond":"수집중","rate":"3.50%"},
        "keywords": list({tag for n in history for tag in ["#"+n.get("cat","").replace(" ","")]}),
        "todayWord": new_items[0]["hl"] if new_items else "오늘도 AI가 뉴스를 수집했어요 ✦"
    }
    meta_json = json.dumps(meta, ensure_ascii=False, indent=2)
    html = re.sub(r'const SITE_META = \{.*?\};', f'const SITE_META = {meta_json};', html, flags=re.DOTALL)
    HTML_FILE.write_text(html, encoding="utf-8")
    print(f"  💾 index.html 업데이트 완료")

def git_push():
    if not config.AUTO_GIT_PUSH:
        print("  📤 수동 push 필요: git add docs/ && git commit -m 'update' && git push")
        return
    try:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        subprocess.run(["git","add","docs/"], check=True)
        subprocess.run(["git","commit","-m",f"auto: 뉴스 수집 {now_str}"], check=True)
        subprocess.run(["git","push"], check=True)
        print(f"  🚀 GitHub push 완료!")
    except Exception as e:
        print(f"  ⚠️ Git push 실패: {e}")

def run():
    now = datetime.now()
    print(f"\n{'='*52}\n  🚀 수집 시작 — {now.strftime('%Y-%m-%d %H:%M:%S')}\n{'='*52}")
    keywords = random.sample(config.KEYWORDS, min(config.COLLECT_COUNT, len(config.KEYWORDS)))
    print("\n[1/4] 뉴스 수집 중...")
    new_items = collect_news(keywords)
    if not new_items:
        print("  ❌ 수집 실패."); return
    for item in new_items:
        item["collectedAt"] = now.strftime("%Y-%m-%d %H:%M")
    print(f"  ✅ {len(new_items)}건")
    print("\n[2/4] 히스토리 업데이트...")
    history = load_history()
    history = new_items + history
    history = history[:100]
    save_history(history)
    print(f"  📚 누적 {len(history)}건")
    print("\n[3/4] index.html 업데이트...")
    update_html(new_items, history)
    print("\n[4/4] GitHub push...")
    git_push()
    print(f"\n{'='*52}\n  🎉 완료!\n{'='*52}\n")
    webbrowser.open(HTML_FILE.resolve().as_uri())

if __name__ == "__main__":
    run()

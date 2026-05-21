"""
collector.py — google-genai (신버전) 으로 금융 리스크 뉴스 수집
"""

import json
import random
import smtplib
import ssl
import webbrowser
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from google import genai
from google.genai import types

import config


# ─── 뉴스 수집 ────────────────────────────────────────
def collect_news(keywords: list) -> list:
    keyword_str = ", ".join(keywords)
    print(f"  🔍 검색 키워드: {keyword_str}")

    client = genai.Client(api_key=config.API_KEY)

    prompt = f"""다음 키워드로 최신 금융 리스크 뉴스를 검색하고 카드뉴스 형태로 {len(keywords)}개 요약해주세요: {keyword_str}

반드시 아래 JSON 형식만 반환하세요 (마크다운 코드블록, 설명 없이 순수 JSON만):
{{
  "items": [
    {{
      "title": "뉴스 제목",
      "category": "카테고리 (예: 신용리스크, 규제동향, ESG 등)",
      "level": "고/중/저",
      "headline": "한 줄 핵심 요약",
      "summary": "핵심 내용 3~4문장 요약",
      "keypoints": ["핵심 포인트 1", "핵심 포인트 2", "핵심 포인트 3"],
      "implication": "금융권 실무 시사점 1~2문장",
      "date": "날짜 또는 최근"
    }}
  ]
}}
결과 없으면 {{"items":[]}}."""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite", 
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.3,
            ),
        )

        text = response.text.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()

        parsed = json.loads(text)
        return parsed.get("items", [])

    except json.JSONDecodeError as e:
        print(f"  ⚠️ JSON 파싱 오류: {e}")
        return []
    except Exception as e:
        print(f"  ⚠️ API 오류: {e}")
        return []


# ─── HTML 생성 ────────────────────────────────────────
def generate_html(items: list, date_str: str) -> str:

    def level_style(level):
        if "고" in str(level): return ("#ef4444", "#fef2f2", "ef4444,f59e0b")
        if "중" in str(level): return ("#f59e0b", "#fffbeb", "f59e0b,14b8a6")
        return ("#10b981", "#f0fdf4", "10b981,3b82f6")

    cards_html = ""
    for item in items:
        txt, bg, grad = level_style(item.get("level", ""))
        kp = "".join(f"<li>{p}</li>" for p in item.get("keypoints", []))
        cards_html += f"""
        <div class="card">
          <div class="card-banner" style="background:linear-gradient(90deg,#{grad})"></div>
          <div class="card-body">
            <div class="tag" style="color:{txt};background:{bg};border:1px solid {txt}33">
              {item.get('category','금융리스크')} · 리스크 {item.get('level','중')}
            </div>
            <h2>{item.get('title','')}</h2>
            <div class="headline">📌 {item.get('headline','')}</div>
            <p class="summary">{item.get('summary','')}</p>
            <ul class="keypoints">{kp}</ul>
            <div class="implication">
              <span class="imp-label">💼 실무 시사점</span>
              {item.get('implication','')}
            </div>
          </div>
          <div class="card-footer"><span>{item.get('date','최근')}</span></div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>금융 리스크 뉴스 — {date_str}</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root {{
  --bg:#0a0e1a; --bg2:#111827; --bg3:#1a2235;
  --text:#e8edf5; --text2:#8a9ab5; --text3:#5a6a85;
  --accent:#3b82f6; --border:rgba(255,255,255,0.08);
  --sans:'Noto Sans KR',sans-serif; --mono:'IBM Plex Mono',monospace;
}}
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ background:var(--bg); color:var(--text); font-family:var(--sans); padding:2rem 1rem; }}
.container {{ max-width:720px; margin:0 auto; }}
.header {{ text-align:center; margin-bottom:2.5rem; padding-bottom:1.5rem; border-bottom:1px solid var(--border); }}
.header .date {{ font-family:var(--mono); font-size:12px; color:var(--accent); letter-spacing:2px; margin-bottom:8px; }}
.header h1 {{ font-size:24px; font-weight:700; margin-bottom:6px; }}
.header .sub {{ font-size:13px; color:var(--text3); }}
.card {{ background:var(--bg2); border:1px solid var(--border); border-radius:16px; overflow:hidden; margin-bottom:1.5rem; }}
.card-banner {{ height:5px; }}
.card-body {{ padding:1.5rem; }}
.tag {{ display:inline-block; font-size:11px; padding:3px 10px; border-radius:4px; font-family:var(--mono); margin-bottom:12px; font-weight:500; }}
.card-body h2 {{ font-size:17px; font-weight:700; margin-bottom:10px; line-height:1.5; }}
.headline {{ font-size:13px; color:var(--accent); font-weight:500; margin-bottom:12px; }}
.summary {{ font-size:14px; color:var(--text2); line-height:1.8; margin-bottom:12px; }}
.keypoints {{ padding-left:18px; margin-bottom:12px; }}
.keypoints li {{ font-size:13px; color:var(--text2); margin-bottom:5px; line-height:1.6; }}
.implication {{ background:var(--bg3); border-radius:8px; padding:0.75rem 1rem; font-size:13px; color:var(--text2); line-height:1.6; }}
.imp-label {{ display:block; font-size:11px; color:var(--text3); font-family:var(--mono); margin-bottom:4px; }}
.card-footer {{ padding:0.75rem 1.5rem; border-top:1px solid var(--border); font-size:11px; color:var(--text3); font-family:var(--mono); }}
.footer {{ text-align:center; margin-top:2rem; font-size:12px; color:var(--text3); font-family:var(--mono); }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="date">{date_str}</div>
    <h1>📊 금융 리스크 뉴스</h1>
    <div class="sub">Gemini AI 자동 수집 · 금융 리스크 · 규제 동향</div>
  </div>
  {cards_html}
  <div class="footer">Generated by Risk.AI · {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
</div>
</body>
</html>"""


# ─── HTML 저장 + 브라우저 자동 열기 ──────────────────
def save_and_open(html: str, date_str: str) -> str:
    output_dir = Path(config.OUTPUT_DIR)
    output_dir.mkdir(exist_ok=True)
    filepath = output_dir / f"report_{date_str}.html"
    filepath.write_text(html, encoding="utf-8")
    print(f"  💾 HTML 저장: {filepath}")

    webbrowser.open(filepath.resolve().as_uri())
    print(f"  🌐 브라우저 자동 실행!")

    return str(filepath)


# ─── 이메일 발송 ──────────────────────────────────────
def send_email(html: str, items: list, date_str: str):
    if not config.EMAIL_ENABLED:
        print("  📧 이메일 비활성화 상태")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📊 금융 리스크 뉴스 — {date_str} ({len(items)}건)"
    msg["From"] = config.EMAIL_SENDER
    msg["To"] = config.EMAIL_RECEIVER

    text_body = f"금융 리스크 뉴스 {date_str}\n\n"
    for i, item in enumerate(items, 1):
        text_body += f"{i}. [{item.get('level','')}] {item.get('title','')}\n"
        text_body += f"   {item.get('headline','')}\n\n"

    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    ctx = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as server:
            server.login(config.EMAIL_SENDER, config.EMAIL_PASSWORD)
            server.sendmail(config.EMAIL_SENDER, config.EMAIL_RECEIVER, msg.as_string())
        print(f"  📧 이메일 발송 완료 → {config.EMAIL_RECEIVER}")
    except Exception as e:
        print(f"  ⚠️ 이메일 발송 실패: {e}")


# ─── 메인 ─────────────────────────────────────────────
def run():
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    print(f"\n{'='*50}")
    print(f"  🚀 수집 시작 — {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")

    keywords = random.sample(config.KEYWORDS, min(config.COLLECT_COUNT, len(config.KEYWORDS)))

    print("\n[1/3] 뉴스 수집 중...")
    items = collect_news(keywords)

    if not items:
        print("  ❌ 수집된 뉴스 없음. 다시 시도해주세요.")
        return

    print(f"  ✅ {len(items)}건 수집 완료")

    print("\n[2/3] HTML 리포트 생성 중...")
    html = generate_html(items, date_str)
    filepath = save_and_open(html, date_str)

    print("\n[3/3] 이메일 발송 중...")
    send_email(html, items, date_str)

    print(f"\n{'='*50}")
    print(f"  🎉 완료! → {filepath}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    run()
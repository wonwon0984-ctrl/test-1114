"""
Pillow 카드뉴스 생성기

사용법:
    python card_news.py                    # 내장 예시 데이터로 생성
    python card_news.py content.json       # JSON 파일로 생성
    python card_news.py content.json -o out --size 1080x1350

JSON 형식:
{
  "theme": {"bg_top": "#1E3C72", "bg_bottom": "#2A5298", "accent": "#FFD166", "text": "#FFFFFF"},
  "brand": "@my_channel",
  "slides": [
    {"type": "cover", "title": "제목", "subtitle": "부제목"},
    {"type": "content", "title": "소제목", "body": "본문 내용", "image": "선택: 배경 이미지 경로"},
    {"type": "end", "title": "마무리 문구", "subtitle": "팔로우 해주세요"}
  ]
}
"""
import argparse
import json
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

# ---------------------------------------------------------------- 기본 설정
DEFAULT_THEME = {
    "bg_top": "#1E3C72",
    "bg_bottom": "#2A5298",
    "accent": "#FFD166",
    "text": "#FFFFFF",
    "sub_text": "#D9E2F2",
}

SAMPLE = {
    "brand": "@card_news",
    "slides": [
        {"type": "cover", "title": "아침 10분으로\n하루를 바꾸는 습관 3가지",
         "subtitle": "작은 루틴이 만드는 큰 변화"},
        {"type": "content", "title": "물 한 잔 마시기",
         "body": "자는 동안 몸은 수분을 잃습니다. 일어나자마자 물 한 잔을 마시면 신진대사가 깨어나고 머리가 맑아집니다."},
        {"type": "content", "title": "5분 스트레칭",
         "body": "굳은 근육을 가볍게 풀어주면 혈액순환이 좋아지고 하루 종일 몸이 가벼워집니다. 목, 어깨, 허리 위주로 천천히 움직여 보세요."},
        {"type": "content", "title": "오늘의 할 일 3개 적기",
         "body": "많을 필요 없습니다. 오늘 꼭 끝낼 일 세 가지만 적어두면 우선순위가 분명해지고 성취감도 커집니다."},
        {"type": "end", "title": "내일 아침,\n하나만 시작해 보세요",
         "subtitle": "도움이 되셨다면 저장하고 공유해 주세요"},
    ],
}

FONT_CANDIDATES = {
    "bold": [
        "C:/Windows/Fonts/malgunbd.ttf",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    ],
    "regular": [
        "C:/Windows/Fonts/malgun.ttf",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    ],
}


# ---------------------------------------------------------------- 유틸
def load_font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES[weight]:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    sys.exit(f"한글 폰트를 찾을 수 없습니다. FONT_CANDIDATES['{weight}']에 폰트 경로를 추가하세요.")


def gradient(size, top, bottom) -> Image.Image:
    """세로 그라디언트 배경."""
    mask = Image.linear_gradient("L").resize(size)
    return Image.composite(Image.new("RGB", size, bottom), Image.new("RGB", size, top), mask)


def image_background(path, size) -> Image.Image:
    """이미지를 꽉 차게 자르고 어둡게 덮어 글자가 잘 보이게 함."""
    img = ImageOps.fit(Image.open(path).convert("RGB"), size, Image.LANCZOS)
    overlay = Image.new("RGB", size, (0, 0, 0))
    return Image.blend(img, overlay, 0.55)


def wrap_text(draw, text, font, max_width) -> list[str]:
    """픽셀 폭 기준 줄바꿈. 단어 단위 우선, 너무 긴 단어는 글자 단위로 자름."""
    lines = []
    for paragraph in text.split("\n"):
        current = ""
        for word in paragraph.split(" "):
            candidate = f"{current} {word}".strip()
            if draw.textlength(candidate, font=font) <= max_width:
                current = candidate
                continue
            if current:
                lines.append(current)
            # 단어 하나가 한 줄보다 길면 글자 단위로 분할
            current = ""
            for ch in word:
                if draw.textlength(current + ch, font=font) <= max_width:
                    current += ch
                else:
                    lines.append(current)
                    current = ch
        lines.append(current)
    return lines


def draw_lines(draw, lines, font, x, y, fill, line_gap, align="left", width=0) -> int:
    """여러 줄을 그리고 마지막 y 좌표를 반환."""
    line_h = font.getbbox("가Ag")[3]
    for line in lines:
        lx = x
        if align == "center":
            lx = x + (width - draw.textlength(line, font=font)) / 2
        draw.text((lx, y), line, font=font, fill=fill)
        y += int(line_h * line_gap)
    return y


def block_height(lines, font, line_gap) -> int:
    line_h = font.getbbox("가Ag")[3]
    return int(line_h * line_gap) * len(lines)


# ---------------------------------------------------------------- 슬라이드 렌더링
def render_slide(slide, page_no, num, total, size, theme, brand) -> Image.Image:
    W, H = size
    s = W / 1080  # 1080 기준 스케일
    pad = int(90 * s)
    max_w = W - pad * 2

    if slide.get("image") and os.path.exists(slide["image"]):
        img = image_background(slide["image"], size)
    else:
        img = gradient(size, theme["bg_top"], theme["bg_bottom"])
    draw = ImageDraw.Draw(img)

    kind = slide.get("type", "content")
    title = slide.get("title", "")
    subtitle = slide.get("subtitle", "")
    body = slide.get("body", "")

    if kind in ("cover", "end"):
        # 가운데 정렬 레이아웃
        f_title = load_font("bold", int(84 * s))
        f_sub = load_font("regular", int(40 * s))
        t_lines = wrap_text(draw, title, f_title, max_w)
        s_lines = wrap_text(draw, subtitle, f_sub, max_w) if subtitle else []
        gap = int(50 * s)
        bar_h = int(8 * s)
        total_h = block_height(t_lines, f_title, 1.3) + gap + bar_h + (gap + block_height(s_lines, f_sub, 1.5) if s_lines else 0)
        y = (H - total_h) // 2
        y = draw_lines(draw, t_lines, f_title, pad, y, theme["text"], 1.3, "center", max_w)
        y += gap // 2
        bar_w = int(120 * s)
        draw.rectangle([(W - bar_w) // 2, y, (W + bar_w) // 2, y + bar_h], fill=theme["accent"])
        y += bar_h + gap
        if s_lines:
            draw_lines(draw, s_lines, f_sub, pad, y, theme["sub_text"], 1.5, "center", max_w)
    else:
        # 본문 레이아웃: 큰 번호 + 제목 + 본문
        f_num = load_font("bold", int(150 * s))
        f_title = load_font("bold", int(64 * s))
        f_body = load_font("regular", int(42 * s))
        y = int(150 * s)
        draw.text((pad, y), f"{num:02d}", font=f_num, fill=theme["accent"])
        y += int(200 * s)
        y = draw_lines(draw, wrap_text(draw, title, f_title, max_w), f_title, pad, y, theme["text"], 1.3)
        y += int(30 * s)
        draw.rectangle([pad, y, pad + int(80 * s), y + int(6 * s)], fill=theme["accent"])
        y += int(60 * s)
        draw_lines(draw, wrap_text(draw, body, f_body, max_w), f_body, pad, y, theme["sub_text"], 1.6)

    # 하단: 브랜드 + 페이지 번호
    f_small = load_font("regular", int(30 * s))
    by = H - int(90 * s)
    if brand:
        draw.text((pad, by), brand, font=f_small, fill=theme["sub_text"])
    page = f"{page_no} / {total}"
    draw.text((W - pad - draw.textlength(page, font=f_small), by), page, font=f_small, fill=theme["sub_text"])
    return img


# ---------------------------------------------------------------- 메인
def main():
    ap = argparse.ArgumentParser(description="Pillow 카드뉴스 생성기")
    ap.add_argument("json", nargs="?", help="슬라이드 내용 JSON 파일 (생략 시 예시 데이터)")
    ap.add_argument("-o", "--out", default="output", help="출력 폴더 (기본: output)")
    ap.add_argument("--size", default="1080x1080", help="이미지 크기 WxH (기본: 1080x1080, 세로형 1080x1350)")
    args = ap.parse_args()

    data = json.loads(Path(args.json).read_text(encoding="utf-8")) if args.json else SAMPLE
    theme = {**DEFAULT_THEME, **data.get("theme", {})}
    size = tuple(int(v) for v in args.size.lower().split("x"))
    slides = data["slides"]

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    # 본문 슬라이드 번호(01, 02...)는 content 타입만 카운트
    content_no = 0
    for i, slide in enumerate(slides):
        if slide.get("type", "content") == "content":
            content_no += 1
        img = render_slide(slide, i + 1, content_no, len(slides), size, theme, data.get("brand", ""))
        path = out / f"card_{i + 1:02d}.png"
        img.save(path)
        print(f"저장: {path}")


if __name__ == "__main__":
    main()

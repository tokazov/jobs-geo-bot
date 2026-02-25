"""
Instagram автопостинг — заготовка.
Требует INSTAGRAM_ACCESS_TOKEN и INSTAGRAM_ACCOUNT_ID в env.
"""

import os
import json
import logging
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

log = logging.getLogger(__name__)

INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID", "")


# --------------- Image generation ---------------

def _get_font(size: int) -> ImageFont.FreeTypeFont:
    """Try system fonts, fall back to default."""
    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/app/fonts/DejaVuSans-Bold.ttf",
    ]:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _wrap(text: str, draw: ImageDraw.ImageDraw, font, max_width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        cur = words[0]
        for w in words[1:]:
            test = cur + " " + w
            bbox = draw.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] <= max_width:
                cur = test
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def generate_post_image(data: dict, post_type: str) -> BytesIO:
    """
    Generate a 1080×1080 image for Instagram.
    post_type: 'resume' | 'job'
    data: collected form fields as dict.
    Returns BytesIO with PNG.
    """
    W, H = 1080, 1080
    bg_color = (18, 18, 30)
    accent = (0, 200, 120) if post_type == "job" else (80, 140, 255)

    img = Image.new("RGB", (W, H), bg_color)
    draw = ImageDraw.Draw(img)

    # accent bar
    draw.rectangle([(0, 0), (W, 8)], fill=accent)
    draw.rectangle([(0, H - 8), (W, H)], fill=accent)

    # header
    hdr_font = _get_font(52)
    small_font = _get_font(32)
    body_font = _get_font(30)

    # logo text
    draw.text((40, 30), "jobs.ge", fill=accent, font=hdr_font)

    # type label
    label = "🏢 ВАКАНСИЯ / VACANCY" if post_type == "job" else "📄 РЕЗЮМЕ / RESUME"
    draw.text((40, 100), label, fill=(255, 255, 255), font=small_font)

    # divider
    draw.line([(40, 150), (W - 40, 150)], fill=accent, width=2)

    # body
    y = 170
    margin = 50
    max_w = W - margin * 2

    for key, val in data.items():
        if y > H - 120:
            break
        line = f"{key}: {val}"
        wrapped = _wrap(line, draw, body_font, max_w)
        for wl in wrapped:
            if y > H - 80:
                break
            draw.text((margin, y), wl, fill=(220, 220, 220), font=body_font)
            y += 40

    # footer
    draw.text((40, H - 60), "t.me/jobs_geo_bot", fill=(150, 150, 150), font=small_font)

    buf = BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    return buf


# --------------- Instagram Graph API stubs ---------------

async def publish_post(image_url: str, caption: str) -> str | None:
    """
    Publish image post to Instagram via Graph API.
    Returns media_id on success, None on failure.
    TODO: implement when Instagram API token is available.
    """
    # Steps:
    # 1. POST /{ig-account-id}/media  { image_url, caption, access_token }
    # 2. POST /{ig-account-id}/media_publish { creation_id, access_token }
    log.warning("Instagram publish_post is a stub — not publishing.")
    return None


async def delete_post(post_id: str) -> bool:
    """
    Delete an Instagram post.
    TODO: implement when Instagram API token is available.
    """
    log.warning("Instagram delete_post is a stub — not deleting %s", post_id)
    return False


def generate_caption(data: dict, post_type: str, lang: str = "ru") -> str:
    """Generate Instagram caption with emojis and hashtags."""
    lines: list[str] = []
    if post_type == "job":
        lines.append("🏢 Вакансия / Vacancy\n")
        for k, v in data.items():
            lines.append(f"▪️ {k}: {v}")
        lines.append("\n📩 Подробнее: t.me/jobs_geo_bot")
        lines.append("\n#работа #вакансия #Грузия #Тбилиси #Батуми #job #Georgia #hiring")
    else:
        lines.append("📄 Резюме / Resume\n")
        for k, v in data.items():
            lines.append(f"▪️ {k}: {v}")
        lines.append("\n📩 Подробнее: t.me/jobs_geo_bot")
        lines.append("\n#резюме #ищуработу #Грузия #Тбилиси #Батуми #resume #Georgia #lookingforjob")
    return "\n".join(lines)

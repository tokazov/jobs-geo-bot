"""
Instagram автопостинг через Instagram Graph API.
Requires INSTAGRAM_ACCESS_TOKEN (page token) and INSTAGRAM_ACCOUNT_ID in env.
"""

import os
import json
import logging
import aiohttp
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

log = logging.getLogger(__name__)

INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID", "")
GRAPH_API = "https://graph.facebook.com/v21.0"


# --------------- Image generation ---------------

def _get_font(size: int) -> ImageFont.FreeTypeFont:
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
    W, H = 1080, 1080
    bg_color = (255, 255, 255)
    blue = (0, 82, 180)
    red = (210, 45, 45)
    green = (0, 140, 70)
    gray = (120, 120, 120)
    text_color = (40, 40, 40)
    title_color = red if post_type == "job" else green

    img = Image.new("RGB", (W, H), bg_color)
    draw = ImageDraw.Draw(img)

    draw.rectangle([(0, 0), (W, 6)], fill=blue)

    logo_font = _get_font(58)
    sub_font = _get_font(28)
    title_font = _get_font(48)
    body_font = _get_font(32)
    footer_font = _get_font(26)

    logo_text = "JOBS.GE"
    logo_bbox = draw.textbbox((0, 0), logo_text, font=logo_font)
    logo_w = logo_bbox[2] - logo_bbox[0]
    draw.text(((W - logo_w) // 2, 40), logo_text, fill=blue, font=logo_font)

    sub_text = "Georgia"
    sub_bbox = draw.textbbox((0, 0), sub_text, font=sub_font)
    sub_w = sub_bbox[2] - sub_bbox[0]
    draw.text(((W - sub_w) // 2, 108), sub_text, fill=gray, font=sub_font)

    title_text = "ვაკანსია" if post_type == "job" else "რეზიუმე"
    title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
    title_w = title_bbox[2] - title_bbox[0]
    draw.text(((W - title_w) // 2, 165), title_text, fill=title_color, font=title_font)

    draw.line([(80, 235), (W - 80, 235)], fill=(220, 220, 220), width=2)

    y = 260
    margin = 80
    max_w = W - margin * 2

    for key, val in data.items():
        if y > H - 150:
            break
        line = f"{val}"
        wrapped = _wrap(line, draw, body_font, max_w)
        for wl in wrapped:
            if y > H - 120:
                break
            line_bbox = draw.textbbox((0, 0), wl, font=body_font)
            line_w = line_bbox[2] - line_bbox[0]
            draw.text(((W - line_w) // 2, y), wl, fill=text_color, font=body_font)
            y += 44
        y += 10

    draw.line([(80, H - 130), (W - 80, H - 130)], fill=(220, 220, 220), width=1)

    footer1 = "t.me/jobs_geo_bot"
    f1_bbox = draw.textbbox((0, 0), footer1, font=footer_font)
    f1_w = f1_bbox[2] - f1_bbox[0]
    draw.text(((W - f1_w) // 2, H - 110), footer1, fill=blue, font=footer_font)

    footer2 = "სამუშაო და მუშები 🇬🇪"
    f2_bbox = draw.textbbox((0, 0), footer2, font=footer_font)
    f2_w = f2_bbox[2] - f2_bbox[0]
    draw.text(((W - f2_w) // 2, H - 70), footer2, fill=gray, font=footer_font)

    draw.rectangle([(0, H - 6), (W, H)], fill=blue)

    buf = BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    return buf


# --------------- Image hosting via Telegram ---------------

async def upload_image_to_telegram(bot, image_bytes: BytesIO, chat_id: str) -> str | None:
    """
    Upload image to Telegram (send to admin chat + delete) to get a public URL.
    Instagram API needs a publicly accessible image_url.
    Returns file URL or None.
    """
    from aiogram.types import BufferedInputFile
    try:
        input_file = BufferedInputFile(image_bytes.getvalue(), filename="post.png")
        msg = await bot.send_photo(chat_id=chat_id, photo=input_file, caption="📸 Uploading to Instagram...")
        # Get file URL
        file_id = msg.photo[-1].file_id
        file = await bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"
        # Delete the temp message
        await bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
        return file_url
    except Exception as e:
        log.error("Failed to upload image to Telegram: %s", e)
        return None


# --------------- Instagram Graph API ---------------

async def publish_post(image_url: str, caption: str) -> str | None:
    """
    Publish image post to Instagram via Graph API.
    Returns media_id on success, None on failure.
    
    Steps:
    1. Create media container with image_url + caption
    2. Publish the container
    """
    if not INSTAGRAM_ACCESS_TOKEN or not INSTAGRAM_ACCOUNT_ID:
        log.warning("Instagram credentials not set — skipping publish")
        return None

    try:
        async with aiohttp.ClientSession() as session:
            # Step 1: Create media container
            create_url = f"{GRAPH_API}/{INSTAGRAM_ACCOUNT_ID}/media"
            create_params = {
                "image_url": image_url,
                "caption": caption,
                "access_token": INSTAGRAM_ACCESS_TOKEN,
            }
            async with session.post(create_url, data=create_params) as resp:
                result = await resp.json()
                if "id" not in result:
                    log.error("Instagram create media failed: %s", result)
                    return None
                creation_id = result["id"]
                log.info("Instagram media container created: %s", creation_id)

            # Step 2: Publish
            publish_url = f"{GRAPH_API}/{INSTAGRAM_ACCOUNT_ID}/media_publish"
            publish_params = {
                "creation_id": creation_id,
                "access_token": INSTAGRAM_ACCESS_TOKEN,
            }
            async with session.post(publish_url, data=publish_params) as resp:
                result = await resp.json()
                if "id" not in result:
                    log.error("Instagram publish failed: %s", result)
                    return None
                media_id = result["id"]
                log.info("Instagram post published! media_id=%s", media_id)
                return media_id

    except Exception as e:
        log.error("Instagram publish error: %s", e)
        return None


async def delete_post(post_id: str) -> bool:
    """Delete an Instagram post."""
    if not INSTAGRAM_ACCESS_TOKEN:
        log.warning("Instagram credentials not set — skipping delete")
        return False

    try:
        async with aiohttp.ClientSession() as session:
            url = f"{GRAPH_API}/{post_id}"
            params = {"access_token": INSTAGRAM_ACCESS_TOKEN}
            async with session.delete(url, params=params) as resp:
                result = await resp.json()
                if result.get("success"):
                    log.info("Instagram post %s deleted", post_id)
                    return True
                else:
                    log.error("Instagram delete failed: %s", result)
                    return False
    except Exception as e:
        log.error("Instagram delete error: %s", e)
        return False


def generate_caption(data: dict, post_type: str, lang: str = "ge") -> str:
    lines: list[str] = []
    if post_type == "job":
        lines.append("🏢 ვაკანსია / Vacancy\n")
        for k, v in data.items():
            lines.append(f"▪️ {k}: {v}")
        lines.append("\n📩 t.me/jobs_geo_bot")
        lines.append("\n#სამუშაო #ვაკანსია #საქართველო #თბილისი #ბათუმი #დასაქმება #job #Georgia #hiring #jobsge")
    else:
        lines.append("📄 რეზიუმე / Resume\n")
        for k, v in data.items():
            lines.append(f"▪️ {k}: {v}")
        lines.append("\n📩 t.me/jobs_geo_bot")
        lines.append("\n#რეზიუმე #სამუშაო #საქართველო #თბილისი #ბათუმი #დასაქმება #resume #Georgia #lookingforjob #jobsge")
    return "\n".join(lines)

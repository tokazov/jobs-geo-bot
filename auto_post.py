"""
Auto-post rotation for Jobs.ge Instagram + Facebook.
Run via cron every 8 hours.
Picks next post from rotation, publishes to both platforms.
"""
import json
import os
import sys
import requests

IG_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
IG_ID = os.getenv("INSTAGRAM_ACCOUNT_ID", "17841409029708884")
FB_TOKEN = os.getenv("FB_PAGE_TOKEN", "")
FB_PAGE = "102448604580304"
GRAPH = "https://graph.facebook.com/v21.0"
STATE_FILE = os.path.join(os.path.dirname(__file__), "data", "rotation_state.json")

POSTS = [
    {
        "image": "https://files.catbox.moe/ykfmv2.png",
        "caption": "📢 დამსაქმებლებისთვის!\n\nJOBS.GE — განათავსე ვაკანსია რამდენიმე წუთში!\n\n✅ 12,000+ მიმდევარი ნახავს\n✅ ავტო-პოსტი Instagram-ზე\n✅ მიიღე განაცხადები პირდაპირ\n🔥 ხელმისაწვდომი ფასი!\n\n⚡ დაიწყე → t.me/jobs_geo_bot\n\n#ვაკანსია #დასაქმება #საქართველო #თბილისი #ბათუმი #hiring #jobs #Georgia #jobsge",
    },
    {
        "image": "https://files.catbox.moe/vnexi1.png",
        "caption": "📄 სამუშაოს ეძებ?\n\nJOBS.GE — განათავსე რეზიუმე და მოხვდი დამსაქმებლების თვალში!\n\n✅ ათასობით დამსაქმებელი ნახავს\n✅ გამოქვეყნდება Instagram-ზე\n✅ სწრაფად და მარტივად\n💪 იპოვე ოცნების სამუშაო!\n\n⚡ დაიწყე → t.me/jobs_geo_bot\n\n#რეზიუმე #სამუშაო #საქართველო #თბილისი #ბათუმი #დასაქმება #job #Georgia #jobsge",
    },
    {
        "image": "https://files.catbox.moe/n6pd7z.png",
        "caption": "⚡ როგორ მუშაობს JOBS.GE?\n\n1️⃣ გახსენი ბოტი → t.me/jobs_geo_bot\n2️⃣ აირჩიე: ვაკანსია ან რეზიუმე\n3️⃣ შეავსე ინფორმაცია\n4️⃣ გადაიხადე\n5️⃣ გამოქვეყნდება Instagram-ზე!\n\n🎉 მარტივი და სწრაფი!\n\n#სამუშაო #ვაკანსია #რეზიუმე #საქართველო #Georgia #jobs #jobsge",
    },
    {
        "image": "https://files.catbox.moe/ifs0sv.png",
        "caption": "📢 Hiring in Georgia?\n\nJOBS.GE — post a vacancy in minutes!\n\n✅ Reach 12,000+ followers\n✅ Auto-publish to Instagram\n✅ Get applications directly\n🔥 Affordable price!\n\n⚡ Start → t.me/jobs_geo_bot\n\n#vacancy #hiring #Georgia #Tbilisi #Batumi #jobs #jobsge #work #career",
    },
    {
        "image": "https://files.catbox.moe/dwdof6.png",
        "caption": "📄 Looking for a job in Georgia?\n\nJOBS.GE — post your resume and get noticed!\n\n✅ Thousands of employers will see\n✅ Published on Instagram (12,000+ followers)\n✅ Fast and easy\n💪 Find your dream job!\n\n⚡ Start → t.me/jobs_geo_bot\n\n#resume #job #Georgia #Tbilisi #Batumi #hiring #jobsge #career",
    },
    {
        "image": "https://files.catbox.moe/gzow49.png",
        "caption": "🇬🇪 რატომ JOBS.GE?\n\n📸 12,000+ Instagram მიმდევარი\n⚡ ავტომატური გამოქვეყნება\n🤖 მარტივი Telegram ბოტი\n💰 ხელმისაწვდომი ფასი\n⏰ 48 საათი აქტიური პოსტი\n🔒 უსაფრთხო გადახდა\n\n👉 t.me/jobs_geo_bot\n\n#სამუშაო #რეზიუმე #ვაკანსია #საქართველო #Georgia #jobs #jobsge",
    },
    # Photo posts with people
    {
        "image": "https://files.catbox.moe/e023tl.png",
        "caption": "📢 ეძებ თანამშრომელს?\n\nJOBS.GE — განათავსე ვაკანსია და იპოვე საუკეთესო კანდიდატი!\n\n✅ 12,000+ მიმდევარი\n✅ ავტო-პოსტი Instagram-ზე\n✅ სწრაფი და მარტივი\n\n👉 t.me/jobs_geo_bot\n\n#ვაკანსია #დასაქმება #საქართველო #თბილისი #hiring #jobs #Georgia #jobsge",
    },
    {
        "image": "https://files.catbox.moe/52b39m.png",
        "caption": "📄 ეძებ სამუშაოს?\n\nJOBS.GE — განათავსე რეზიუმე და მოხვდი დამსაქმებლების თვალში!\n\n✅ ათასობით დამსაქმებელი\n✅ გამოქვეყნდება Instagram-ზე\n✅ სწრაფად და მარტივად\n\n👉 t.me/jobs_geo_bot\n\n#რეზიუმე #სამუშაო #საქართველო #თბილისი #job #Georgia #jobsge",
    },
    {
        "image": "https://files.catbox.moe/qosoix.png",
        "caption": "🤝 იპოვე იდეალური კანდიდატი!\n\nJOBS.GE აკავშირებს დამსაქმებლებს და სამუშაოს მაძიებლებს.\n\n📢 ვაკანსია ან 📄 რეზიუმე — რამდენიმე წუთში!\n\n👉 t.me/jobs_geo_bot\n\n#სამუშაო #ვაკანსია #რეზიუმე #საქართველო #Georgia #jobs #jobsge #hiring",
    },
    {
        "image": "https://files.catbox.moe/9knt10.png",
        "caption": "💼 სამუშაო საქართველოში — სწრაფად და მარტივად!\n\nJOBS.GE — თანამედროვე გზა სამუშაოს საპოვნელად.\n\n🤖 Telegram ბოტი\n📸 Instagram 12,000+\n⚡ რამდენიმე წუთში\n\n👉 t.me/jobs_geo_bot\n\n#დასაქმება #სამუშაო #საქართველო #თბილისი #ბათუმი #jobs #Georgia #jobsge",
    },
    {
        "image": "https://files.catbox.moe/jr8dpy.png",
        "caption": "🎉 შენი გუნდი აქ არის!\n\nJOBS.GE-ზე იპოვი საუკეთესო თანამშრომლებს.\n\n📢 განათავსე ვაკანსია\n📄 მიიღე განაცხადები\n🔥 12,000+ მიმდევარი\n\n👉 t.me/jobs_geo_bot\n\n#ვაკანსია #გუნდი #დასაქმება #საქართველო #hiring #team #Georgia #jobsge",
    },
    {
        "image": "https://files.catbox.moe/utopgm.png",
        "caption": "⚡ დაიწყე ახლავე!\n\nJOBS.GE — ვაკანსიები და რეზიუმეები საქართველოში.\n\n✅ მარტივი\n✅ სწრაფი\n✅ ხელმისაწვდომი\n\n👉 t.me/jobs_geo_bot\n\n#სამუშაო #ვაკანსია #რეზიუმე #საქართველო #Georgia #jobs #jobsge #career",
    },
    # English posts with people (v6 — dark overlay + emoji PNG)
    {
        "image": "https://files.catbox.moe/0l1aq1.png",
        "caption": "📢 Looking for employees?\n\nJOBS.GE — post a vacancy in minutes!\n\n✅ Reach 12,000+ followers\n✅ Auto-publish to Instagram\n✅ Get applications directly\n\n⚡ Start → t.me/jobs_geo_bot\n\n#vacancy #hiring #Georgia #Tbilisi #Batumi #jobs #jobsge #work #career",
    },
    {
        "image": "https://files.catbox.moe/zs57cz.png",
        "caption": "📄 Looking for a job in Georgia?\n\nJOBS.GE — post your resume and get noticed!\n\n✅ Thousands of employers will see\n✅ Published on Instagram (12,000+ followers)\n✅ Fast and easy\n\n⚡ Start → t.me/jobs_geo_bot\n\n#resume #job #Georgia #Tbilisi #Batumi #hiring #jobsge #career",
    },
    {
        "image": "https://files.catbox.moe/7j0vvr.png",
        "caption": "🤝 Find the perfect candidate!\n\nJOBS.GE connects employers and job seekers.\n\n📢 Vacancy or 📄 Resume — in just a few minutes!\n\n👉 t.me/jobs_geo_bot\n\n#hiring #vacancy #resume #Georgia #jobs #jobsge #Tbilisi #Batumi",
    },
    {
        "image": "https://files.catbox.moe/4qhokc.png",
        "caption": "💼 Jobs in Georgia — Quick & Easy!\n\nJOBS.GE — the modern way to find work.\n\n🤖 Telegram bot\n📸 Instagram 12,000+\n⚡ Just a few minutes\n\n👉 t.me/jobs_geo_bot\n\n#job #Georgia #Tbilisi #Batumi #hiring #career #jobsge",
    },
    {
        "image": "https://files.catbox.moe/byq4jp.png",
        "caption": "🎉 Your team is here!\n\nFind the best employees on JOBS.GE.\n\n📢 Post a vacancy\n📄 Get applications\n🔥 12,000+ followers\n\n👉 t.me/jobs_geo_bot\n\n#hiring #team #vacancy #Georgia #Tbilisi #jobs #jobsge",
    },
    {
        "image": "https://files.catbox.moe/su1vwc.png",
        "caption": "⚡ Start right now!\n\nJOBS.GE — vacancies and resumes in Georgia.\n\n✅ Simple\n✅ Fast\n✅ Affordable\n\n👉 t.me/jobs_geo_bot\n\n#job #vacancy #resume #Georgia #Tbilisi #Batumi #hiring #jobsge #career",
    },
]


def get_next_index():
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
        idx = state.get("next_index", 0)
    except (FileNotFoundError, json.JSONDecodeError):
        idx = 0
    return idx % len(POSTS)


def save_index(idx):
    with open(STATE_FILE, "w") as f:
        json.dump({"next_index": (idx + 1) % len(POSTS)}, f)


def post_instagram(image_url, caption):
    if not IG_TOKEN:
        print("SKIP Instagram: no token")
        return None
    # Create container
    r = requests.post(f"{GRAPH}/{IG_ID}/media", data={
        "image_url": image_url,
        "caption": caption,
        "access_token": IG_TOKEN,
    })
    cid = r.json().get("id")
    if not cid:
        print(f"IG container error: {r.json()}")
        return None
    # Publish
    import time; time.sleep(3)
    r = requests.post(f"{GRAPH}/{IG_ID}/media_publish", data={
        "creation_id": cid,
        "access_token": IG_TOKEN,
    })
    mid = r.json().get("id")
    print(f"IG published: {mid}")
    return mid


def post_facebook(image_url, caption):
    if not FB_TOKEN:
        print("SKIP Facebook: no token")
        return None
    r = requests.post(f"{GRAPH}/{FB_PAGE}/photos", data={
        "url": image_url,
        "message": caption,
        "access_token": FB_TOKEN,
    })
    pid = r.json().get("post_id")
    print(f"FB published: {pid}")
    return pid


def main():
    idx = get_next_index()
    post = POSTS[idx]
    print(f"Posting #{idx+1}/{len(POSTS)}: {post['image']}")

    post_instagram(post["image"], post["caption"])
    post_facebook(post["image"], post["caption"])

    save_index(idx)
    print("Done!")


if __name__ == "__main__":
    main()

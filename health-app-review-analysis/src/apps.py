"""
The 15 health / nutrition apps in this study (India Play Store, lang=en, country=in).

Cap per app keeps the four giants (Healthify, cult.fit, MyFitnessPal, Samsung Health)
from drowning out the rest. All IDs verified with google-play-scraper on 2026-10-02.
"""

APPS = [
    # app_id, short name, segment, per-app cap
    ("com.healthifyme.basic",             "HealthifyMe",   "india_coach",   8000),
    ("fit.cure.android",                  "cult.fit",      "india_fitness", 8000),
    ("com.squats.fittr",                  "FITTR",         "india_coach",   8000),
    ("com.fitelo.android",                "Fitelo",        "india_coach",   8000),
    ("com.myfitnesspal.android",          "MyFitnessPal",  "global_tracker", 8000),
    ("com.fatsecret.android",             "FatSecret",     "global_tracker", 8000),
    ("com.fitnow.loseit",                 "Lose It!",      "global_tracker", 8000),
    ("com.fourtechnologies.mynetdiary.ad","MyNetDiary",    "global_tracker", 8000),
    ("com.sillens.shapeupclub",           "Lifesum",       "global_tracker", 8000),
    ("com.cronometer.android.gold",       "Cronometer",    "global_tracker", 8000),
    ("com.yazio.android",                 "YAZIO",         "global_tracker", 8000),
    ("com.wsl.noom",                      "Noom",          "global_coach",  8000),
    ("com.viraldevelopment.calai",        "Cal AI",        "ai_photo",      8000),
    ("com.bodyfast",                      "BodyFast",      "fasting",       8000),
    ("com.sec.android.app.shealth",       "Samsung Health","platform",      8000),
]

APP_NAMES = {a[0]: a[1] for a in APPS}
APP_SEGMENTS = {a[0]: a[2] for a in APPS}

# Complaint taxonomy: health & nutrition apps (India Play Store)

One primary label per review. A review that complains about two things gets the one the
reviewer leads with (first sentence wins). Praise with no complaint is `no_complaint`.

| Code | Label | Covers | Does not cover |
|---|---|---|---|
| `billing` | Subscription & billing | Unwanted / auto-renewed charges, refund refused, trial converted silently, price hike, payment failed but money deducted, cannot cancel | "Too expensive" with no transaction problem -> `paywall` |
| `paywall` | Paywall & ads | Feature that was free is now paid, too many ads, nag screens, constant upsell pop-ups, "everything is premium" | Actual money taken -> `billing` |
| `login` | Login, account & sync | OTP not received, cannot sign in, account locked, data lost after reinstall or phone change, cross-device sync broken | Wearable sync -> `device_sync` |
| `crash` | Crashes & bugs | App crashes, freezes, blank screen, buttons do nothing, feature broken after update | Slow but working -> `performance` |
| `performance` | Performance & battery | Slow, laggy, long loading, battery drain, storage hog, data usage | Crash -> `crash` |
| `food_db` | Food database & logging accuracy | Indian dishes missing, wrong calories / macros, barcode scan fails, portion sizes wrong, AI photo recognition wrong, duplicate entries | Fitness tracking numbers -> `tracking` |
| `tracking` | Activity tracking & measurement | Step count wrong, workout not recorded, weight / sleep / heart-rate data wrong, GPS issues | Wearable pairing -> `device_sync` |
| `device_sync` | Wearable & third-party sync | Google Fit / Health Connect / Fitbit / smartwatch pairing or sync broken, data not flowing between apps | Account sync across phones -> `login` |
| `coach_support` | Coach & customer support | Human coach unresponsive or generic, support tickets ignored, chatbot loops, no phone support, refund request unanswered (the service failure, not the money) | Money taken -> `billing` |
| `spam` | Spam & notifications | Marketing calls, WhatsApp spam, excessive push notifications, cannot turn notifications off | Upsell inside app -> `paywall` |
| `ux` | UX & navigation | Confusing layout, too many steps to log, cluttered, redesign made it worse, dark mode / font, accessibility | Bugs -> `crash` |
| `content_quality` | Plan & content quality | Diet plan generic or culturally wrong, unsafe advice, workouts too hard / easy, outdated content, AI coach gives nonsense | Database numbers -> `food_db` |
| `privacy` | Privacy & permissions | Excessive permissions, data selling worry, cannot delete account / data, location tracking | Spam calls -> `spam` |
| `localisation` | Language, units & India fit | No Hindi / regional language, imperial units only, pricing in dollars, features missing in India, India-specific foods (overlaps `food_db`: use `food_db` if the complaint is "food missing", `localisation` if "app not made for India") | |
| `other_complaint` | Other complaint | Anything negative that fits nowhere above | |
| `no_complaint` | No complaint | Praise, neutral, feature request without a complaint, unreadable / empty | |

Secondary fields captured alongside the label:

- `is_complaint` (bool): any label except `no_complaint`.
- `mentions_update` (bool): reviewer ties the problem to a recent update or version.
- `severity` (1-3): 1 = annoyance, 2 = feature unusable, 3 = money lost / data lost / safety.

## Why this taxonomy

- Categories are mutually exclusive on the *root cause* the reviewer names, which is what a
  PM can act on. "App is useless" is not a category; "food database wrong" is.
- `billing` and `paywall` are split because they route to different teams (payments vs pricing).
- `food_db` exists as its own bucket because in a nutrition app it is the product; for a pure
  fitness app it will be near zero, which is itself a finding.
- `localisation` is kept separate from `food_db` so that "global app, Indian user" friction can
  be measured across the global-vs-Indian app split.

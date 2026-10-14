#!/usr/bin/env python3
import json
import os
import sys

# LinuxToys languages. English is normally already present in the descriptions file.
LANGUAGES = (
    "am", "ar", "az", "bg", "bn", "bs", "cs", "da", "de", "el", "es", "et",
    "fa", "fi", "fr", "ga", "he", "hi", "hr", "hu", "hy", "id", "is", "it",
    "ja", "ka", "km", "ko", "lo", "lt", "lv", "mn", "ms", "my", "nb", "ne",
    "nl", "pl", "pt", "ro", "ru", "sk", "sl", "sq", "sr", "sv", "sw", "ta",
    "tg", "th", "tl", "tr", "uk", "ur", "uz", "vi", "zh",
)

# Fill this dictionary in the translation step.
#
# The key is the description tag from the target descriptions.json and each value is
# a language -> translated short-description mapping, following the same layout used
# by the old translate_json.py helper.
#
# Example:
# translations = {
#     "vkvolt_desc": {
#         "am": "...",
#         "ar": "...",
#         ...
#         "pt": "Painel de controle para jogos Vulkan no Linux, uma alternativa ao AMD Adrenalin e NVIDIA Settings para Linux.",
#         ...
#         "zh": "...",
#     },
# }
translations = {
    "epic_desc": {
        "am": "በvibe coding የተሰራው አዲሱ የEpic Games Launcher፣ እጅግ ፈጣን እና ምላሽ ሰጪ ነው።",
        "ar": "مشغّل Epic Games الجديد المطوّر بأسلوب vibe coding، أسرع بكثير وأكثر استجابة.",
        "az": "Vibe coding ilə hazırlanmış, daha sürətli və çevik yeni Epic Games Launcher.",
        "bg": "Новият Epic Games Launcher, създаден с vibe coding, е много по-бърз и отзивчив.",
        "bn": "ভাইব কোডিং দিয়ে তৈরি নতুন Epic Games Launcher, যা অনেক দ্রুত এবং আরও প্রতিক্রিয়াশীল।",
        "bs": "Novi Epic Games Launcher, napravljen uz vibe coding, mnogo je brži i odzivniji.",
        "cs": "Nový Epic Games Launcher vytvořený pomocí vibe codingu je mnohem rychlejší a svižnější.",
        "da": "Den nye Epic Games Launcher, skabt med vibe coding, er meget hurtigere og mere responsiv.",
        "de": "Der neue, mit Vibe Coding entwickelte Epic Games Launcher ist deutlich schneller und reaktionsfreudiger.",
        "el": "Ο νέος Epic Games Launcher, φτιαγμένος με vibe coding, είναι πολύ πιο γρήγορος και άμεσος.",
        "es": "El nuevo Epic Games Launcher, creado con vibe coding, es mucho más rápido y ágil.",
        "et": "Uus vibe coding’u abil loodud Epic Games Launcher on palju kiirem ja reageerib sujuvamalt.",
        "fa": "لانچر جدید Epic Games که با vibe coding ساخته شده، بسیار سریع‌تر و پاسخ‌گوتر است.",
        "fi": "Uusi vibe codingilla tehty Epic Games Launcher on paljon nopeampi ja responsiivisempi.",
        "fr": "Le nouveau lanceur Epic Games, créé en vibe coding, est bien plus rapide et réactif.",
        "ga": "Tá an Epic Games Launcher nua, cruthaithe le vibe coding, i bhfad níos tapúla agus níos freagrúla.",
        "he": "משגר Epic Games החדש, שנוצר באמצעות vibe coding, מהיר ומגיב הרבה יותר.",
        "hi": "वाइब कोडिंग से बना नया Epic Games Launcher, जो कहीं ज़्यादा तेज़ और प्रतिक्रियाशील है।",
        "hr": "Novi Epic Games Launcher, izrađen uz vibe coding, mnogo je brži i odzivniji.",
        "hu": "Az új, vibe codinggal készült Epic Games Launcher sokkal gyorsabb és reszponzívabb.",
        "hy": "Vibe coding-ով ստեղծված նոր Epic Games Launcher-ը շատ ավելի արագ է և արձագանքող։",
        "id": "Epic Games Launcher baru yang dibuat dengan vibe coding, jauh lebih cepat dan responsif.",
        "is": "Nýi Epic Games Launcher, búinn til með vibe coding, er mun hraðari og viðbragðsbetri.",
        "it": "Il nuovo Epic Games Launcher, creato con il vibe coding, è molto più veloce e reattivo.",
        "ja": "バイブコーディングで作られた新しいEpic Games Launcher。従来よりずっと高速で、反応も軽快です。",
        "ka": "Vibe coding-ით შექმნილი ახალი Epic Games Launcher გაცილებით სწრაფი და რეაგირებადია.",
        "km": "Epic Games Launcher ថ្មីដែលបង្កើតដោយ vibe coding មានល្បឿនលឿនជាងមុន និងឆ្លើយតបរហ័សជាងមុន។",
        "ko": "바이브 코딩으로 만든 새로운 Epic Games Launcher로, 훨씬 빠르고 반응성이 뛰어납니다.",
        "lo": "Epic Games Launcher ໃໝ່ທີ່ສ້າງດ້ວຍ vibe coding ໄວຂຶ້ນຫຼາຍ ແລະຕອບສະໜອງໄດ້ດີຂຶ້ນ.",
        "lt": "Naujoji „Epic Games Launcher“ programa, sukurta naudojant vibe coding, yra daug greitesnė ir jautresnė.",
        "lv": "Jaunais Epic Games Launcher, kas izveidots ar vibe coding, ir daudz ātrāks un atsaucīgāks.",
        "mn": "Vibe coding ашиглан бүтээсэн шинэ Epic Games Launcher нь хавьгүй хурдан, илүү шуурхай ажиллагаатай.",
        "ms": "Epic Games Launcher baharu yang dibina menggunakan vibe coding, jauh lebih pantas dan responsif.",
        "my": "Vibe coding ဖြင့် ဖန်တီးထားသော Epic Games Launcher အသစ်သည် ပိုမိုမြန်ဆန်ပြီး တုံ့ပြန်မှုလည်း ပိုကောင်းပါသည်။",
        "nb": "Den nye Epic Games Launcher, laget med vibe coding, er mye raskere og mer responsiv.",
        "ne": "भाइब कोडिङबाट बनाइएको नयाँ Epic Games Launcher, जुन धेरै छिटो र प्रतिक्रियाशील छ।",
        "nl": "De nieuwe Epic Games Launcher, gemaakt met vibe coding, is veel sneller en reageert vlotter.",
        "pl": "Nowy Epic Games Launcher, stworzony metodą vibe coding, jest znacznie szybszy i bardziej responsywny.",
        "pt": "O novo Launcher da Epic Games, criado com vibe coding, muito mais rápido e responsivo.",
        "ro": "Noul Epic Games Launcher, creat prin vibe coding, este mult mai rapid și mai receptiv.",
        "ru": "Новый Epic Games Launcher, созданный с помощью вайб-кодинга, стал гораздо быстрее и отзывчивее.",
        "sk": "Nový Epic Games Launcher vytvorený pomocou vibe codingu je oveľa rýchlejší a pohotovejší.",
        "sl": "Novi Epic Games Launcher, ustvarjen z vibe codingom, je veliko hitrejši in odzivnejši.",
        "sq": "Epic Games Launcher i ri, i krijuar me vibe coding, është shumë më i shpejtë dhe reagon më mirë.",
        "sr": "Нови Epic Games Launcher, направљен уз vibe coding, много је бржи и одзивнији.",
        "sv": "Den nya Epic Games Launcher, skapad med vibe coding, är mycket snabbare och mer responsiv.",
        "sw": "Epic Games Launcher mpya iliyoundwa kwa vibe coding, yenye kasi zaidi na mwitikio bora zaidi.",
        "ta": "வைப் கோடிங் மூலம் உருவாக்கப்பட்ட புதிய Epic Games Launcher, மிகவும் வேகமானதும் சிறப்பாகப் பதிலளிப்பதுமாக உள்ளது.",
        "tg": "Epic Games Launcher-и нав, ки бо vibe coding сохта шудааст, хеле тезтар ва ҷавобгӯтар аст.",
        "th": "Epic Games Launcher ใหม่ที่สร้างด้วย vibe coding เร็วขึ้นมากและตอบสนองได้ดียิ่งขึ้น",
        "tl": "Ang bagong Epic Games Launcher na ginawa gamit ang vibe coding, mas mabilis at mas responsive.",
        "tr": "Vibe coding ile geliştirilen yeni Epic Games Launcher, çok daha hızlı ve duyarlı.",
        "uk": "Новий Epic Games Launcher, створений за допомогою вайбкодингу, значно швидший і чутливіший.",
        "ur": "وائب کوڈنگ سے بنایا گیا نیا Epic Games Launcher، جو بہت زیادہ تیز اور بہتر ردعمل والا ہے۔",
        "uz": "Vibe coding yordamida yaratilgan yangi Epic Games Launcher ancha tezkor va sezgir.",
        "vi": "Epic Games Launcher mới được tạo bằng vibe coding, nhanh hơn và phản hồi nhạy hơn nhiều.",
        "zh": "全新 Epic Games Launcher，采用氛围编程（vibe coding）打造，速度更快、响应更灵敏。"
    }
}


def resolve_target(argument: str) -> str:
    """Resolve either a direct path or a path relative to ../p3/scripts/lists."""
    if os.path.isfile(argument):
        return os.path.abspath(argument)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    lists_dir = os.path.normpath(os.path.join(script_dir, "..", "p3", "scripts", "lists"))
    candidate = os.path.join(lists_dir, argument)

    if os.path.isfile(candidate):
        return candidate

    raise FileNotFoundError(
        f"Could not find '{argument}' directly or under '{lists_dir}'."
    )


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: python3 {os.path.basename(sys.argv[0])} <path/to/descriptions.json>")
        print(f"Example: python3 {os.path.basename(sys.argv[0])} volt/descriptions.json")
        return 2

    try:
        target = resolve_target(sys.argv[1])
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    try:
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Error reading {target}: {exc}", file=sys.stderr)
        return 1

    description_tag = data.get("description_tag")
    if not isinstance(description_tag, str) or not description_tag:
        print(f"Error: {target} has no valid 'description_tag'.", file=sys.stderr)
        return 1

    lang_translations = translations.get(description_tag)
    if lang_translations is None:
        print(
            f"Error: no translations were provided for '{description_tag}' in translations.",
            file=sys.stderr,
        )
        return 1

    unknown = sorted(set(lang_translations) - set(LANGUAGES) - {"en"})
    if unknown:
        print(
            "Error: unsupported language code(s): " + ", ".join(unknown),
            file=sys.stderr,
        )
        return 1

    written = 0
    missing = []

    for lang in LANGUAGES:
        translation = lang_translations.get(lang)
        if not isinstance(translation, str) or not translation.strip():
            missing.append(lang)
            continue

        section = data.get(lang)
        if section is None:
            section = {}
            data[lang] = section
        elif not isinstance(section, dict):
            print(
                f"Error: language section '{lang}' is not a JSON object.",
                file=sys.stderr,
            )
            return 1

        # Only touch the short-description key. Existing long-description paths and
        # any other per-language metadata are preserved.
        section[description_tag] = translation
        written += 1

    if missing:
        print(
            "Error: translations are missing for: " + ", ".join(missing),
            file=sys.stderr,
        )
        print("No changes were written.", file=sys.stderr)
        return 1

    try:
        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except OSError as exc:
        print(f"Error writing {target}: {exc}", file=sys.stderr)
        return 1

    print(f"Added {written} translations for '{description_tag}' to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

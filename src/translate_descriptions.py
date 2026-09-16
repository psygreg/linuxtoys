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
    "vkvolt_desc": {
        "am": "በLinux ላይ ለVulkan ጨዋታዎች የመቆጣጠሪያ ፓነል፣ ከAMD Adrenalin እና NVIDIA Settings የLinux አማራጭ።",
        "ar": "لوحة تحكم لألعاب Vulkan على Linux، بديل لنظام Linux عن AMD Adrenalin وNVIDIA Settings.",
        "az": "Linux-da Vulkan oyunları üçün idarəetmə paneli, AMD Adrenalin və NVIDIA Settings-ə Linux alternativi.",
        "bg": "Контролен панел за Vulkan игри под Linux, Linux алтернатива на AMD Adrenalin и NVIDIA Settings.",
        "bn": "Linux-এ Vulkan গেমের জন্য একটি কন্ট্রোল প্যানেল, AMD Adrenalin এবং NVIDIA Settings-এর Linux বিকল্প।",
        "bs": "Kontrolna ploča za Vulkan igre na Linuxu, Linux alternativa za AMD Adrenalin i NVIDIA Settings.",
        "cs": "Ovládací panel pro hry využívající Vulkan na Linuxu, linuxová alternativa k AMD Adrenalin a NVIDIA Settings.",
        "da": "Kontrolpanel til Vulkan-spil på Linux, et Linux-alternativ til AMD Adrenalin og NVIDIA Settings.",
        "de": "Systemsteuerung für Vulkan-Spiele unter Linux, eine Linux-Alternative zu AMD Adrenalin und NVIDIA Settings.",
        "el": "Πίνακας ελέγχου για παιχνίδια Vulkan στο Linux, μια εναλλακτική λύση για Linux στα AMD Adrenalin και NVIDIA Settings.",
        "es": "Panel de control para juegos Vulkan en Linux, una alternativa para Linux a AMD Adrenalin y NVIDIA Settings.",
        "et": "Linuxi Vulkani mängude juhtpaneel, Linuxi alternatiiv AMD Adrenalinile ja NVIDIA Settingsile.",
        "fa": "پنل کنترل بازی‌های Vulkan در Linux، جایگزینی لینوکسی برای AMD Adrenalin و NVIDIA Settings.",
        "fi": "Ohjauspaneeli Vulkan-peleille Linuxissa, Linux-vaihtoehto AMD Adrenalinille ja NVIDIA Settingsille.",
        "fr": "Panneau de contrôle pour les jeux Vulkan sous Linux, une alternative Linux à AMD Adrenalin et NVIDIA Settings.",
        "ga": "Painéal rialaithe do chluichí Vulkan ar Linux, rogha Linux ar AMD Adrenalin agus NVIDIA Settings.",
        "he": "לוח בקרה למשחקי Vulkan ב-Linux, חלופה ל-Linux עבור AMD Adrenalin ו-NVIDIA Settings.",
        "hi": "Linux पर Vulkan गेम के लिए कंट्रोल पैनल, AMD Adrenalin और NVIDIA Settings का Linux विकल्प।",
        "hr": "Upravljačka ploča za Vulkan igre na Linuxu, Linux alternativa za AMD Adrenalin i NVIDIA Settings.",
        "hu": "Vezérlőpult Vulkan-játékokhoz Linuxon, az AMD Adrenalin és az NVIDIA Settings linuxos alternatívája.",
        "hy": "Linux-ում Vulkan խաղերի կառավարման վահանակ՝ AMD Adrenalin-ի և NVIDIA Settings-ի Linux այլընտրանք։",
        "id": "Panel kontrol untuk game Vulkan di Linux, alternatif Linux untuk AMD Adrenalin dan NVIDIA Settings.",
        "is": "Stjórnborð fyrir Vulkan-leiki á Linux, Linux-valkostur við AMD Adrenalin og NVIDIA Settings.",
        "it": "Pannello di controllo per i giochi Vulkan su Linux, un'alternativa Linux ad AMD Adrenalin e NVIDIA Settings.",
        "ja": "Linux 上の Vulkan ゲーム向けコントロールパネル。AMD Adrenalin と NVIDIA Settings の Linux 向け代替ツールです。",
        "ka": "Linux-ზე Vulkan თამაშების მართვის პანელი, AMD Adrenalin-ისა და NVIDIA Settings-ის Linux ალტერნატივა.",
        "km": "ផ្ទាំងបញ្ជាសម្រាប់ហ្គេម Vulkan លើ Linux ដែលជាជម្រើសសម្រាប់ Linux ជំនួស AMD Adrenalin និង NVIDIA Settings។",
        "ko": "Linux의 Vulkan 게임을 위한 제어판으로, AMD Adrenalin 및 NVIDIA Settings의 Linux 대안입니다.",
        "lo": "ແຜງຄວບຄຸມສຳລັບເກມ Vulkan ເທິງ Linux, ເປັນທາງເລືອກສຳລັບ Linux ແທນ AMD Adrenalin ແລະ NVIDIA Settings.",
        "lt": "„Vulkan“ žaidimų valdymo skydelis sistemoje „Linux“, „AMD Adrenalin“ ir „NVIDIA Settings“ alternatyva „Linux“ sistemai.",
        "lv": "Vulkan spēļu vadības panelis operētājsistēmā Linux, Linux alternatīva AMD Adrenalin un NVIDIA Settings.",
        "mn": "Linux дээрх Vulkan тоглоомуудад зориулсан удирдлагын самбар, AMD Adrenalin болон NVIDIA Settings-ийн Linux хувилбар.",
        "ms": "Panel kawalan untuk permainan Vulkan di Linux, alternatif Linux kepada AMD Adrenalin dan NVIDIA Settings.",
        "my": "Linux ပေါ်ရှိ Vulkan ဂိမ်းများအတွက် ထိန်းချုပ်မှု panel၊ AMD Adrenalin နှင့် NVIDIA Settings တို့၏ Linux အစားထိုးရွေးချယ်စရာ။",
        "nb": "Kontrollpanel for Vulkan-spill på Linux, et Linux-alternativ til AMD Adrenalin og NVIDIA Settings.",
        "ne": "Linux मा Vulkan खेलहरूका लागि नियन्त्रण प्यानल, AMD Adrenalin र NVIDIA Settings को Linux विकल्प।",
        "nl": "Configuratiescherm voor Vulkan-games op Linux, een Linux-alternatief voor AMD Adrenalin en NVIDIA Settings.",
        "pl": "Panel sterowania dla gier Vulkan w systemie Linux, linuksowa alternatywa dla AMD Adrenalin i NVIDIA Settings.",
        "pt": "Painel de controle para jogos Vulkan no Linux, uma alternativa ao AMD Adrenalin e NVIDIA Settings para Linux.",
        "ro": "Panou de control pentru jocuri Vulkan pe Linux, o alternativă Linux la AMD Adrenalin și NVIDIA Settings.",
        "ru": "Панель управления для Vulkan-игр в Linux, Linux-альтернатива AMD Adrenalin и NVIDIA Settings.",
        "sk": "Ovládací panel pre hry využívajúce Vulkan v Linuxe, linuxová alternatíva k AMD Adrenalin a NVIDIA Settings.",
        "sl": "Nadzorna plošča za igre Vulkan v Linuxu, alternativa za Linux programoma AMD Adrenalin in NVIDIA Settings.",
        "sq": "Panel kontrolli për lojërat Vulkan në Linux, një alternativë Linux ndaj AMD Adrenalin dhe NVIDIA Settings.",
        "sr": "Контролна табла за Vulkan игре на Linux-у, Linux алтернатива за AMD Adrenalin и NVIDIA Settings.",
        "sv": "Kontrollpanel för Vulkan-spel på Linux, ett Linux-alternativ till AMD Adrenalin och NVIDIA Settings.",
        "sw": "Paneli ya kudhibiti michezo ya Vulkan kwenye Linux, mbadala wa Linux kwa AMD Adrenalin na NVIDIA Settings.",
        "ta": "Linux-இல் Vulkan விளையாட்டுகளுக்கான கட்டுப்பாட்டுப் பலகம், AMD Adrenalin மற்றும் NVIDIA Settings-க்கான Linux மாற்று.",
        "tg": "Лавҳаи идоракунӣ барои бозиҳои Vulkan дар Linux, алтернативаи Linux ба AMD Adrenalin ва NVIDIA Settings.",
        "th": "แผงควบคุมสำหรับเกม Vulkan บน Linux ทางเลือกบน Linux สำหรับ AMD Adrenalin และ NVIDIA Settings",
        "tl": "Control panel para sa mga larong Vulkan sa Linux, isang alternatibo sa Linux para sa AMD Adrenalin at NVIDIA Settings.",
        "tr": "Linux'ta Vulkan oyunları için kontrol paneli, AMD Adrenalin ve NVIDIA Settings'e Linux alternatifi.",
        "uk": "Панель керування для Vulkan-ігор у Linux, Linux-альтернатива AMD Adrenalin і NVIDIA Settings.",
        "ur": "Linux پر Vulkan گیمز کے لیے کنٹرول پینل، AMD Adrenalin اور NVIDIA Settings کا Linux متبادل۔",
        "uz": "Linux'dagi Vulkan o'yinlari uchun boshqaruv paneli, AMD Adrenalin va NVIDIA Settings'ga Linux muqobili.",
        "vi": "Bảng điều khiển cho trò chơi Vulkan trên Linux, một giải pháp thay thế AMD Adrenalin và NVIDIA Settings dành cho Linux.",
        "zh": "Linux 上的 Vulkan 游戏控制面板，是 AMD Adrenalin 和 NVIDIA Settings 的 Linux 替代方案。"
    },
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

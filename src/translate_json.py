import json
import os

# Directory containing the language files
lang_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "p3/libs/lang/")

# Translations dictionary: key -> {lang_code: translation}
translations = {
    "app_page_open": {
        "am": "ክፈት",
        "ar": "فتح",
        "az": "Aç",
        "bg": "Отвори",
        "bn": "খুলুন",
        "bs": "Otvori",
        "cs": "Otevřít",
        "da": "Åbn",
        "de": "Öffnen",
        "el": "Άνοιγμα",
        "es": "Abrir",
        "et": "Ava",
        "fa": "باز کردن",
        "fi": "Avaa",
        "fr": "Ouvrir",
        "ga": "Oscail",
        "he": "פתיחה",
        "hi": "खोलें",
        "hr": "Otvori",
        "hu": "Megnyitás",
        "hy": "Բացել",
        "id": "Buka",
        "is": "Opna",
        "it": "Apri",
        "ja": "開く",
        "ka": "გახსნა",
        "km": "បើក",
        "ko": "열기",
        "lo": "ເປີດ",
        "lt": "Atverti",
        "lv": "Atvērt",
        "mn": "Нээх",
        "ms": "Buka",
        "my": "ဖွင့်ရန်",
        "nb": "Åpne",
        "ne": "खोल्नुहोस्",
        "nl": "Openen",
        "pl": "Otwórz",
        "pt": "Abrir",
        "ro": "Deschide",
        "ru": "Открыть",
        "sk": "Otvoriť",
        "sl": "Odpri",
        "sq": "Hap",
        "sr": "Отвори",
        "sv": "Öppna",
        "sw": "Fungua",
        "ta": "திற",
        "tg": "Кушодан",
        "th": "เปิด",
        "tl": "Buksan",
        "tr": "Aç",
        "uk": "Відкрити",
        "ur": "کھولیں",
        "uz": "Ochish",
        "vi": "Mở",
        "zh": "打开"
    },
    "app_page_source_system": {
        "am": "ስርዓት",
        "ar": "النظام",
        "az": "sistem",
        "bg": "система",
        "bn": "সিস্টেম",
        "bs": "sistem",
        "cs": "systém",
        "da": "system",
        "de": "System",
        "el": "σύστημα",
        "es": "sistema",
        "et": "süsteem",
        "fa": "سیستم",
        "fi": "järjestelmä",
        "fr": "système",
        "ga": "córas",
        "he": "מערכת",
        "hi": "सिस्टम",
        "hr": "sustav",
        "hu": "rendszer",
        "hy": "համակարգ",
        "id": "sistem",
        "is": "kerfi",
        "it": "sistema",
        "ja": "システム",
        "ka": "სისტემა",
        "km": "ប្រព័ន្ធ",
        "ko": "시스템",
        "lo": "ລະບົບ",
        "lt": "sistema",
        "lv": "sistēma",
        "mn": "систем",
        "ms": "sistem",
        "my": "စနစ်",
        "nb": "system",
        "ne": "प्रणाली",
        "nl": "systeem",
        "pl": "system",
        "pt": "sistema",
        "ro": "sistem",
        "ru": "система",
        "sk": "systém",
        "sl": "sistem",
        "sq": "sistem",
        "sr": "систем",
        "sv": "system",
        "sw": "mfumo",
        "ta": "கணினி",
        "tg": "система",
        "th": "ระบบ",
        "tl": "system",
        "tr": "sistem",
        "uk": "система",
        "ur": "سسٹم",
        "uz": "tizim",
        "vi": "hệ thống",
        "zh": "系统"
    }
}

# Skip 'en' since it's already added
for key, lang_translations in translations.items():
    for lang, translation in lang_translations.items():
        file_path = os.path.join(lang_dir, f"{lang}.json")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data[key] = translation
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Added {key} to {lang}.json")
        else:
            print(f"File {file_path} does not exist")

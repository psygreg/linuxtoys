import json
import os

# Directory containing the language files
lang_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "p3/libs/lang/")

# Translations dictionary: key -> {lang_code: translation}
translations = {
    "specials": {
        "am": "ልዩ",
        "ar": "حصري",
        "az": "Eksklüziv",
        "bg": "Ексклузивно",
        "bn": "এক্সক্লুসিভ",
        "bs": "Ekskluzivno",
        "cs": "Exkluzivní",
        "da": "Eksklusivt",
        "de": "Exklusiv",
        "el": "Αποκλειστικά",
        "es": "Exclusivo",
        "et": "Eksklusiivne",
        "fa": "اختصاصی",
        "fi": "Eksklusiiviset",
        "fr": "Exclusif",
        "ga": "Eisiach",
        "he": "בלעדי",
        "hi": "विशेष",
        "hr": "Ekskluzivno",
        "hu": "Exkluzív",
        "hy": "Բացառիկ",
        "id": "Eksklusif",
        "is": "Sérstakt",
        "it": "Esclusivi",
        "ja": "限定",
        "ka": "ექსკლუზიური",
        "km": "ផ្តាច់មុខ",
        "ko": "독점",
        "lo": "ພິເສດ",
        "lt": "Išskirtinė",
        "lv": "Ekskluzīvi",
        "mn": "Онцгой",
        "ms": "Eksklusif",
        "my": "သီးသန့်",
        "nb": "Eksklusivt",
        "ne": "विशेष",
        "nl": "Exclusief",
        "pl": "Ekskluzywne",
        "pt": "Exclusivos",
        "ro": "Exclusive",
        "ru": "Эксклюзив",
        "sk": "Exkluzívne",
        "sl": "Ekskluzivno",
        "sq": "Ekskluzive",
        "sr": "Ексклузивно",
        "sv": "Exklusivt",
        "sw": "Kipekee",
        "ta": "பிரத்தியேகமானவை",
        "tg": "Истисноӣ",
        "th": "เอ็กซ์คลูซีฟ",
        "tl": "Eksklusibo",
        "tr": "Özel",
        "uk": "Ексклюзив",
        "ur": "خصوصی",
        "uz": "Eksklyuziv",
        "vi": "Độc quyền",
        "zh": "独家"
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

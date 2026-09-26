import json
import os

# Directory containing the language files
lang_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "p3/libs/lang/")

# Translations dictionary: key -> {lang_code: translation}
translations = {
    "app_page_details": {
        "am": "ዝርዝሮች",
        "ar": "التفاصيل",
        "az": "Təfərrüatlar",
        "bg": "Подробности",
        "bn": "বিস্তারিত",
        "bs": "Detalji",
        "cs": "Podrobnosti",
        "da": "Detaljer",
        "de": "Details",
        "el": "Λεπτομέρειες",
        "es": "Detalles",
        "et": "Üksikasjad",
        "fa": "جزئیات",
        "fi": "Tiedot",
        "fr": "Détails",
        "ga": "Sonraí",
        "he": "פרטים",
        "hi": "विवरण",
        "hr": "Pojedinosti",
        "hu": "Részletek",
        "hy": "Մանրամասներ",
        "id": "Detail",
        "is": "Upplýsingar",
        "it": "Dettagli",
        "ja": "詳細",
        "ka": "დეტალები",
        "km": "ព័ត៌មានលម្អិត",
        "ko": "세부 정보",
        "lo": "ລາຍລະອຽດ",
        "lt": "Išsami informacija",
        "lv": "Informācija",
        "mn": "Дэлгэрэнгүй",
        "ms": "Butiran",
        "my": "အသေးစိတ်",
        "nb": "Detaljer",
        "ne": "विवरण",
        "nl": "Details",
        "pl": "Szczegóły",
        "pt": "Detalhes",
        "ro": "Detalii",
        "ru": "Подробности",
        "sk": "Podrobnosti",
        "sl": "Podrobnosti",
        "sq": "Detaje",
        "sr": "Детаљи",
        "sv": "Detaljer",
        "sw": "Maelezo",
        "ta": "விவரங்கள்",
        "tg": "Тафсилот",
        "th": "รายละเอียด",
        "tl": "Mga detalye",
        "tr": "Ayrıntılar",
        "uk": "Подробиці",
        "ur": "تفصیلات",
        "uz": "Tafsilotlar",
        "vi": "Chi tiết",
        "zh": "详细信息"
    },
    "app_page_extensions": {
        "am": "ቅጥያዎች",
        "ar": "الامتدادات",
        "az": "Genişləndirmələr",
        "bg": "Разширения",
        "bn": "এক্সটেনশন",
        "bs": "Proširenja",
        "cs": "Rozšíření",
        "da": "Udvidelser",
        "de": "Erweiterungen",
        "el": "Επεκτάσεις",
        "es": "Extensiones",
        "et": "Laiendused",
        "fa": "افزونه‌ها",
        "fi": "Laajennukset",
        "fr": "Extensions",
        "ga": "Eisínteachtaí",
        "he": "הרחבות",
        "hi": "एक्सटेंशन",
        "hr": "Proširenja",
        "hu": "Bővítmények",
        "hy": "Ընդլայնումներ",
        "id": "Ekstensi",
        "is": "Viðbætur",
        "it": "Estensioni",
        "ja": "拡張機能",
        "ka": "გაფართოებები",
        "km": "ផ្នែកបន្ថែម",
        "ko": "확장 기능",
        "lo": "ສ່ວນຂະຫຍາຍ",
        "lt": "Plėtiniai",
        "lv": "Paplašinājumi",
        "mn": "Өргөтгөлүүд",
        "ms": "Sambungan",
        "my": "တိုးချဲ့မှုများ",
        "nb": "Utvidelser",
        "ne": "विस्तारहरू",
        "nl": "Extensies",
        "pl": "Rozszerzenia",
        "pt": "Extensões",
        "ro": "Extensii",
        "ru": "Расширения",
        "sk": "Rozšírenia",
        "sl": "Razširitve",
        "sq": "Shtesa",
        "sr": "Проширења",
        "sv": "Tillägg",
        "sw": "Viendelezi",
        "ta": "நீட்சிகள்",
        "tg": "Васеъкуниҳо",
        "th": "ส่วนขยาย",
        "tl": "Mga extension",
        "tr": "Uzantılar",
        "uk": "Розширення",
        "ur": "ایکسٹینشنز",
        "uz": "Kengaytmalar",
        "vi": "Tiện ích mở rộng",
        "zh": "扩展"
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

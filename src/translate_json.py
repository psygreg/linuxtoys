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
    "category_available": {
        "am": "የሚገኝ",
        "ar": "متاح",
        "az": "Mövcud",
        "bg": "Налично",
        "bn": "উপলব্ধ",
        "bs": "Dostupno",
        "cs": "Dostupné",
        "da": "Tilgængelig",
        "de": "Verfügbar",
        "el": "Διαθέσιμο",
        "es": "Disponible",
        "et": "Saadaval",
        "fa": "موجود",
        "fi": "Saatavilla",
        "fr": "Disponible",
        "ga": "Ar fáil",
        "he": "זמין",
        "hi": "उपलब्ध",
        "hr": "Dostupno",
        "hu": "Elérhető",
        "hy": "Հասանելի",
        "id": "Tersedia",
        "is": "Í boði",
        "it": "Disponibile",
        "ja": "利用可能",
        "ka": "ხელმისაწვდომი",
        "km": "មាន",
        "ko": "사용 가능",
        "lo": "ມີໃຫ້ໃຊ້",
        "lt": "Pasiekiama",
        "lv": "Pieejams",
        "mn": "Боломжтой",
        "ms": "Tersedia",
        "my": "ရရှိနိုင်သည်",
        "nb": "Tilgjengelig",
        "ne": "उपलब्ध",
        "nl": "Beschikbaar",
        "pl": "Dostępne",
        "pt": "Disponível",
        "ro": "Disponibil",
        "ru": "Доступно",
        "sk": "Dostupné",
        "sl": "Na voljo",
        "sq": "E disponueshme",
        "sr": "Доступно",
        "sv": "Tillgänglig",
        "sw": "Inapatikana",
        "ta": "கிடைக்கிறது",
        "tg": "Дастрас",
        "th": "พร้อมใช้งาน",
        "tl": "Available",
        "tr": "Mevcut",
        "uk": "Доступно",
        "ur": "دستیاب",
        "uz": "Mavjud",
        "vi": "Có sẵn",
        "zh": "可用"
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

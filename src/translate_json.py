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
    "subtitle": {
        "am": "ለሁሉም የLinux ነገር።",
        "ar": "لكل ما يتعلق بـ Linux.",
        "az": "Linux ilə bağlı hər şey üçün.",
        "bg": "За всичко свързано с Linux.",
        "bn": "Linux-এর সবকিছুর জন্য।",
        "bs": "Za sve što se tiče Linuxa.",
        "cs": "Pro vše kolem Linuxu.",
        "da": "Til alt inden for Linux.",
        "de": "Für alles rund um Linux.",
        "el": "Για οτιδήποτε αφορά το Linux.",
        "es": "Para todo lo relacionado con Linux.",
        "et": "Kõigeks, mis puudutab Linuxit.",
        "fa": "برای همه‌چیز در دنیای Linux.",
        "fi": "Kaikkeen Linuxiin liittyvään.",
        "fr": "Pour tout ce qui concerne Linux.",
        "ga": "Do gach rud a bhaineann le Linux.",
        "he": "לכל מה שקשור ל-Linux.",
        "hi": "Linux से जुड़ी हर चीज़ के लिए।",
        "hr": "Za sve vezano uz Linux.",
        "hu": "Mindenhez, ami Linux.",
        "hy": "Linux-ի հետ կապված ամեն ինչի համար։",
        "id": "Untuk segala hal tentang Linux.",
        "is": "Fyrir allt sem tengist Linux.",
        "it": "Per tutto ciò che riguarda Linux.",
        "ja": "Linux のすべてに。",
        "ka": "ყველაფრისთვის, რაც Linux-ს ეხება.",
        "km": "សម្រាប់អ្វីគ្រប់យ៉ាងអំពី Linux។",
        "ko": "Linux의 모든 것을 위해.",
        "lo": "ສຳລັບທຸກຢ່າງກ່ຽວກັບ Linux.",
        "lt": "Viskam, kas susiję su Linux.",
        "lv": "Visam, kas saistīts ar Linux.",
        "mn": "Linux-тэй холбоотой бүх зүйлд.",
        "ms": "Untuk segala-galanya tentang Linux.",
        "my": "Linux နှင့်ပတ်သက်သမျှ အရာအားလုံးအတွက်။",
        "nb": "For alt som har med Linux å gjøre.",
        "ne": "Linux सम्बन्धी सबै कुराका लागि।",
        "nl": "Voor alles wat met Linux te maken heeft.",
        "pl": "Do wszystkiego, co związane z Linuxem.",
        "pt": "Para tudo no Linux.",
        "ro": "Pentru tot ce ține de Linux.",
        "ru": "Для всего, что связано с Linux.",
        "sk": "Pre všetko okolo Linuxu.",
        "sl": "Za vse, kar je povezano z Linuxom.",
        "sq": "Për gjithçka që lidhet me Linux.",
        "sr": "За све што се тиче Linux-а.",
        "sv": "För allt som rör Linux.",
        "sw": "Kwa kila kitu kuhusu Linux.",
        "ta": "Linux தொடர்பான அனைத்திற்கும்.",
        "tg": "Барои ҳама чизе, ки ба Linux марбут аст.",
        "th": "สำหรับทุกสิ่งเกี่ยวกับ Linux",
        "tl": "Para sa lahat ng tungkol sa Linux.",
        "tr": "Linux ile ilgili her şey için.",
        "uk": "Для всього, що пов’язано з Linux.",
        "ur": "Linux سے متعلق ہر چیز کے لیے۔",
        "uz": "Linux bilan bog‘liq barcha narsalar uchun.",
        "vi": "Cho mọi thứ về Linux.",
        "zh": "满足您对 Linux 的一切需求。"
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

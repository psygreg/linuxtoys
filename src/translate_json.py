import json
import os

# Directory containing the language files
lang_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "p3/libs/lang/")

# Translations dictionary: key -> {lang_code: translation}
translations = {
    "uri_install_error_title": {
        "am": "የLinuxToys አገናኝን መክፈት አልተቻለም",
        "ar": "تعذر فتح رابط LinuxToys",
        "az": "LinuxToys keçidini açmaq mümkün olmadı",
        "bg": "Връзката към LinuxToys не може да бъде отворена",
        "bn": "LinuxToys লিঙ্ক খোলা যায়নি",
        "bs": "Nije moguće otvoriti LinuxToys vezu",
        "cs": "Odkaz LinuxToys nelze otevřít",
        "da": "Kunne ikke åbne LinuxToys-linket",
        "de": "LinuxToys-Link konnte nicht geöffnet werden",
        "el": "Δεν ήταν δυνατό το άνοιγμα του συνδέσμου LinuxToys",
        "es": "No se pudo abrir el enlace de LinuxToys",
        "et": "LinuxToysi linki ei saa avada",
        "fa": "پیوند LinuxToys باز نشد",
        "fi": "LinuxToys-linkkiä ei voitu avata",
        "fr": "Impossible d’ouvrir le lien LinuxToys",
        "ga": "Níorbh fhéidir nasc LinuxToys a oscailt",
        "he": "לא ניתן לפתוח את הקישור של LinuxToys",
        "hi": "LinuxToys लिंक नहीं खोला जा सका",
        "hr": "Nije moguće otvoriti LinuxToys poveznicu",
        "hu": "A LinuxToys-hivatkozás nem nyitható meg",
        "hy": "Չհաջողվեց բացել LinuxToys հղումը",
        "id": "Tidak dapat membuka tautan LinuxToys",
        "is": "Ekki tókst að opna LinuxToys-tengilinn",
        "it": "Impossibile aprire il link LinuxToys",
        "ja": "LinuxToys リンクを開けません",
        "ka": "LinuxToys-ის ბმულის გახსნა ვერ მოხერხდა",
        "km": "មិនអាចបើកតំណ LinuxToys បានទេ",
        "ko": "LinuxToys 링크를 열 수 없음",
        "lo": "ບໍ່ສາມາດເປີດລິ້ງ LinuxToys ໄດ້",
        "lt": "Nepavyko atidaryti LinuxToys nuorodos",
        "lv": "Neizdevās atvērt LinuxToys saiti",
        "mn": "LinuxToys холбоосыг нээх боломжгүй",
        "ms": "Tidak dapat membuka pautan LinuxToys",
        "my": "LinuxToys လင့်ခ်ကို ဖွင့်၍မရပါ",
        "nb": "Kunne ikke åpne LinuxToys-lenken",
        "ne": "LinuxToys लिङ्क खोल्न सकिएन",
        "nl": "Kan LinuxToys-link niet openen",
        "pl": "Nie można otworzyć odnośnika LinuxToys",
        "pt": "Não foi possível abrir o link do LinuxToys",
        "ro": "Linkul LinuxToys nu a putut fi deschis",
        "ru": "Не удалось открыть ссылку LinuxToys",
        "sk": "Odkaz LinuxToys sa nepodarilo otvoriť",
        "sl": "Povezave LinuxToys ni mogoče odpreti",
        "sq": "Nuk mund të hapet lidhja LinuxToys",
        "sr": "Није могуће отворити LinuxToys везу",
        "sv": "Kunde inte öppna LinuxToys-länken",
        "sw": "Imeshindikana kufungua kiungo cha LinuxToys",
        "ta": "LinuxToys இணைப்பைத் திறக்க முடியவில்லை",
        "tg": "Пайванди LinuxToys кушода нашуд",
        "th": "ไม่สามารถเปิดลิงก์ LinuxToys ได้",
        "tl": "Hindi mabuksan ang LinuxToys link",
        "tr": "LinuxToys bağlantısı açılamadı",
        "uk": "Не вдалося відкрити посилання LinuxToys",
        "ur": "LinuxToys لنک نہیں کھولا جا سکا",
        "uz": "LinuxToys havolasini ochib bo'lmadi",
        "vi": "Không thể mở liên kết LinuxToys",
        "zh": "无法打开 LinuxToys 链接"
    },
"app_page_snap_revert": {
    "am": " ወደ ቀድሞው መልስ ",
    "ar": " رجوع ",
    "az": " Geri qaytar ",
    "bg": " Връщане ",
    "bn": " ফিরিয়ে নিন ",
    "bs": " Vrati ",
    "cs": " Vrátit ",
    "da": " Tilbagefør ",
    "de": " Zurücksetzen ",
    "el": " Επαναφορά ",
    "es": " Revertir ",
    "et": " Taasta ",
    "fa": " بازگردانی ",
    "fi": " Palauta ",
    "fr": " Rétablir ",
    "ga": " Fill ar ais ",
    "he": " החזרה ",
    "hi": " वापस लौटाएँ ",
    "hr": " Vrati ",
    "hu": " Visszaállítás ",
    "hy": " Վերադարձնել ",
    "id": " Kembalikan ",
    "is": " Færa aftur ",
    "it": " Ripristina ",
    "ja": " 元に戻す ",
    "ka": " დაბრუნება ",
    "km": " ត្រឡប់ ",
    "ko": " 되돌리기 ",
    "lo": " ຍ້ອນກັບ ",
    "lt": " Grąžinti ",
    "lv": " Atgriezt ",
    "mn": " Буцаах ",
    "ms": " Kembalikan ",
    "my": " ပြန်ပြောင်းရန် ",
    "nb": " Tilbakestill ",
    "ne": " फर्काउनुहोस् ",
    "nl": " Terugzetten ",
    "pl": " Przywróć ",
    "pt": " Reverter ",
    "ro": " Revino ",
    "ru": " Откатить ",
    "sk": " Vrátiť ",
    "sl": " Povrni ",
    "sq": " Rikthe ",
    "sr": " Врати ",
    "sv": " Återställ ",
    "sw": " Rejesha ",
    "ta": " மாற்றியமை ",
    "tg": " Баргардондан ",
    "th": " ย้อนกลับ ",
    "tl": " I-revert ",
    "tr": " Geri al ",
    "uk": " Відкотити ",
    "ur": " واپس کریں ",
    "uz": " Qaytarish ",
    "vi": " Hoàn nguyên ",
    "zh": " 还原 "
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

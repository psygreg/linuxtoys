import json
import os

# Directory containing the language files
lang_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "p3/libs/lang/")

# Translations dictionary: key -> {lang_code: translation}
translations = {
"dependency_block_title": {
    "am": "ማስወገድ ታግዷል",
    "ar": "تم حظر الإزالة",
    "az": "Silmə bloklanıb",
    "bg": "Премахването е блокирано",
    "bn": "অপসারণ ব্লক করা হয়েছে",
    "bs": "Uklanjanje je blokirano",
    "cs": "Odstranění je zablokováno",
    "da": "Fjernelse blokeret",
    "de": "Entfernen blockiert",
    "el": "Η αφαίρεση αποκλείστηκε",
    "es": "Eliminación bloqueada",
    "et": "Eemaldamine on blokeeritud",
    "fa": "حذف مسدود شده است",
    "fi": "Poistaminen estetty",
    "fr": "Suppression bloquée",
    "ga": "Baineadh bac den bhaint",
    "he": "ההסרה נחסמה",
    "hi": "हटाना अवरुद्ध है",
    "hr": "Uklanjanje je blokirano",
    "hu": "Eltávolítás blokkolva",
    "hy": "Հեռացումն արգելափակված է",
    "id": "Penghapusan diblokir",
    "is": "Fjarlæging útilokuð",
    "it": "Rimozione bloccata",
    "ja": "削除がブロックされました",
    "ka": "წაშლა დაბლოკილია",
    "km": "ការលុបត្រូវបានរារាំង",
    "ko": "제거가 차단됨",
    "lo": "ການລຶບຖືກບລັອກ",
    "lt": "Šalinimas užblokuotas",
    "lv": "Noņemšana bloķēta",
    "mn": "Устгах үйлдэл хаагдсан",
    "ms": "Pembuangan disekat",
    "my": "ဖယ်ရှားခြင်းကို ပိတ်ဆို့ထားသည်",
    "nb": "Fjerning blokkert",
    "ne": "हटाउने कार्य रोकिएको छ",
    "nl": "Verwijderen geblokkeerd",
    "pl": "Usuwanie zablokowane",
    "pt": "Remoção bloqueada",
    "ro": "Eliminare blocată",
    "ru": "Удаление заблокировано",
    "sk": "Odstránenie je zablokované",
    "sl": "Odstranitev je blokirana",
    "sq": "Heqja është bllokuar",
    "sr": "Уклањање је блокирано",
    "sv": "Borttagning blockerad",
    "sw": "Uondoaji umezuiwa",
    "ta": "அகற்றுதல் தடுக்கப்பட்டது",
    "tg": "Несткунӣ манъ шудааст",
    "th": "การนำออกถูกบล็อก",
    "tl": "Naka-block ang pag-alis",
    "tr": "Kaldırma engellendi",
    "uk": "Видалення заблоковано",
    "ur": "ہٹانا مسدود ہے",
    "uz": "Olib tashlash bloklangan",
    "vi": "Đã chặn việc gỡ bỏ",
    "zh": "移除已被阻止"
},
"main_menu": {
    "am": "ዋና ምናሌ",
    "ar": "القائمة الرئيسية",
    "az": "Əsas menyu",
    "bg": "Главно меню",
    "bn": "প্রধান মেনু",
    "bs": "Glavni meni",
    "cs": "Hlavní nabídka",
    "da": "Hovedmenu",
    "de": "Hauptmenü",
    "el": "Κύριο μενού",
    "es": "Menú principal",
    "et": "Peamenüü",
    "fa": "منوی اصلی",
    "fi": "Päävalikko",
    "fr": "Menu principal",
    "ga": "Príomh-roghchlár",
    "he": "תפריט ראשי",
    "hi": "मुख्य मेनू",
    "hr": "Glavni izbornik",
    "hu": "Főmenü",
    "hy": "Գլխավոր ընտրացանկ",
    "id": "Menu utama",
    "is": "Aðalvalmynd",
    "it": "Menu principale",
    "ja": "メインメニュー",
    "ka": "მთავარი მენიუ",
    "km": "ម៉ឺនុយមេ",
    "ko": "메인 메뉴",
    "lo": "ເມນູຫຼັກ",
    "lt": "Pagrindinis meniu",
    "lv": "Galvenā izvēlne",
    "mn": "Үндсэн цэс",
    "ms": "Menu utama",
    "my": "ပင်မ မီနူး",
    "nb": "Hovedmeny",
    "ne": "मुख्य मेनु",
    "nl": "Hoofdmenu",
    "pl": "Menu główne",
    "pt": "Menu principal",
    "ro": "Meniu principal",
    "ru": "Главное меню",
    "sk": "Hlavná ponuka",
    "sl": "Glavni meni",
    "sq": "Menyja kryesore",
    "sr": "Главни мени",
    "sv": "Huvudmeny",
    "sw": "Menyu kuu",
    "ta": "முதன்மை மெனு",
    "tg": "Менюи асосӣ",
    "th": "เมนูหลัก",
    "tl": "Pangunahing menu",
    "tr": "Ana menü",
    "uk": "Головне меню",
    "ur": "مرکزی مینو",
    "uz": "Asosiy menyu",
    "vi": "Menu chính",
    "zh": "主菜单"
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

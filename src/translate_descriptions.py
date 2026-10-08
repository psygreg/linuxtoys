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
    "opticlient_desc": {
        "am": "የOptiScaler ሞድን በሁሉም ጨዋታዎችዎ ላይ መጫን፣ ማስተዳደር እና ማዘመንን ቀላል ያድርጉ።",
        "ar": "بسّط تثبيت تعديل OptiScaler وإدارته وتحديثه عبر مكتبة ألعابك بالكامل.",
        "az": "OptiScaler modunun bütün oyun kitabxananızda quraşdırılmasını, idarə edilməsini və yenilənməsini asanlaşdırın.",
        "bg": "Улеснете инсталирането, управлението и актуализирането на мода OptiScaler във всичките си игри.",
        "bn": "আপনার সম্পূর্ণ গেম লাইব্রেরিতে OptiScaler মড ইনস্টল, পরিচালনা ও আপডেট করা সহজ করুন।",
        "bs": "Pojednostavite instalaciju, upravljanje i ažuriranje OptiScaler moda u cijeloj biblioteci igara.",
        "cs": "Zjednodušte instalaci, správu a aktualizaci modu OptiScaler v celé své herní knihovně.",
        "da": "Gør installation, administration og opdatering af OptiScaler-moddet nemmere i hele dit spilbibliotek.",
        "de": "Vereinfache die Installation, Verwaltung und Aktualisierung der OptiScaler-Mod in deiner gesamten Spielebibliothek.",
        "el": "Απλοποιήστε την εγκατάσταση, τη διαχείριση και την ενημέρωση του mod OptiScaler σε ολόκληρη τη βιβλιοθήκη παιχνιδιών σας.",
        "es": "Simplifica la instalación, gestión y actualización del mod OptiScaler en toda tu biblioteca de juegos.",
        "et": "Lihtsusta OptiScaleri modi paigaldamist, haldamist ja uuendamist kogu oma mängukogus.",
        "fa": "نصب، مدیریت و به‌روزرسانی ماد OptiScaler را در سراسر کتابخانه بازی‌های خود آسان کنید.",
        "fi": "Helpota OptiScaler-modin asentamista, hallintaa ja päivittämistä koko pelikirjastossasi.",
        "fr": "Simplifiez l’installation, la gestion et la mise à jour du mod OptiScaler dans toute votre bibliothèque de jeux.",
        "ga": "Simpligh suiteáil, bainistiú agus nuashonrú an mhod OptiScaler ar fud do leabharlainne cluichí.",
        "he": "פשטו את ההתקנה, הניהול והעדכון של מוד OptiScaler בכל ספריית המשחקים שלכם.",
        "hi": "अपनी पूरी गेम लाइब्रेरी में OptiScaler मॉड को इंस्टॉल, प्रबंधित और अपडेट करना आसान बनाएं।",
        "hr": "Pojednostavite instalaciju, upravljanje i ažuriranje moda OptiScaler u cijeloj biblioteci igara.",
        "hu": "Egyszerűsítse az OptiScaler mod telepítését, kezelését és frissítését a teljes játékkönyvtárában.",
        "hy": "Պարզեցրեք OptiScaler մոդի տեղադրումը, կառավարումը և թարմացումը ձեր ամբողջ խաղադարանում։",
        "id": "Permudah pemasangan, pengelolaan, dan pembaruan mod OptiScaler di seluruh pustaka game Anda.",
        "is": "Einfaldaðu uppsetningu, stjórnun og uppfærslu OptiScaler-mótsins í öllu leikjasafninu þínu.",
        "it": "Semplifica l’installazione, la gestione e l’aggiornamento della mod OptiScaler in tutta la tua libreria di giochi.",
        "ja": "ゲームライブラリ全体でOptiScaler Modのインストール、管理、更新を簡単に行えます。",
        "ka": "გაამარტივეთ OptiScaler მოდის ინსტალაცია, მართვა და განახლება თქვენი თამაშების მთელ ბიბლიოთეკაში.",
        "km": "ធ្វើឱ្យការដំឡើង ការគ្រប់គ្រង និងការធ្វើបច្ចុប្បន្នភាពម៉ូដ OptiScaler នៅក្នុងបណ្ណាល័យហ្គេមទាំងមូលរបស់អ្នកកាន់តែងាយស្រួល។",
        "ko": "전체 게임 라이브러리에서 OptiScaler 모드의 설치, 관리 및 업데이트를 간편하게 하세요.",
        "lo": "ເຮັດໃຫ້ການຕິດຕັ້ງ ຈັດການ ແລະອັບເດດມອດ OptiScaler ໃນຄັງເກມທັງໝົດຂອງທ່ານງ່າຍຂຶ້ນ.",
        "lt": "Supaprastinkite „OptiScaler“ modifikacijos diegimą, valdymą ir atnaujinimą visoje savo žaidimų bibliotekoje.",
        "lv": "Vienkāršojiet OptiScaler modifikācijas instalēšanu, pārvaldību un atjaunināšanu visā spēļu bibliotēkā.",
        "mn": "Тоглоомын сангийнхаа бүх тоглоомд OptiScaler модыг суулгах, удирдах, шинэчлэх үйлдлийг хялбарчлаарай.",
        "ms": "Permudahkan pemasangan, pengurusan dan pengemaskinian mod OptiScaler di seluruh pustaka permainan anda.",
        "my": "သင့်ဂိမ်းစာကြည့်တိုက်တစ်ခုလုံးတွင် OptiScaler mod ကို ထည့်သွင်းခြင်း၊ စီမံခန့်ခွဲခြင်းနှင့် အပ်ဒိတ်လုပ်ခြင်းတို့ကို လွယ်ကူစေပါ။",
        "nb": "Gjør det enklere å installere, administrere og oppdatere OptiScaler-modden i hele spillbiblioteket ditt.",
        "ne": "आफ्नो सम्पूर्ण गेम लाइब्रेरीमा OptiScaler मोड स्थापना, व्यवस्थापन र अद्यावधिक गर्न सजिलो बनाउनुहोस्।",
        "nl": "Vereenvoudig de installatie, het beheer en het bijwerken van de OptiScaler-mod in je hele gamebibliotheek.",
        "pl": "Uprość instalację, zarządzanie i aktualizację moda OptiScaler w całej bibliotece gier.",
        "pt": "Simplifique a instalação, o gerenciamento e a atualização do mod OptiScaler em toda a sua biblioteca de jogos.",
        "ro": "Simplificați instalarea, gestionarea și actualizarea modului OptiScaler în întreaga bibliotecă de jocuri.",
        "ru": "Упростите установку, управление и обновление мода OptiScaler во всей вашей библиотеке игр.",
        "sk": "Zjednodušte inštaláciu, správu a aktualizáciu modu OptiScaler v celej svojej knižnici hier.",
        "sl": "Poenostavite namestitev, upravljanje in posodabljanje moda OptiScaler v celotni knjižnici iger.",
        "sq": "Thjeshtoni instalimin, menaxhimin dhe përditësimin e modit OptiScaler në të gjithë bibliotekën tuaj të lojërave.",
        "sr": "Поједноставите инсталацију, управљање и ажурирање мода OptiScaler у целој библиотеци игара.",
        "sv": "Förenkla installation, hantering och uppdatering av OptiScaler-modden i hela ditt spelbibliotek.",
        "sw": "Rahisisha usakinishaji, usimamizi na usasishaji wa mod ya OptiScaler katika maktaba yako yote ya michezo.",
        "ta": "உங்கள் முழு கேம் நூலகத்திலும் OptiScaler மோடை நிறுவுதல், நிர்வகித்தல் மற்றும் புதுப்பித்தலை எளிதாக்குங்கள்.",
        "tg": "Насб, идоракунӣ ва навсозии модули OptiScaler-ро дар тамоми китобхонаи бозиҳои худ осон кунед.",
        "th": "ทำให้การติดตั้ง จัดการ และอัปเดตม็อด OptiScaler ในคลังเกมทั้งหมดของคุณง่ายขึ้น",
        "tl": "Padaliin ang pag-install, pamamahala, at pag-update ng OptiScaler mod sa buong library ng iyong mga laro.",
        "tr": "OptiScaler modunun tüm oyun kütüphanenizde kurulumunu, yönetimini ve güncellenmesini kolaylaştırın.",
        "uk": "Спростіть встановлення, керування й оновлення мода OptiScaler в усій вашій бібліотеці ігор.",
        "ur": "اپنی پوری گیم لائبریری میں OptiScaler موڈ کی تنصیب، انتظام اور اپ ڈیٹ کو آسان بنائیں۔",
        "uz": "Butun oʻyin kutubxonangizda OptiScaler modini oʻrnatish, boshqarish va yangilashni osonlashtiring.",
        "vi": "Đơn giản hóa việc cài đặt, quản lý và cập nhật bản mod OptiScaler trên toàn bộ thư viện trò chơi của bạn.",
        "zh": "简化整个游戏库中 OptiScaler 模组的安装、管理和更新。",
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

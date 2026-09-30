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
    "photon_desc": {
        "am": "ለmacOS፣ Windows እና Linux ነፃ የዴስክቶፕ ፎቶ አርታዒ። ፎቶዎችን ያርትዑ፣ ባለንብርብር ንድፎችን ይፍጠሩ እና PSD ፋይሎችን ይክፈቱ ወይም ያስቀምጡ።",
        "ar": "محرر صور مجاني لسطح المكتب لأنظمة macOS وWindows وLinux. حرّر الصور وأنشئ تصاميم متعددة الطبقات وافتح ملفات PSD أو احفظها.",
        "az": "macOS, Windows və Linux üçün pulsuz masaüstü foto redaktoru. Fotoları redaktə edin, laylı dizaynlar yaradın və PSD fayllarını açın və ya saxlayın.",
        "bg": "Безплатен настолен фоторедактор за macOS, Windows и Linux. Редактирайте снимки, създавайте многослойни дизайни и отваряйте или запазвайте PSD файлове.",
        "bn": "macOS, Windows এবং Linux-এর জন্য একটি বিনামূল্যের ডেস্কটপ ফটো এডিটর। ছবি সম্পাদনা করুন, স্তরযুক্ত ডিজাইন তৈরি করুন এবং PSD ফাইল খুলুন বা সংরক্ষণ করুন।",
        "bs": "Besplatan desktop uređivač fotografija za macOS, Windows i Linux. Uređujte fotografije, kreirajte slojevite dizajne i otvarajte ili spremajte PSD datoteke.",
        "cs": "Bezplatný desktopový editor fotografií pro macOS, Windows a Linux. Upravujte fotografie, vytvářejte návrhy ve vrstvách a otevírejte nebo ukládejte soubory PSD.",
        "da": "Et gratis fotoredigeringsprogram til macOS, Windows og Linux. Rediger fotos, opret design med lag, og åbn eller gem PSD-filer.",
        "de": "Ein kostenloser Desktop-Fotoeditor für macOS, Windows und Linux. Fotos bearbeiten, Designs mit Ebenen erstellen und PSD-Dateien öffnen oder speichern.",
        "el": "Ένα δωρεάν πρόγραμμα επεξεργασίας φωτογραφιών για macOS, Windows και Linux. Επεξεργαστείτε φωτογραφίες, δημιουργήστε σχέδια με επίπεδα και ανοίξτε ή αποθηκεύστε αρχεία PSD.",
        "es": "Un editor de fotos de escritorio gratuito para macOS, Windows y Linux. Edita fotos, crea diseños por capas y abre o guarda archivos PSD.",
        "et": "Tasuta töölaua fotoredaktor macOS-ile, Windowsile ja Linuxile. Töötle fotosid, loo kihtidega kujundusi ning ava või salvesta PSD-faile.",
        "fa": "یک ویرایشگر رایگان عکس برای دسکتاپ در macOS، Windows و Linux. عکس‌ها را ویرایش کنید، طرح‌های لایه‌ای بسازید و فایل‌های PSD را باز یا ذخیره کنید.",
        "fi": "Ilmainen työpöydän kuvankäsittelyohjelma macOS:lle, Windowsille ja Linuxille. Muokkaa kuvia, luo tasoja käyttäviä suunnitelmia ja avaa tai tallenna PSD-tiedostoja.",
        "fr": "Un éditeur photo de bureau gratuit pour macOS, Windows et Linux. Modifiez des photos, créez des compositions avec des calques et ouvrez ou enregistrez des fichiers PSD.",
        "ga": "Eagarthóir grianghraf deisce saor in aisce do macOS, Windows agus Linux. Cuir grianghraif in eagar, cruthaigh dearaí sraitheacha agus oscail nó sábháil comhaid PSD.",
        "he": "עורך תמונות חינמי לשולחן העבודה עבור macOS, Windows ו-Linux. ערכו תמונות, צרו עיצובים בשכבות ופתחו או שמרו קובצי PSD.",
        "hi": "macOS, Windows और Linux के लिए एक निःशुल्क डेस्कटॉप फोटो एडिटर। फोटो संपादित करें, लेयर्ड डिज़ाइन बनाएं और PSD फ़ाइलें खोलें या सहेजें।",
        "hr": "Besplatan stolni uređivač fotografija za macOS, Windows i Linux. Uređujte fotografije, stvarajte slojevite dizajne te otvarajte ili spremajte PSD datoteke.",
        "hu": "Ingyenes asztali fotószerkesztő macOS, Windows és Linux rendszerekhez. Szerkesszen fényképeket, készítsen réteges terveket, valamint nyisson meg vagy mentsen PSD-fájlokat.",
        "hy": "Անվճար աշխատասեղանի լուսանկարների խմբագրիչ macOS-ի, Windows-ի և Linux-ի համար։ Խմբագրեք լուսանկարներ, ստեղծեք շերտավոր ձևավորումներ և բացեք կամ պահպանեք PSD ֆայլեր։",
        "id": "Editor foto desktop gratis untuk macOS, Windows, dan Linux. Edit foto, buat desain berlapis, serta buka atau simpan file PSD.",
        "is": "Ókeypis myndvinnsluforrit fyrir macOS, Windows og Linux. Breyttu myndum, búðu til hönnun með lögum og opnaðu eða vistaðu PSD-skrár.",
        "it": "Un editor di foto desktop gratuito per macOS, Windows e Linux. Modifica foto, crea progetti a livelli e apri o salva file PSD.",
        "ja": "macOS、Windows、Linux向けの無料デスクトップ写真編集ソフト。写真の編集、レイヤーを使ったデザインの作成、PSDファイルの読み込みや保存ができます。",
        "ka": "უფასო დესკტოპ ფოტო რედაქტორი macOS-ისთვის, Windows-ისთვის და Linux-ისთვის. დაარედაქტირეთ ფოტოები, შექმენით ფენებიანი დიზაინები და გახსენით ან შეინახეთ PSD ფაილები.",
        "km": "កម្មវិធីកែរូបថតលើកុំព្យូទ័រឥតគិតថ្លៃសម្រាប់ macOS, Windows និង Linux។ កែរូបថត បង្កើតការរចនាជាស្រទាប់ និងបើកឬរក្សាទុកឯកសារ PSD។",
        "ko": "macOS, Windows 및 Linux용 무료 데스크톱 사진 편집기입니다. 사진을 편집하고 레이어 기반 디자인을 만들며 PSD 파일을 열거나 저장할 수 있습니다.",
        "lo": "ໂປຣແກຣມແກ້ໄຂຮູບພາບເດສທັອບຟຣີສຳລັບ macOS, Windows ແລະ Linux. ແກ້ໄຂຮູບພາບ, ສ້າງງານອອກແບບແບບຫຼາຍຊັ້ນ ແລະເປີດຫຼືບັນທຶກໄຟລ໌ PSD.",
        "lt": "Nemokama darbalaukio nuotraukų redagavimo programa, skirta „macOS“, „Windows“ ir „Linux“. Redaguokite nuotraukas, kurkite daugiasluoksnius dizainus ir atidarykite arba išsaugokite PSD failus.",
        "lv": "Bezmaksas darbvirsmas fotoattēlu redaktors operētājsistēmām macOS, Windows un Linux. Rediģējiet fotoattēlus, veidojiet daudzslāņu dizainus un atveriet vai saglabājiet PSD failus.",
        "mn": "macOS, Windows болон Linux-д зориулсан үнэгүй десктоп зураг засварлагч. Зураг засварлах, давхаргатай дизайн үүсгэх, PSD файл нээх эсвэл хадгалах боломжтой.",
        "ms": "Penyunting foto desktop percuma untuk macOS, Windows dan Linux. Edit foto, cipta reka bentuk berlapis serta buka atau simpan fail PSD.",
        "my": "macOS၊ Windows နှင့် Linux အတွက် အခမဲ့ desktop ဓာတ်ပုံတည်းဖြတ်စနစ်။ ဓာတ်ပုံများကို တည်းဖြတ်ခြင်း၊ အလွှာများပါသော ဒီဇိုင်းများဖန်တီးခြင်းနှင့် PSD ဖိုင်များကို ဖွင့်ခြင်း သို့မဟုတ် သိမ်းဆည်းခြင်း ပြုလုပ်နိုင်သည်။",
        "nb": "Et gratis bilderedigeringsprogram for macOS, Windows og Linux. Rediger bilder, lag design med flere lag, og åpne eller lagre PSD-filer.",
        "ne": "macOS, Windows र Linux का लागि निःशुल्क डेस्कटप फोटो सम्पादक। फोटो सम्पादन गर्नुहोस्, तहयुक्त डिजाइनहरू सिर्जना गर्नुहोस् र PSD फाइलहरू खोल्नुहोस् वा बचत गर्नुहोस्।",
        "nl": "Een gratis fotobewerker voor macOS, Windows en Linux. Bewerk foto's, maak ontwerpen met lagen en open of bewaar PSD-bestanden.",
        "pl": "Bezpłatny desktopowy edytor zdjęć dla macOS, Windows i Linux. Edytuj zdjęcia, twórz projekty z warstwami oraz otwieraj lub zapisuj pliki PSD.",
        "pt": "Um editor de fotos gratuito para desktop no macOS, Windows e Linux. Edite fotos, crie designs em camadas e abra ou salve arquivos PSD.",
        "ro": "Un editor foto desktop gratuit pentru macOS, Windows și Linux. Editați fotografii, creați designuri cu straturi și deschideți sau salvați fișiere PSD.",
        "ru": "Бесплатный настольный фоторедактор для macOS, Windows и Linux. Редактируйте фотографии, создавайте многослойные дизайны и открывайте или сохраняйте файлы PSD.",
        "sk": "Bezplatný desktopový editor fotografií pre macOS, Windows a Linux. Upravujte fotografie, vytvárajte návrhy vo vrstvách a otvárajte alebo ukladajte súbory PSD.",
        "sl": "Brezplačen namizni urejevalnik fotografij za macOS, Windows in Linux. Urejajte fotografije, ustvarjajte večplastne zasnove ter odpirajte ali shranjujte datoteke PSD.",
        "sq": "Një redaktues falas fotografish për desktop për macOS, Windows dhe Linux. Redaktoni foto, krijoni dizajne me shtresa dhe hapni ose ruani skedarë PSD.",
        "sr": "Бесплатан десктоп уређивач фотографија за macOS, Windows и Linux. Уређујте фотографије, правите слојевите дизајне и отварајте или чувајте PSD датотеке.",
        "sv": "En kostnadsfri fotoredigerare för macOS, Windows och Linux. Redigera foton, skapa design med lager och öppna eller spara PSD-filer.",
        "sw": "Kihariri cha picha cha mezani bila malipo kwa macOS, Windows na Linux. Hariri picha, unda miundo yenye tabaka na ufungue au uhifadhi faili za PSD.",
        "ta": "macOS, Windows மற்றும் Linux-க்கான இலவச டெஸ்க்டாப் புகைப்படத் திருத்தி. புகைப்படங்களைத் திருத்தவும், அடுக்குகளைக் கொண்ட வடிவமைப்புகளை உருவாக்கவும், PSD கோப்புகளைத் திறக்கவும் அல்லது சேமிக்கவும்.",
        "tg": "Муҳаррири ройгони аксҳо барои мизи кории macOS, Windows ва Linux. Аксҳоро таҳрир кунед, тарҳҳои қабатдор созед ва файлҳои PSD-ро кушоед ё захира кунед.",
        "th": "โปรแกรมแก้ไขรูปภาพบนเดสก์ท็อปฟรีสำหรับ macOS, Windows และ Linux แก้ไขรูปภาพ สร้างงานออกแบบแบบหลายเลเยอร์ และเปิดหรือบันทึกไฟล์ PSD",
        "tl": "Libreng desktop photo editor para sa macOS, Windows, at Linux. Mag-edit ng mga larawan, gumawa ng mga layered na disenyo, at magbukas o mag-save ng mga PSD file.",
        "tr": "macOS, Windows ve Linux için ücretsiz bir masaüstü fotoğraf düzenleyicisi. Fotoğrafları düzenleyin, katmanlı tasarımlar oluşturun ve PSD dosyalarını açın veya kaydedin.",
        "uk": "Безкоштовний настільний фоторедактор для macOS, Windows і Linux. Редагуйте фотографії, створюйте багатошарові дизайни та відкривайте або зберігайте файли PSD.",
        "ur": "macOS، Windows اور Linux کے لیے مفت ڈیسک ٹاپ فوٹو ایڈیٹر۔ تصاویر میں ترمیم کریں، تہہ دار ڈیزائن بنائیں اور PSD فائلیں کھولیں یا محفوظ کریں۔",
        "uz": "macOS, Windows va Linux uchun bepul ish stoli foto muharriri. Suratlarni tahrirlang, qatlamli dizaynlar yarating va PSD fayllarini oching yoki saqlang.",
        "vi": "Trình chỉnh sửa ảnh miễn phí trên máy tính dành cho macOS, Windows và Linux. Chỉnh sửa ảnh, tạo thiết kế nhiều lớp và mở hoặc lưu tệp PSD.",
        "zh": "适用于 macOS、Windows 和 Linux 的免费桌面照片编辑器。编辑照片、创建分层设计，并打开或保存 PSD 文件。"
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

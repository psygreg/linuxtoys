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
    "appstream_initial_building": {
        "am": "የመጀመሪያውን AppStream ካታሎግ በመገንባት ላይ።\nይህ ጥቂት ሰከንዶች ሊወስድ ይችላል...",
        "ar": "جارٍ إنشاء كتالوج AppStream الأولي.\nقد يستغرق هذا بضع ثوانٍ...",
        "az": "İlkin AppStream kataloqu yaradılır.\nBu bir neçə saniyə çəkə bilər...",
        "bg": "Създаване на първоначалния AppStream каталог.\nТова може да отнеме няколко секунди...",
        "bn": "প্রাথমিক AppStream ক্যাটালগ তৈরি করা হচ্ছে।\nএতে কয়েক সেকেন্ড সময় লাগতে পারে...",
        "bs": "Izrada početnog AppStream kataloga.\nOvo može potrajati nekoliko sekundi...",
        "cs": "Vytváří se počáteční katalog AppStream.\nMůže to trvat několik sekund...",
        "da": "Opbygger det indledende AppStream-katalog.\nDette kan tage et par sekunder...",
        "de": "Der anfängliche AppStream-Katalog wird erstellt.\nDies kann einige Sekunden dauern...",
        "el": "Δημιουργία του αρχικού καταλόγου AppStream.\nΑυτό μπορεί να διαρκέσει μερικά δευτερόλεπτα...",
        "es": "Creando el catálogo inicial de AppStream.\nEsto puede tardar unos segundos...",
        "et": "Esialgse AppStreami kataloogi loomine.\nSee võib võtta mõne sekundi...",
        "fa": "در حال ساخت فهرست اولیه AppStream.\nاین کار ممکن است چند ثانیه طول بکشد...",
        "fi": "Luodaan alkuperäistä AppStream-luetteloa.\nTämä voi kestää muutaman sekunnin...",
        "fr": "Création du catalogue AppStream initial.\nCela peut prendre quelques secondes...",
        "ga": "Catalóg tosaigh AppStream á chruthú.\nSeans go dtógfaidh sé seo cúpla soicind...",
        "he": "בונה את קטלוג AppStream הראשוני.\nפעולה זו עשויה להימשך מספר שניות...",
        "hi": "प्रारंभिक AppStream कैटलॉग बनाया जा रहा है।\nइसमें कुछ सेकंड लग सकते हैं...",
        "hr": "Izrada početnog AppStream kataloga.\nOvo može potrajati nekoliko sekundi...",
        "hu": "A kezdeti AppStream-katalógus létrehozása.\nEz néhány másodpercet vehet igénybe...",
        "hy": "Ստեղծվում է սկզբնական AppStream կատալոգը։\nՍա կարող է տևել մի քանի վայրկյան...",
        "id": "Membangun katalog AppStream awal.\nIni mungkin memerlukan waktu beberapa detik...",
        "is": "Byggi upp upphaflegan AppStream-vörulista.\nÞetta gæti tekið nokkrar sekúndur...",
        "it": "Creazione del catalogo AppStream iniziale.\nPotrebbero essere necessari alcuni secondi...",
        "ja": "初期 AppStream カタログを構築しています。\n数秒かかる場合があります...",
        "ka": "მიმდინარეობს საწყისი AppStream კატალოგის შექმნა.\nამას შეიძლება რამდენიმე წამი დასჭირდეს...",
        "km": "កំពុងបង្កើតកាតាឡុក AppStream ដំបូង។\nវាអាចចំណាយពេលពីរបីវិនាទី...",
        "ko": "초기 AppStream 카탈로그를 생성하는 중입니다.\n몇 초 정도 걸릴 수 있습니다...",
        "lo": "ກຳລັງສ້າງລາຍການ AppStream ເບື້ອງຕົ້ນ.\nອາດໃຊ້ເວລາສອງສາມວິນາທີ...",
        "lt": "Kuriamas pradinis AppStream katalogas.\nTai gali užtrukti kelias sekundes...",
        "lv": "Tiek veidots sākotnējais AppStream katalogs.\nTas var aizņemt dažas sekundes...",
        "mn": "Анхны AppStream каталогийг үүсгэж байна.\nҮүнд хэдэн секунд зарцуулагдаж магадгүй...",
        "ms": "Membina katalog AppStream awal.\nIni mungkin mengambil masa beberapa saat...",
        "my": "ကနဦး AppStream ကတ်တလောက်ကို တည်ဆောက်နေသည်။\nစက္ကန့်အနည်းငယ် ကြာနိုင်သည်...",
        "nb": "Bygger den første AppStream-katalogen.\nDette kan ta noen sekunder...",
        "ne": "प्रारम्भिक AppStream क्याटलग निर्माण हुँदैछ।\nयसले केही सेकेन्ड लिन सक्छ...",
        "nl": "De eerste AppStream-catalogus wordt opgebouwd.\nDit kan enkele seconden duren...",
        "pl": "Tworzenie początkowego katalogu AppStream.\nMoże to potrwać kilka sekund...",
        "pt": "Criando o catálogo inicial do AppStream.\nIsso pode levar alguns segundos...",
        "ro": "Se creează catalogul AppStream inițial.\nAcest lucru poate dura câteva secunde...",
        "ru": "Создание начального каталога AppStream.\nЭто может занять несколько секунд...",
        "sk": "Vytvára sa počiatočný katalóg AppStream.\nMôže to trvať niekoľko sekúnd...",
        "sl": "Ustvarjanje začetnega kataloga AppStream.\nTo lahko traja nekaj sekund...",
        "sq": "Po ndërtohet katalogu fillestar AppStream.\nKjo mund të zgjasë disa sekonda...",
        "sr": "Креирање почетног AppStream каталога.\nОво може потрајати неколико секунди...",
        "sv": "Bygger den inledande AppStream-katalogen.\nDetta kan ta några sekunder...",
        "sw": "Inaunda katalogi ya awali ya AppStream.\nHii inaweza kuchukua sekunde chache...",
        "ta": "ஆரம்ப AppStream பட்டியல் உருவாக்கப்படுகிறது.\nஇதற்கு சில வினாடிகள் ஆகலாம்...",
        "tg": "Каталоги ибтидоии AppStream сохта мешавад.\nИн метавонад чанд сония вақт гирад...",
        "th": "กำลังสร้างแค็ตตาล็อก AppStream เริ่มต้น\nซึ่งอาจใช้เวลาสักครู่...",
        "tl": "Binubuo ang paunang katalogo ng AppStream.\nMaaaring tumagal ito nang ilang segundo...",
        "tr": "İlk AppStream kataloğu oluşturuluyor.\nBu işlem birkaç saniye sürebilir...",
        "uk": "Створення початкового каталогу AppStream.\nЦе може зайняти кілька секунд...",
        "ur": "ابتدائی AppStream کیٹلاگ بنایا جا رہا ہے۔\nاس میں چند سیکنڈ لگ سکتے ہیں...",
        "uz": "Dastlabki AppStream katalogi yaratilmoqda.\nBu bir necha soniya vaqt olishi mumkin...",
        "vi": "Đang tạo danh mục AppStream ban đầu.\nQuá trình này có thể mất vài giây...",
        "zh": "正在构建初始 AppStream 目录。\n这可能需要几秒钟..."
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

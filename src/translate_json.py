import json
import os

# Directory containing the language files
lang_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "p3/libs/lang/")

# Translations dictionary: key -> {lang_code: translation}
translations = {
    "package_view_external_warning": {
        "am": "ይህ ጥቅል ከውጫዊ ፋይል የመጣ ነው። ከሚያምኗቸው ምንጮች የመጡ ጥቅሎችን ብቻ ይጫኑ።",
        "ar": "تأتي هذه الحزمة من ملف خارجي. ثبّت الحزم فقط من المصادر التي تثق بها.",
        "az": "Bu paket xarici fayldan gəlir. Yalnız etibar etdiyiniz mənbələrdən olan paketləri quraşdırın.",
        "bg": "Този пакет идва от външен файл. Инсталирайте пакети само от източници, на които имате доверие.",
        "bn": "এই প্যাকেজটি একটি বাহ্যিক ফাইল থেকে এসেছে। শুধুমাত্র বিশ্বস্ত উৎসের প্যাকেজ ইনস্টল করুন।",
        "bs": "Ovaj paket dolazi iz vanjske datoteke. Instalirajte samo pakete iz izvora kojima vjerujete.",
        "cs": "Tento balíček pochází z externího souboru. Instalujte pouze balíčky ze zdrojů, kterým důvěřujete.",
        "da": "Denne pakke kommer fra en ekstern fil. Installér kun pakker fra kilder, du har tillid til.",
        "de": "Dieses Paket stammt aus einer externen Datei. Installieren Sie nur Pakete aus Quellen, denen Sie vertrauen.",
        "el": "Αυτό το πακέτο προέρχεται από εξωτερικό αρχείο. Εγκαθιστάτε πακέτα μόνο από πηγές που εμπιστεύεστε.",
        "es": "Este paquete proviene de un archivo externo. Instala únicamente paquetes de fuentes en las que confíes.",
        "et": "See pakett pärineb välisest failist. Paigaldage pakette ainult allikatest, mida usaldate.",
        "fa": "این بسته از یک فایل خارجی می‌آید. فقط بسته‌هایی را از منابع مورد اعتماد خود نصب کنید.",
        "fi": "Tämä paketti tulee ulkoisesta tiedostosta. Asenna paketteja vain lähteistä, joihin luotat.",
        "fr": "Ce paquet provient d’un fichier externe. N’installez que des paquets provenant de sources auxquelles vous faites confiance.",
        "ga": "Tagann an pacáiste seo ó chomhad seachtrach. Ná suiteáil ach pacáistí ó fhoinsí a bhfuil muinín agat astu.",
        "he": "חבילה זו מגיעה מקובץ חיצוני. התקינו חבילות רק ממקורות שאתם סומכים עליהם.",
        "hi": "यह पैकेज एक बाहरी फ़ाइल से आता है। केवल उन स्रोतों से पैकेज इंस्टॉल करें जिन पर आप भरोसा करते हैं।",
        "hr": "Ovaj paket dolazi iz vanjske datoteke. Instalirajte samo pakete iz izvora kojima vjerujete.",
        "hu": "Ez a csomag külső fájlból származik. Csak megbízható forrásból származó csomagokat telepítsen.",
        "hy": "Այս փաթեթը գալիս է արտաքին ֆայլից։ Տեղադրեք փաթեթներ միայն այն աղբյուրներից, որոնց վստահում եք։",
        "id": "Paket ini berasal dari file eksternal. Instal hanya paket dari sumber yang Anda percayai.",
        "is": "Þessi pakki kemur úr utanaðkomandi skrá. Settu aðeins upp pakka frá heimildum sem þú treystir.",
        "it": "Questo pacchetto proviene da un file esterno. Installa solo pacchetti provenienti da fonti attendibili.",
        "ja": "このパッケージは外部ファイルから取得されています。信頼できる提供元のパッケージのみをインストールしてください。",
        "ka": "ეს პაკეტი გარე ფაილიდან მოდის. დააინსტალირეთ პაკეტები მხოლოდ იმ წყაროებიდან, რომლებსაც ენდობით.",
        "km": "កញ្ចប់នេះមកពីឯកសារខាងក្រៅ។ ដំឡើងតែកញ្ចប់ពីប្រភពដែលអ្នកទុកចិត្តប៉ុណ្ណោះ។",
        "ko": "이 패키지는 외부 파일에서 가져왔습니다. 신뢰할 수 있는 출처의 패키지만 설치하세요.",
        "lo": "ແພັກເກດນີ້ມາຈາກໄຟລ໌ພາຍນອກ. ຕິດຕັ້ງສະເພາະແພັກເກດຈາກແຫຼ່ງທີ່ທ່ານໄວ້ໃຈເທົ່ານັ້ນ.",
        "lt": "Šis paketas yra iš išorinio failo. Diekite tik paketus iš šaltinių, kuriais pasitikite.",
        "lv": "Šī pakotne nāk no ārēja faila. Instalējiet pakotnes tikai no avotiem, kuriem uzticaties.",
        "mn": "Энэ багц гадаад файлаас ирсэн. Зөвхөн итгэдэг эх сурвалжийн багцуудыг суулгана уу.",
        "ms": "Pakej ini berasal daripada fail luaran. Pasang hanya pakej daripada sumber yang anda percayai.",
        "my": "ဤ package သည် ပြင်ပဖိုင်တစ်ခုမှ လာသည်။ သင်ယုံကြည်ရသော ရင်းမြစ်များမှ package များကိုသာ ထည့်သွင်းပါ။",
        "nb": "Denne pakken kommer fra en ekstern fil. Installer bare pakker fra kilder du stoler på.",
        "ne": "यो प्याकेज बाह्य फाइलबाट आएको हो। तपाईंले विश्वास गर्ने स्रोतका प्याकेजहरू मात्र स्थापना गर्नुहोस्।",
        "nl": "Dit pakket is afkomstig uit een extern bestand. Installeer alleen pakketten uit bronnen die u vertrouwt.",
        "pl": "Ten pakiet pochodzi z zewnętrznego pliku. Instaluj tylko pakiety ze źródeł, którym ufasz.",
        "pt": "Este pacote vem de um arquivo externo. Instale apenas pacotes de fontes em que você confia.",
        "ro": "Acest pachet provine dintr-un fișier extern. Instalați numai pachete din surse în care aveți încredere.",
        "ru": "Этот пакет получен из внешнего файла. Устанавливайте пакеты только из источников, которым доверяете.",
        "sk": "Tento balík pochádza z externého súboru. Inštalujte iba balíky zo zdrojov, ktorým dôverujete.",
        "sl": "Ta paket prihaja iz zunanje datoteke. Nameščajte samo pakete iz virov, ki jim zaupate.",
        "sq": "Kjo paketë vjen nga një skedar i jashtëm. Instaloni vetëm paketa nga burime të cilave u besoni.",
        "sr": "Овај пакет долази из спољне датотеке. Инсталирајте само пакете из извора којима верујете.",
        "sv": "Det här paketet kommer från en extern fil. Installera endast paket från källor du litar på.",
        "sw": "Kifurushi hiki kinatoka kwenye faili ya nje. Sakinisha vifurushi kutoka vyanzo unavyoviamini pekee.",
        "ta": "இந்த தொகுப்பு வெளிப்புறக் கோப்பிலிருந்து வருகிறது. நீங்கள் நம்பும் மூலங்களிலிருந்து வரும் தொகுப்புகளை மட்டுமே நிறுவவும்.",
        "tg": "Ин баста аз файли беруна меояд. Танҳо бастаҳоро аз манбаъҳое насб кунед, ки ба онҳо эътимод доред.",
        "th": "แพ็กเกจนี้มาจากไฟล์ภายนอก โปรดติดตั้งเฉพาะแพ็กเกจจากแหล่งที่คุณเชื่อถือเท่านั้น",
        "tl": "Ang package na ito ay mula sa isang external na file. Mag-install lamang ng mga package mula sa mga source na pinagkakatiwalaan mo.",
        "tr": "Bu paket harici bir dosyadan geliyor. Yalnızca güvendiğiniz kaynaklardan gelen paketleri yükleyin.",
        "uk": "Цей пакет походить із зовнішнього файлу. Встановлюйте пакети лише з джерел, яким довіряєте.",
        "ur": "یہ پیکیج ایک بیرونی فائل سے آیا ہے۔ صرف ان ذرائع سے پیکیجز انسٹال کریں جن پر آپ اعتماد کرتے ہیں۔",
        "uz": "Bu paket tashqi fayldan keladi. Faqat ishonchli manbalardan olingan paketlarni o'rnating.",
        "vi": "Gói này đến từ một tệp bên ngoài. Chỉ cài đặt các gói từ những nguồn mà bạn tin cậy.",
        "zh": "此软件包来自外部文件。请仅安装来自您信任来源的软件包。"
    },
"package_view_format_snap": {
    "am": "የSnap ጥቅል",
    "ar": "حزمة Snap",
    "az": "Snap paketi",
    "bg": "Snap пакет",
    "bn": "Snap প্যাকেজ",
    "bs": "Snap paket",
    "cs": "Balíček Snap",
    "da": "Snap-pakke",
    "de": "Snap-Paket",
    "el": "Πακέτο Snap",
    "es": "Paquete Snap",
    "et": "Snapi pakett",
    "fa": "بسته Snap",
    "fi": "Snap-paketti",
    "fr": "Paquet Snap",
    "ga": "Pacáiste Snap",
    "he": "חבילת Snap",
    "hi": "Snap पैकेज",
    "hr": "Snap paket",
    "hu": "Snap-csomag",
    "hy": "Snap փաթեթ",
    "id": "Paket Snap",
    "is": "Snap-pakki",
    "it": "Pacchetto Snap",
    "ja": "Snap パッケージ",
    "ka": "Snap პაკეტი",
    "km": "កញ្ចប់ Snap",
    "ko": "Snap 패키지",
    "lo": "ແພັກເກດ Snap",
    "lt": "Snap paketas",
    "lv": "Snap pakotne",
    "mn": "Snap багц",
    "ms": "Pakej Snap",
    "my": "Snap package",
    "nb": "Snap-pakke",
    "ne": "Snap प्याकेज",
    "nl": "Snap-pakket",
    "pl": "Pakiet Snap",
    "pt": "Pacote Snap",
    "ro": "Pachet Snap",
    "ru": "Пакет Snap",
    "sk": "Balík Snap",
    "sl": "Paket Snap",
    "sq": "Paketë Snap",
    "sr": "Snap пакет",
    "sv": "Snap-paket",
    "sw": "Kifurushi cha Snap",
    "ta": "Snap தொகுப்பு",
    "tg": "Бастаи Snap",
    "th": "แพ็กเกจ Snap",
    "tl": "Snap package",
    "tr": "Snap paketi",
    "uk": "Пакет Snap",
    "ur": "Snap پیکیج",
    "uz": "Snap paketi",
    "vi": "Gói Snap",
    "zh": "Snap 软件包"
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

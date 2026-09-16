import json
import os

# Directory containing the language files
lang_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "p3/libs/lang/")

# Translations dictionary: key -> {lang_code: translation}
translations = {
    "quarto_desc": {
        "am": "ክፍት ምንጭ የሳይንሳዊ እና ቴክኒካዊ ህትመት ስርዓት።",
        "ar": "نظام مفتوح المصدر للنشر العلمي والتقني.",
        "az": "Açıq mənbəli elmi və texniki nəşr sistemi.",
        "bg": "Система с отворен код за научно и техническо публикуване.",
        "bn": "বৈজ্ঞানিক ও প্রযুক্তিগত প্রকাশনার জন্য একটি ওপেন সোর্স সিস্টেম।",
        "bs": "Sistem otvorenog koda za naučno i tehničko objavljivanje.",
        "cs": "Open source systém pro vědecké a technické publikování.",
        "da": "Et open source-system til videnskabelig og teknisk publicering.",
        "de": "Ein Open-Source-System für wissenschaftliches und technisches Publizieren.",
        "el": "Ένα σύστημα ανοιχτού κώδικα για επιστημονικές και τεχνικές δημοσιεύσεις.",
        "es": "Un sistema de código abierto para publicaciones científicas y técnicas.",
        "et": "Avatud lähtekoodiga teadusliku ja tehnilise avaldamise süsteem.",
        "fa": "یک سیستم متن‌باز برای انتشار علمی و فنی.",
        "fi": "Avoimen lähdekoodin järjestelmä tieteelliseen ja tekniseen julkaisemiseen.",
        "fr": "Un système open source de publication scientifique et technique.",
        "ga": "Córas foinse oscailte le haghaidh foilsiú eolaíoch agus teicniúil.",
        "he": "מערכת בקוד פתוח לפרסום מדעי וטכני.",
        "hi": "वैज्ञानिक और तकनीकी प्रकाशन के लिए एक ओपन सोर्स सिस्टम।",
        "hr": "Sustav otvorenog koda za znanstveno i tehničko objavljivanje.",
        "hu": "Nyílt forráskódú rendszer tudományos és műszaki publikáláshoz.",
        "hy": "Բաց կոդով համակարգ գիտական և տեխնիկական հրապարակումների համար։",
        "id": "Sistem sumber terbuka untuk penerbitan ilmiah dan teknis.",
        "is": "Opið kerfi fyrir vísindalega og tæknilega útgáfu.",
        "it": "Un sistema open source per la pubblicazione scientifica e tecnica.",
        "ja": "科学・技術文書を公開するためのオープンソースシステムです。",
        "ka": "ღია კოდის სისტემა სამეცნიერო და ტექნიკური პუბლიკაციებისთვის.",
        "km": "ប្រព័ន្ធប្រភពបើកចំហសម្រាប់ការបោះពុម្ពផ្សាយបែបវិទ្យាសាស្ត្រ និងបច្ចេកទេស។",
        "ko": "과학 및 기술 출판을 위한 오픈 소스 시스템입니다.",
        "lo": "ລະບົບໂອເພນຊອດສຳລັບການເຜີຍແຜ່ທາງວິທະຍາສາດ ແລະ ເຕັກນິກ.",
        "lt": "Atvirojo kodo sistema mokslinėms ir techninėms publikacijoms.",
        "lv": "Atvērtā pirmkoda sistēma zinātniskai un tehniskai publicēšanai.",
        "mn": "Шинжлэх ухаан, техникийн нийтлэл хэвлэн нийтлэх нээлттэй эхийн систем.",
        "ms": "Sistem sumber terbuka untuk penerbitan saintifik dan teknikal.",
        "my": "သိပ္ပံနှင့် နည်းပညာဆိုင်ရာ ထုတ်ဝေမှုများအတွက် open source စနစ်။",
        "nb": "Et system med åpen kildekode for vitenskapelig og teknisk publisering.",
        "ne": "वैज्ञानिक तथा प्राविधिक प्रकाशनका लागि खुला स्रोत प्रणाली।",
        "nl": "Een opensourcesysteem voor wetenschappelijke en technische publicaties.",
        "pl": "System open source do publikacji naukowych i technicznych.",
        "pt": "Um sistema de código aberto para publicação científica e técnica.",
        "ro": "Un sistem open source pentru publicare științifică și tehnică.",
        "ru": "Система с открытым исходным кодом для научных и технических публикаций.",
        "sk": "Open source systém na vedecké a technické publikovanie.",
        "sl": "Odprtokodni sistem za znanstveno in tehnično objavljanje.",
        "sq": "Një sistem me burim të hapur për publikime shkencore dhe teknike.",
        "sr": "Систем отвореног кода за научно и техничко објављивање.",
        "sv": "Ett system med öppen källkod för vetenskaplig och teknisk publicering.",
        "sw": "Mfumo wa chanzo huria kwa uchapishaji wa kisayansi na kiufundi.",
        "ta": "அறிவியல் மற்றும் தொழில்நுட்ப வெளியீட்டிற்கான திறந்த மூல அமைப்பு.",
        "tg": "Системаи кушодаасос барои нашри илмӣ ва техникӣ.",
        "th": "ระบบโอเพนซอร์สสำหรับการเผยแพร่ผลงานทางวิทยาศาสตร์และเทคนิค",
        "tl": "Isang open source na sistema para sa siyentipiko at teknikal na paglalathala.",
        "tr": "Bilimsel ve teknik yayıncılık için açık kaynaklı bir sistem.",
        "uk": "Система з відкритим кодом для наукових і технічних публікацій.",
        "ur": "سائنسی اور تکنیکی اشاعت کے لیے ایک اوپن سورس نظام۔",
        "uz": "Ilmiy va texnik nashrlar uchun ochiq kodli tizim.",
        "vi": "Hệ thống mã nguồn mở dành cho xuất bản khoa học và kỹ thuật.",
        "zh": "一个用于科学和技术出版的开源系统。"
    },

    "rbase_desc": {
        "am": "ለስታቲስቲካዊ ስሌት እና ግራፊክስ ነፃ የሶፍትዌር አካባቢ።",
        "ar": "بيئة برمجية حرة للحوسبة الإحصائية والرسوميات.",
        "az": "Statistik hesablamalar və qrafika üçün pulsuz proqram təminatı mühiti.",
        "bg": "Свободна софтуерна среда за статистически изчисления и графика.",
        "bn": "পরিসংখ্যানগত গণনা ও গ্রাফিক্সের জন্য একটি মুক্ত সফটওয়্যার পরিবেশ।",
        "bs": "Slobodno softversko okruženje za statističko računanje i grafiku.",
        "cs": "Svobodné softwarové prostředí pro statistické výpočty a grafiku.",
        "da": "Et frit softwaremiljø til statistiske beregninger og grafik.",
        "de": "Eine freie Softwareumgebung für statistische Berechnungen und Grafiken.",
        "el": "Ένα περιβάλλον ελεύθερου λογισμικού για στατιστικούς υπολογισμούς και γραφικά.",
        "es": "Un entorno de software libre para computación estadística y gráficos.",
        "et": "Vaba tarkvarakeskkond statistilisteks arvutusteks ja graafikaks.",
        "fa": "یک محیط نرم‌افزاری آزاد برای محاسبات آماری و گرافیک.",
        "fi": "Vapaa ohjelmistoympäristö tilastolliseen laskentaan ja grafiikkaan.",
        "fr": "Un environnement logiciel libre pour le calcul statistique et les graphiques.",
        "ga": "Timpeallacht bogearraí saor in aisce le haghaidh ríomhaireacht staitistiúil agus grafaicí.",
        "he": "סביבת תוכנה חופשית לחישובים סטטיסטיים ולגרפיקה.",
        "hi": "सांख्यिकीय कंप्यूटिंग और ग्राफ़िक्स के लिए एक मुक्त सॉफ़्टवेयर वातावरण।",
        "hr": "Slobodno softversko okruženje za statističko računanje i grafiku.",
        "hu": "Szabad szoftverkörnyezet statisztikai számításokhoz és grafikákhoz.",
        "hy": "Ազատ ծրագրային միջավայր վիճակագրական հաշվարկների և գրաֆիկայի համար։",
        "id": "Lingkungan perangkat lunak bebas untuk komputasi statistik dan grafis.",
        "is": "Frjálst hugbúnaðarumhverfi fyrir tölfræðilega útreikninga og grafík.",
        "it": "Un ambiente software libero per il calcolo statistico e la grafica.",
        "ja": "統計計算とグラフィックスのためのフリーソフトウェア環境です。",
        "ka": "თავისუფალი პროგრამული გარემო სტატისტიკური გამოთვლებისა და გრაფიკისთვის.",
        "km": "បរិស្ថានកម្មវិធីសេរីសម្រាប់ការគណនាស្ថិតិ និងក្រាហ្វិក។",
        "ko": "통계 계산 및 그래픽을 위한 자유 소프트웨어 환경입니다.",
        "lo": "ສະພາບແວດລ້ອມຊອບແວເສລີສຳລັບການຄຳນວນທາງສະຖິຕິ ແລະ ກຣາຟິກ.",
        "lt": "Laisvosios programinės įrangos aplinka statistiniams skaičiavimams ir grafikai.",
        "lv": "Brīvās programmatūras vide statistiskajiem aprēķiniem un grafikai.",
        "mn": "Статистик тооцоолол болон графикт зориулсан чөлөөт програм хангамжийн орчин.",
        "ms": "Persekitaran perisian bebas untuk pengkomputeran statistik dan grafik.",
        "my": "စာရင်းအင်းတွက်ချက်မှုနှင့် ဂရပ်ဖစ်များအတွက် အခမဲ့နှင့် လွတ်လပ်သော software environment။",
        "nb": "Et fritt programvaremiljø for statistiske beregninger og grafikk.",
        "ne": "सांख्यिकीय गणना र ग्राफिक्सका लागि स्वतन्त्र सफ्टवेयर वातावरण।",
        "nl": "Een vrije softwareomgeving voor statistische berekeningen en grafieken.",
        "pl": "Wolne środowisko programistyczne do obliczeń statystycznych i grafiki.",
        "pt": "Um ambiente de software livre para computação estatística e gráficos.",
        "ro": "Un mediu software liber pentru calcule statistice și grafică.",
        "ru": "Свободная программная среда для статистических вычислений и графики.",
        "sk": "Slobodné softvérové prostredie na štatistické výpočty a grafiku.",
        "sl": "Prosto programsko okolje za statistično računanje in grafiko.",
        "sq": "Një mjedis softuerësh të lirë për llogaritje statistikore dhe grafikë.",
        "sr": "Слободно софтверско окружење за статистичко рачунање и графику.",
        "sv": "En fri programvarumiljö för statistiska beräkningar och grafik.",
        "sw": "Mazingira ya programu huru kwa ukokotoaji wa takwimu na michoro.",
        "ta": "புள்ளிவிவரக் கணக்கீடு மற்றும் வரைகலைக்கான கட்டற்ற மென்பொருள் சூழல்.",
        "tg": "Муҳити нармафзори озод барои ҳисоббарориҳои оморӣ ва графика.",
        "th": "สภาพแวดล้อมซอฟต์แวร์เสรีสำหรับการคำนวณทางสถิติและกราฟิก",
        "tl": "Isang malayang software environment para sa statistical computing at graphics.",
        "tr": "İstatistiksel hesaplama ve grafikler için özgür bir yazılım ortamı.",
        "uk": "Вільне програмне середовище для статистичних обчислень і графіки.",
        "ur": "شماریاتی کمپیوٹنگ اور گرافکس کے لیے ایک آزاد سافٹ ویئر ماحول۔",
        "uz": "Statistik hisoblash va grafika uchun erkin dasturiy ta'minot muhiti.",
        "vi": "Môi trường phần mềm tự do dành cho tính toán thống kê và đồ họa.",
        "zh": "用于统计计算和图形处理的自由软件环境。"
    },
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

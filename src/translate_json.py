import json
import os

# Directory containing the language files
lang_dir = '../p3/libs/lang/'

# Translations dictionary: key -> {lang_code: translation}
translations = {
    'damx_desc': {
        'am': 'ለ Acer ጌሚንግ ላፕቶፕ ባህሪያትን እና አፈፃፀም ማስተካከያን ለመቆጣጠር መገልገያ።',
        'ar': 'أداة للتحكم في ميزات الأداء وضبط أداء أجهزة الكمبيوتر المحمولة Acer للألعاب.',
        'az': 'Acer oyun noutbuklarının xüsusiyyətlərini və performans tənzimləməsini idarə etmək üçün yardımçı proqram.',
        'bg': 'Инструмент за управление на функциите и настройката на производителността на геймърски лаптопи Acer.',
        'bn': 'Acer গেমিং ল্যাপটপ বৈশিষ্ট্য এবং পারফরম্যান্স টিউনিং নিয়ন্ত্রণের জন্য ইউটিলিটি।',
        'bs': 'Alat za kontrolu Acer gaming laptop funkcija i podešavanje performansi.',
        'cs': 'Nástroj pro ovládání funkcí a ladění výkonu herních notebooků Acer.',
        'da': 'Værktøj til styring af Acer gaming-laptop funktioner og ydeevneoptimering.',
        'de': 'Dienstprogramm zur Steuerung von Acer Gaming-Laptop-Funktionen und Leistungsoptimierung.',
        'el': 'Βοηθητικό πρόγραμμα για τον έλεγχο χαρακτηριστικών και τη ρύθμιση απόδοσης φορητών υπολογιστών gaming Acer.',
        'es': 'Utilidad para controlar las características y el ajuste de rendimiento de portátiles gaming Acer.',
        'et': 'Tööriist Acer mänguarvutite funktsioonide ja jõudluse häälestamise juhtimiseks.',
        'fa': 'ابزاری برای کنترل ویژگی‌های لپ‌تاپ‌های گیمینگ Acer و تنظیم عملکرد.',
        'fi': 'Työkalu Acer-pelilaptopien ominaisuuksien ja suorituskyvyn säätämiseen.',
        'fr': 'Utilitaire pour contrôler les fonctionnalités et régler les performances des ordinateurs portables gaming Acer.',
        'ga': 'Fóntais chun gnéithe ríomhaire glúine cearrbhachais Acer agus tiúnadh feidhmíochta a rialú.',
        'he': 'כלי עזר לשליטה בתכונות מחשבים ניידים לגיימינג של Acer וכיוון ביצועים.',
        'hi': 'Acer गेमिंग लैपटॉप सुविधाओं और प्रदर्शन ट्यूनिंग को नियंत्रित करने के लिए उपयोगिता।',
        'hr': 'Alat za kontrolu Acer gaming laptop funkcija i podešavanje performansi.',
        'hu': 'Segédprogram az Acer gaming laptopok funkcióinak vezérléséhez és teljesítményhangolásához.',
        'hy': 'Օգտակարություն Acer խաղային նոութբուքերի հատկությունների և կատարողականության կարգավորման համար։',
        'id': 'Utilitas untuk mengontrol fitur laptop gaming Acer dan penyetelan kinerja.',
        'is': 'Tól til að stjórna Acer leikjatölvu eiginleikum og frammistöðustillingu.',
        'it': 'Utilità per controllare le funzionalità e le prestazioni dei laptop gaming Acer.',
        'ja': 'Acer ゲーミングラップトップの機能とパフォーマンスチューニングを制御するユーティリティ。',
        'ka': 'უტილიტა Acer გეიმინგ ლეპტოპების ფუნქციების და წარმადობის გასწორებისთვის.',
        'km': 'ឧបករណ៍ប្រើប្រាស់សម្រាប់គ្រប់គ្រងលក្ខណៈពិសេស និងការកែលម្អដំណើរការកុំព្យូទ័រយួរដៃហ្គេម Acer។',
        'ko': 'Acer 게이밍 노트북 기능 및 성능 튜닝을 제어하는 유틸리티.',
        'lo': 'ເຄື່ອງມືສໍາລັບຄວບຄຸມຄຸນສົມບັດ ແລະ ການປັບແຕ່ງປະສິດທິພາບຂອງແລັບທັອບເກມ Acer.',
        'lt': 'Įrankis Acer žaidimų nešiojamųjų kompiuterių funkcijoms ir našumo derinimui valdyti.',
        'lv': 'Utilīta Acer spēļu klēpjdatoru funkciju un veiktspējas regulēšanas kontrolei.',
        'mn': 'Acer гейминг зөөврийн компьютерийн онцлогууд болон гүйцэтгэлийг тохируулах хэрэгсэл.',
        'ms': 'Utiliti untuk mengawal ciri laptop gaming Acer dan penalaan prestasi.',
        'my': 'Acer ဂိမ်းလက်ပ်တော့ပ် လုပ်ဆောင်ချက်များနှင့် စွမ်းဆောင်ရည် ညှိနှိုင်းမှုကို ထိန်းချုပ်ရန် အသုံးပြုကိရိယာ။',
        'nb': 'Verktøy for å kontrollere Acer gaming-laptop funksjoner og ytelsesoptimering.',
        'ne': 'Acer गेमिङ ल्यापटप सुविधाहरू र प्रदर्शन ट्युनिङ नियन्त्रण गर्नका लागि उपयोगिता।',
        'nl': 'Hulpprogramma voor het beheren van Acer gaming laptop-functies en prestatieafstemming.',
        'pl': 'Narzędzie do kontroli funkcji laptopów gamingowych Acer i dostrajania wydajności.',
        'pt': 'Utilitário para controlar recursos de laptops gaming Acer e ajuste de desempenho.',
        'ro': 'Utilitar pentru controlul funcțiilor laptop-urilor gaming Acer și reglarea performanței.',
        'ru': 'Утилита для управления функциями игровых ноутбуков Acer и настройки производительности.',
        'sk': 'Nástroj na ovládanie funkcií herných notebookov Acer a ladenie výkonu.',
        'sl': 'Pripomoček za nadzor funkcij prenosnikov za igre Acer in uglasitev zmogljivosti.',
        'sq': 'Utilitet për kontrollimin e funksioneve të laptopëve gaming Acer dhe rregullimin e performancës.',
        'sr': 'Алатка за контролу функција Acer геjминг лаптопа и подешавање перформанси.',
        'sv': 'Verktyg för att styra Acer gaming-laptop funktioner och prestandajustering.',
        'sw': 'Kifaa cha kudhibiti vipengele vya kompyuta za kuchezea za Acer na kusasisha utendaji.',
        'ta': 'Acer கேமிங் மடிக்கணினி அம்சங்கள் மற்றும் செயல்திறன் டியூனிங்கை கட்டுப்படுத்த பயன்பாடு.',
        'tg': 'Абзор барои идора кардани хусусиятҳои ноутбук\u200cҳои бозии Acer ва танзими самаранокӣ.',
        'th': 'ยูทิลิตี้สำหรับควบคุมคุณลักษณะแล็ปท็อปเกมมิ่ง Acer และการปรับแต่งประสิทธิภาพ',
        'tl': 'Utility para sa pagkontrol ng mga feature ng Acer gaming laptop at pagpapahusay ng performance.',
        'tr': 'Acer oyun dizüstü bilgisayarı özelliklerini ve performans ayarlarını kontrol etmek için yardımcı program.',
        'uk': 'Утиліта для керування функціями ігрових ноутбуків Acer та налаштування продуктивності.',
        'ur': 'Acer گیمنگ لیپ ٹاپ کی خصوصیات اور کارکردگی کی ٹیوننگ کو کنٹرول کرنے کے لیے یوٹیلیٹی۔',
        'uz': 'Acer o\'yin noutbuklari xususiyatlarini va ishlash sozlamalarini boshqarish uchun dastur.',
        'vi': 'Tiện ích để điều khiển các tính năng và tinh chỉnh hiệu suất của laptop gaming Acer.',
        'zh': '用于控制 Acer 游戏笔记本电脑功能和性能调整的实用程序。'
    },
    'pacstall_desc': {
        'am': 'ሙሉ በሙሉ ካለመስማማት ሳይኖር የቅርብ ጊዜ ሶፍትዌር እንዲጠቀሙ ያስችልዎታል፣ ከ AUR ጋር ተመሳሳይ ነገር ግን ለ Debian/Ubuntu። በጥንቃቄ ይጠቀሙ።',
        'ar': 'يتيح لك استخدام أحدث البرامج دون تنازلات، مشابه لـ AUR ولكن لـ Debian/Ubuntu. استخدمه بحذر.',
        'az': 'AUR-a bənzər şəkildə, lakin Debian/Ubuntu üçün güzəştlər olmadan ən son proqram təminatından istifadə etməyə imkan verir. Ehtiyatla istifadə edin.',
        'bg': 'Позволява ви да използвате най-новия софтуер без компромиси, подобно на AUR, но за Debian/Ubuntu. Използвайте внимателно.',
        'bn': 'কোনো আপস ছাড়াই সর্বশেষ সফটওয়্যার ব্যবহার করতে দেয়, AUR এর মতো কিন্তু Debian/Ubuntu এর জন্য। সতর্কতার সাথে ব্যবহার করুন।',
        'bs': 'Omogućava vam da koristite najnoviji softver bez kompromisa, slično kao AUR ali za Debian/Ubuntu. Koristite oprezno.',
        'cs': 'Umožňuje používat nejnovější software bez kompromisů, podobně jako AUR, ale pro Debian/Ubuntu. Používejte opatrně.',
        'da': 'Giver dig mulighed for at bruge den nyeste software uden kompromiser, ligesom AUR men til Debian/Ubuntu. Brug med forsigtighed.',
        'de': 'Ermöglicht die Nutzung der neuesten Software ohne Kompromisse, ähnlich wie AUR, aber für Debian/Ubuntu. Mit Vorsicht verwenden.',
        'el': 'Σας επιτρέπει να χρησιμοποιείτε το πιο πρόσφατο λογισμικό χωρίς συμβιβασμούς, παρόμοια με το AUR αλλά για Debian/Ubuntu. Χρησιμοποιήστε με προσοχή.',
        'es': 'Te permite usar el software más reciente sin compromisos, similar a AUR pero para Debian/Ubuntu. Úsalo con precaución.',
        'et': 'Võimaldab kasutada uusimat tarkvara ilma kompromissideta, sarnaselt AUR-ile, kuid Debian/Ubuntu jaoks. Kasutage ettevaatlikult.',
        'fa': 'به شما امکان می‌دهد از جدیدترین نرم‌افزارها بدون سازش استفاده کنید، مشابه AUR اما برای Debian/Ubuntu. با احتیاط استفاده کنید.',
        'fi': 'Mahdollistaa uusimman ohjelmiston käytön ilman kompromisseja, samankaltainen kuin AUR mutta Debian/Ubuntulle. Käytä varoen.',
        'fr': 'Vous permet d\'utiliser les derniers logiciels sans compromis, similaire à AUR mais pour Debian/Ubuntu. Utilisez avec prudence.',
        'ga': 'Ligeann duit an bogearraí is déanaí a úsáid gan comhréiteach, cosúil le AUR ach do Debian/Ubuntu. Úsáid le cúram.',
        'he': 'מאפשר לך להשתמש בתוכנה העדכנית ביותר ללא פשרות, דומה ל-AUR אך עבור Debian/Ubuntu. השתמש בזהירות.',
        'hi': 'बिना किसी समझौते के नवीनतम सॉफ़्टवेयर का उपयोग करने की अनुमति देता है, AUR की तरह लेकिन Debian/Ubuntu के लिए। सावधानी से उपयोग करें।',
        'hr': 'Omogućava vam korištenje najnovijeg softvera bez kompromisa, slično kao AUR ali za Debian/Ubuntu. Koristite oprezno.',
        'hu': 'Lehetővé teszi a legújabb szoftverek kompromisszumok nélküli használatát, hasonlóan az AUR-hoz, de Debian/Ubuntu rendszerekhez. Használd óvatosan.',
        'hy': 'Թույլ է տալիս օգտագործել վերջին ծրագրակազմը առանց զիջումների, նման AUR-ին, բայց Debian/Ubuntu-ի համար։ Օգտագործեք զգուշությամբ։',
        'id': 'Memungkinkan Anda menggunakan perangkat lunak terbaru tanpa kompromi, mirip dengan AUR tetapi untuk Debian/Ubuntu. Gunakan dengan hati-hati.',
        'is': 'Gerir þér kleift að nota nýjustu hugbúnaðinn án málamiðlana, svipað og AUR en fyrir Debian/Ubuntu. Notaðu varlega.',
        'it': 'Ti consente di utilizzare il software più recente senza compromessi, simile ad AUR ma per Debian/Ubuntu. Usa con cautela.',
        'ja': '妥協することなく最新のソフトウェアを使用できます。AURに似ていますがDebian/Ubuntu用です。注意して使用してください。',
        'ka': 'საშუალებას გაძლევთ გამოიყენოთ უახლესი პროგრამული უზრუნველყოფა კომპრომისების გარეშე, მსგავსი AUR-ის მაგრამ Debian/Ubuntu-სთვის. გამოიყენეთ სიფრთხილით.',
        'km': 'អនុញ្ញាតឱ្យអ្នកប្រើប្រាស់កម្មវិធីថ្មីបំផុតដោយមិនមានការសម្របសម្រួល ស្រដៀងនឹង AUR ប៉ុន្តែសម្រាប់ Debian/Ubuntu។ ប្រើប្រាស់ដោយប្រុងប្រយ័ត្ន។',
        'ko': '타협 없이 최신 소프트웨어를 사용할 수 있습니다. AUR과 유사하지만 Debian/Ubuntu용입니다. 주의해서 사용하세요.',
        'lo': 'ອະນຸຍາດໃຫ້ທ່ານໃຊ້ຊອບແວຫຼ້າສຸດໂດຍບໍ່ມີການປະນີປະນອມ, ຄ້າຍກັບ AUR ແຕ່ສໍາລັບ Debian/Ubuntu. ໃຊ້ດ້ວຍຄວາມລະມັດລະວັງ.',
        'lt': 'Leidžia naudoti naujausią programinę įrangą be kompromisų, panašiai kaip AUR, bet skirta Debian/Ubuntu. Naudokite atsargiai.',
        'lv': 'Ļauj izmantot jaunāko programmatūru bez kompromisiem, līdzīgi kā AUR, bet Debian/Ubuntu. Izmantojiet piesardzīgi.',
        'mn': 'AUR-тай төстэй боловч Debian/Ubuntu-д зориулсан хамгийн сүүлийн үеийн програм хангамжийг буулт хийхгүйгээр ашиглах боломжийг олгоно. Болгоомжтой ашиглана уу.',
        'ms': 'Membolehkan anda menggunakan perisian terkini tanpa kompromi, serupa dengan AUR tetapi untuk Debian/Ubuntu. Gunakan dengan berhati-hati.',
        'my': 'AUR နှင့်ဆင်တူသော်လည်း Debian/Ubuntu အတွက် အပေးအယူမရှိဘဲ နောက်ဆုံးထွက် ဆော့ဖ်ဝဲကို အသုံးပြုနိုင်စေသည်။ ဂရုတစိုက်သုံးပါ။',
        'nb': 'Lar deg bruke den nyeste programvaren uten kompromisser, likt AUR men for Debian/Ubuntu. Bruk med forsiktighet.',
        'ne': 'तपाईंलाई कुनै सम्झौता बिना नवीनतम सफ्टवेयर प्रयोग गर्न अनुमति दिन्छ, AUR जस्तै तर Debian/Ubuntu को लागि। सावधानीपूर्वक प्रयोग गर्नुहोस्।',
        'nl': 'Stelt je in staat om de nieuwste software zonder compromissen te gebruiken, vergelijkbaar met AUR maar voor Debian/Ubuntu. Gebruik met voorzichtigheid.',
        'pl': 'Umożliwia korzystanie z najnowszego oprogramowania bez kompromisów, podobnie jak AUR, ale dla Debian/Ubuntu. Używaj ostrożnie.',
        'pt': 'Permite usar o software mais recente sem compromissos, semelhante ao AUR, mas para Debian/Ubuntu. Use com cautela.',
        'ro': 'Vă permite să utilizați cel mai recent software fără compromisuri, similar cu AUR, dar pentru Debian/Ubuntu. Utilizați cu precauție.',
        'ru': 'Позволяет использовать новейшее программное обеспечение без компромиссов, аналогично AUR, но для Debian/Ubuntu. Используйте с осторожностью.',
        'sk': 'Umožňuje používať najnovší softvér bez kompromisov, podobne ako AUR, ale pre Debian/Ubuntu. Používajte opatrne.',
        'sl': 'Omogoča uporabo najnovejše programske opreme brez kompromisov, podobno kot AUR, vendar za Debian/Ubuntu. Uporabite previdno.',
        'sq': 'Ju lejon të përdorni softuerin më të fundit pa kompromis, i ngjashëm me AUR por për Debian/Ubuntu. Përdoreni me kujdes.',
        'sr': 'Омогућава вам да користите најновији софтвер без компромиса, слично као AUR али за Debian/Ubuntu. Користите опрезно.',
        'sv': 'Låter dig använda den senaste programvaran utan kompromisser, liknande AUR men för Debian/Ubuntu. Använd med försiktighet.',
        'sw': 'Inakuruhusu kutumia programu mpya zaidi bila makubaliano, kama AUR lakini kwa Debian/Ubuntu. Tumia kwa uangalifu.',
        'ta': 'எந்த சமரசமும் இல்லாமல் சமீபத்திய மென்பொருளை பயன்படுத்த அனுமதிக்கிறது, AUR போன்றது ஆனால் Debian/Ubuntu க்கு. கவனமாக பயன்படுத்தவும்.',
        'tg': 'Ба шумо имкон медиҳад, ки нармафзори навтаринро бидуни сазиш истифода баред, монанди AUR вале барои Debian/Ubuntu. Бо эҳтиёт истифода баред.',
        'th': 'ช่วยให้คุณใช้ซอฟต์แวร์ล่าสุดโดยไม่ต้องประนีประนอม คล้ายกับ AUR แต่สำหรับ Debian/Ubuntu ใช้ด้วยความระมัดระวัง',
        'tl': 'Nagbibigay-daan sa iyong gumamit ng pinakabagong software nang walang kompromiso, katulad ng AUR pero para sa Debian/Ubuntu. Gamitin nang may pag-iingat.',
        'tr': 'Taviz vermeden en son yazılımı kullanmanıza olanak tanır, AUR\'ye benzer ancak Debian/Ubuntu için. Dikkatli kullanın.',
        'uk': 'Дозволяє використовувати найновіше програмне забезпечення без компромісів, подібно до AUR, але для Debian/Ubuntu. Використовуйте обережно.',
        'ur': 'آپ کو بغیر کسی سمجھوتے کے تازہ ترین سافٹ ویئر استعمال کرنے کی اجازت دیتا ہے، AUR کی طرح لیکن Debian/Ubuntu کے لیے۔ احتیاط سے استعمال کریں۔',
        'uz': 'AUR-ga o\'xshash, lekin Debian/Ubuntu uchun hech qanday murosasiz eng yangi dasturiy ta\'minotdan foydalanish imkonini beradi. Ehtiyotkorlik bilan foydalaning.',
        'vi': 'Cho phép bạn sử dụng phần mềm mới nhất mà không cần thỏa hiệp, tương tự như AUR nhưng dành cho Debian/Ubuntu. Sử dụng cẩn thận.',
        'zh': '允许您使用最新软件而无需妥协，类似于 AUR 但适用于 Debian/Ubuntu。请谨慎使用。'
    },
    # Add more keys here as needed, e.g.:
    # 'another_key': {
    #     'en': 'English translation',
    #     'es': 'Traducción al español',
    #     ...
    # }
}

# Skip 'en' since it's already added
for key, lang_translations in translations.items():
    for lang, translation in lang_translations.items():
        file_path = os.path.join(lang_dir, f'{lang}.json')
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            data[key] = translation
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f'Added {key} to {lang}.json')
        else:
            print(f'File {file_path} does not exist')
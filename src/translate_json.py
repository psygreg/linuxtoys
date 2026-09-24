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
    "multilib_desc": {
        "am": "Multilib በ64-ቢት ጭነቶች ላይ የ32-ቢት መተግበሪያዎችን ለማስኬድ እና ለመገንባት የሚያገለግሉ የ32-ቢት ሶፍትዌሮችን እና ላይብረሪዎችን ይዟል። እንደ Steam ላሉ መተግበሪያዎች አስፈላጊ ነው።",
        "ar": "يحتوي Multilib على برامج ومكتبات 32 بت يمكن استخدامها لتشغيل وبناء تطبيقات 32 بت على أنظمة 64 بت. وهو مطلوب لتطبيقات مثل Steam.",
        "az": "Multilib 64-bit quraşdırmalarda 32-bit tətbiqləri işə salmaq və qurmaq üçün istifadə edilə bilən 32-bit proqram və kitabxanaları ehtiva edir. Steam kimi tətbiqlər üçün tələb olunur.",
        "bg": "Multilib съдържа 32-битов софтуер и библиотеки, които могат да се използват за стартиране и изграждане на 32-битови приложения върху 64-битови инсталации. Необходим е за приложения като Steam.",
        "bn": "Multilib-এ 32-বিট সফটওয়্যার ও লাইব্রেরি রয়েছে, যা 64-বিট ইনস্টলে 32-বিট অ্যাপ্লিকেশন চালানো ও তৈরি করতে ব্যবহার করা যায়। Steam-এর মতো অ্যাপের জন্য এটি প্রয়োজনীয়।",
        "bs": "Multilib sadrži 32-bitni softver i biblioteke koji se mogu koristiti za pokretanje i izgradnju 32-bitnih aplikacija na 64-bitnim instalacijama. Potreban je za aplikacije poput Steama.",
        "cs": "Multilib obsahuje 32bitový software a knihovny, které lze použít ke spouštění a sestavování 32bitových aplikací na 64bitových instalacích. Je vyžadován aplikacemi, jako je Steam.",
        "da": "Multilib indeholder 32-bit software og biblioteker, der kan bruges til at køre og bygge 32-bit programmer på 64-bit installationer. Det er påkrævet af programmer som Steam.",
        "de": "Multilib enthält 32-Bit-Software und -Bibliotheken, mit denen 32-Bit-Anwendungen auf 64-Bit-Installationen ausgeführt und erstellt werden können. Es wird für Anwendungen wie Steam benötigt.",
        "el": "Το Multilib περιέχει λογισμικό και βιβλιοθήκες 32-bit που μπορούν να χρησιμοποιηθούν για την εκτέλεση και τη δημιουργία εφαρμογών 32-bit σε εγκαταστάσεις 64-bit. Απαιτείται για εφαρμογές όπως το Steam.",
        "es": "Multilib contiene software y bibliotecas de 32 bits que permiten ejecutar y compilar aplicaciones de 32 bits en instalaciones de 64 bits. Es un requisito para aplicaciones como Steam.",
        "et": "Multilib sisaldab 32-bitist tarkvara ja teeke, mida saab kasutada 32-bitiste rakenduste käitamiseks ja koostamiseks 64-bitistel paigaldustel. Seda vajavad sellised rakendused nagu Steam.",
        "fa": "Multilib شامل نرم‌افزارها و کتابخانه‌های ۳۲ بیتی است که می‌توان از آن‌ها برای اجرا و ساخت برنامه‌های ۳۲ بیتی روی نصب‌های ۶۴ بیتی استفاده کرد. برنامه‌هایی مانند Steam به آن نیاز دارند.",
        "fi": "Multilib sisältää 32-bittisiä ohjelmistoja ja kirjastoja, joiden avulla 32-bittisiä sovelluksia voidaan suorittaa ja rakentaa 64-bittisissä asennuksissa. Sitä tarvitaan esimerkiksi Steamia varten.",
        "fr": "Multilib contient des logiciels et des bibliothèques 32 bits permettant d’exécuter et de compiler des applications 32 bits sur des installations 64 bits. Il est requis pour des applications comme Steam.",
        "ga": "Tá bogearraí agus leabharlanna 32-giotán in Multilib is féidir a úsáid chun feidhmchláir 32-giotán a rith agus a thógáil ar shuiteálacha 64-giotán. Tá sé riachtanach d’fheidhmchláir ar nós Steam.",
        "he": "Multilib מכיל תוכנות וספריות של 32 סיביות שניתן להשתמש בהן כדי להריץ ולבנות יישומי 32 סיביות בהתקנות של 64 סיביות. הוא נדרש עבור יישומים כמו Steam.",
        "hi": "Multilib में 32-बिट सॉफ़्टवेयर और लाइब्रेरी शामिल हैं, जिनका उपयोग 64-बिट इंस्टॉलेशन पर 32-बिट एप्लिकेशन चलाने और बनाने के लिए किया जा सकता है। Steam जैसे ऐप्स के लिए यह आवश्यक है।",
        "hr": "Multilib sadrži 32-bitni softver i biblioteke koji se mogu koristiti za pokretanje i izgradnju 32-bitnih aplikacija na 64-bitnim instalacijama. Potreban je za aplikacije poput Steama.",
        "hu": "A Multilib 32 bites szoftvereket és könyvtárakat tartalmaz, amelyekkel 32 bites alkalmazások futtathatók és építhetők 64 bites telepítéseken. Olyan alkalmazásokhoz szükséges, mint a Steam.",
        "hy": "Multilib-ը պարունակում է 32-բիթանոց ծրագրեր և գրադարաններ, որոնք կարող են օգտագործվել 64-բիթանոց համակարգերում 32-բիթանոց հավելվածներ գործարկելու և կառուցելու համար։ Այն անհրաժեշտ է Steam-ի նման հավելվածների համար։",
        "id": "Multilib berisi perangkat lunak dan pustaka 32-bit yang dapat digunakan untuk menjalankan dan membangun aplikasi 32-bit pada instalasi 64-bit. Ini diperlukan untuk aplikasi seperti Steam.",
        "is": "Multilib inniheldur 32-bita hugbúnað og söfn sem hægt er að nota til að keyra og byggja 32-bita forrit á 64-bita uppsetningum. Það er nauðsynlegt fyrir forrit eins og Steam.",
        "it": "Multilib contiene software e librerie a 32 bit che possono essere utilizzati per eseguire e compilare applicazioni a 32 bit su installazioni a 64 bit. È necessario per applicazioni come Steam.",
        "ja": "Multilib には、64 ビット環境で 32 ビットアプリケーションを実行およびビルドするために使用できる 32 ビットのソフトウェアとライブラリが含まれています。Steam などのアプリに必要です。",
        "ka": "Multilib შეიცავს 32-ბიტიან პროგრამებსა და ბიბლიოთეკებს, რომლებიც შეიძლება გამოყენებულ იქნეს 64-ბიტიან სისტემებზე 32-ბიტიანი აპლიკაციების გასაშვებად და ასაწყობად. ის საჭიროა ისეთი აპლიკაციებისთვის, როგორიცაა Steam.",
        "km": "Multilib មានកម្មវិធី និងបណ្ណាល័យ 32-bit ដែលអាចប្រើដើម្បីដំណើរការ និងបង្កើតកម្មវិធី 32-bit លើការដំឡើង 64-bit។ វាត្រូវបានទាមទារសម្រាប់កម្មវិធីដូចជា Steam។",
        "ko": "Multilib에는 64비트 설치 환경에서 32비트 애플리케이션을 실행하고 빌드하는 데 사용할 수 있는 32비트 소프트웨어와 라이브러리가 포함되어 있습니다. Steam과 같은 앱에 필요합니다.",
        "lo": "Multilib ປະກອບມີຊອບແວ ແລະ ໄລບຣາຣີ 32-bit ທີ່ສາມາດໃຊ້ເພື່ອເປີດໃຊ້ ແລະ ສ້າງແອັບ 32-bit ໃນລະບົບ 64-bit. ມັນຈຳເປັນສຳລັບແອັບເຊັ່ນ Steam.",
        "lt": "Multilib yra 32 bitų programinė įranga ir bibliotekos, kurias galima naudoti 32 bitų programoms paleisti ir kurti 64 bitų sistemose. Jis reikalingas tokioms programoms kaip Steam.",
        "lv": "Multilib satur 32 bitu programmatūru un bibliotēkas, ko var izmantot 32 bitu lietotņu palaišanai un būvēšanai 64 bitu instalācijās. Tas ir nepieciešams tādām lietotnēm kā Steam.",
        "mn": "Multilib нь 64-бит суулгац дээр 32-бит аппликейшн ажиллуулах болон бүтээхэд ашиглаж болох 32-бит програм хангамж, сангуудыг агуулдаг. Steam зэрэг аппуудад шаардлагатай.",
        "ms": "Multilib mengandungi perisian dan pustaka 32-bit yang boleh digunakan untuk menjalankan dan membina aplikasi 32-bit pada pemasangan 64-bit. Ia diperlukan untuk aplikasi seperti Steam.",
        "my": "Multilib တွင် 64-bit စနစ်များပေါ်၌ 32-bit အက်ပ်များကို အသုံးပြုရန်နှင့် တည်ဆောက်ရန် အသုံးပြုနိုင်သည့် 32-bit ဆော့ဖ်ဝဲနှင့် library များ ပါဝင်သည်။ Steam ကဲ့သို့သော အက်ပ်များအတွက် လိုအပ်သည်။",
        "nb": "Multilib inneholder 32-bits programvare og biblioteker som kan brukes til å kjøre og bygge 32-bits programmer på 64-bits installasjoner. Det kreves for apper som Steam.",
        "ne": "Multilib मा 32-बिट सफ्टवेयर र लाइब्रेरीहरू हुन्छन्, जसलाई 64-बिट स्थापनामा 32-बिट एप्लिकेसनहरू चलाउन र निर्माण गर्न प्रयोग गर्न सकिन्छ। Steam जस्ता एपहरूका लागि यो आवश्यक हुन्छ।",
        "nl": "Multilib bevat 32-bits software en bibliotheken waarmee 32-bits toepassingen op 64-bits installaties kunnen worden uitgevoerd en gebouwd. Het is vereist voor apps zoals Steam.",
        "pl": "Multilib zawiera 32-bitowe oprogramowanie i biblioteki, które umożliwiają uruchamianie i kompilowanie 32-bitowych aplikacji w 64-bitowych instalacjach. Jest wymagany przez aplikacje takie jak Steam.",
        "pt": "O Multilib contém softwares e bibliotecas de 32 bits que podem ser usados para executar e compilar aplicativos de 32 bits em instalações de 64 bits. Ele é necessário para aplicativos como o Steam.",
        "ro": "Multilib conține software și biblioteci pe 32 de biți care pot fi utilizate pentru a rula și compila aplicații pe 32 de biți în instalări pe 64 de biți. Este necesar pentru aplicații precum Steam.",
        "ru": "Multilib содержит 32-битное программное обеспечение и библиотеки, которые позволяют запускать и собирать 32-битные приложения в 64-битных системах. Он необходим для таких приложений, как Steam.",
        "sk": "Multilib obsahuje 32-bitový softvér a knižnice, ktoré možno použiť na spúšťanie a zostavovanie 32-bitových aplikácií v 64-bitových inštaláciách. Vyžadujú ho aplikácie ako Steam.",
        "sl": "Multilib vsebuje 32-bitno programsko opremo in knjižnice, ki jih je mogoče uporabiti za zagon in gradnjo 32-bitnih aplikacij v 64-bitnih namestitvah. Potrebujejo ga aplikacije, kot je Steam.",
        "sq": "Multilib përmban softuer dhe biblioteka 32-bit që mund të përdoren për të ekzekutuar dhe ndërtuar aplikacione 32-bit në instalime 64-bit. Kërkohet për aplikacione si Steam.",
        "sr": "Multilib садржи 32-битни софтвер и библиотеке који се могу користити за покретање и изградњу 32-битних апликација на 64-битним инсталацијама. Неопходан је за апликације као што је Steam.",
        "sv": "Multilib innehåller 32-bitars programvara och bibliotek som kan användas för att köra och bygga 32-bitars program på 64-bitars installationer. Det krävs för appar som Steam.",
        "sw": "Multilib ina programu na maktaba za biti 32 ambazo zinaweza kutumika kuendesha na kujenga programu za biti 32 kwenye usakinishaji wa biti 64. Inahitajika kwa programu kama Steam.",
        "ta": "Multilib ஆனது 64-bit நிறுவல்களில் 32-bit பயன்பாடுகளை இயக்கவும் உருவாக்கவும் பயன்படுத்தக்கூடிய 32-bit மென்பொருள் மற்றும் நூலகங்களைக் கொண்டுள்ளது. Steam போன்ற பயன்பாடுகளுக்கு இது தேவைப்படுகிறது.",
        "tg": "Multilib нармафзор ва китобхонаҳои 32-битаро дар бар мегирад, ки барои иҷро ва сохтани барномаҳои 32-бита дар насбҳои 64-бита истифода мешаванд. Он барои барномаҳое мисли Steam зарур аст.",
        "th": "Multilib ประกอบด้วยซอฟต์แวร์และไลบรารีแบบ 32 บิตที่ใช้สำหรับเรียกใช้และสร้างแอปพลิเคชันแบบ 32 บิตบนระบบที่ติดตั้งแบบ 64 บิต โดยจำเป็นสำหรับแอปอย่าง Steam",
        "tl": "Naglalaman ang Multilib ng 32-bit na software at mga library na maaaring gamitin upang magpatakbo at bumuo ng mga 32-bit na application sa mga 64-bit na installation. Kinakailangan ito para sa mga app tulad ng Steam.",
        "tr": "Multilib, 64 bit kurulumlarda 32 bit uygulamaları çalıştırmak ve derlemek için kullanılabilen 32 bit yazılım ve kitaplıkları içerir. Steam gibi uygulamalar için gereklidir.",
        "uk": "Multilib містить 32-бітне програмне забезпечення та бібліотеки, які дають змогу запускати й збирати 32-бітні програми в 64-бітних системах. Він необхідний для таких застосунків, як Steam.",
        "ur": "Multilib میں 32-بٹ سافٹ ویئر اور لائبریریاں شامل ہیں جنہیں 64-بٹ تنصیبات پر 32-بٹ ایپلیکیشنز چلانے اور بنانے کے لیے استعمال کیا جا سکتا ہے۔ Steam جیسی ایپس کے لیے یہ ضروری ہے۔",
        "uz": "Multilib 64-bitli o‘rnatmalarda 32-bitli ilovalarni ishga tushirish va yaratish uchun ishlatiladigan 32-bitli dasturiy ta’minot va kutubxonalarni o‘z ichiga oladi. U Steam kabi ilovalar uchun talab qilinadi.",
        "vi": "Multilib chứa phần mềm và thư viện 32-bit có thể được sử dụng để chạy và xây dựng các ứng dụng 32-bit trên các bản cài đặt 64-bit. Đây là yêu cầu đối với các ứng dụng như Steam.",
        "zh": "Multilib 包含 32 位软件和库，可用于在 64 位系统上运行和构建 32 位应用程序。Steam 等应用需要它。"
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

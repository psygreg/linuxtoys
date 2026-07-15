import json
import os

# Directory containing the language files
lang_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "p3/libs/lang/")

# Translations dictionary: key -> {lang_code: translation}
translations = {
    "medicat_desc": {
        "am": "የቅርብ ጊዜ የኮምፒውተር ምርመራ እና መልሶ ማግኛ መሣሪያዎችን በቀላሉ ለመጠቀም የተዘጋጀ የቀጥታ USB መሣሪያ ስብስብ።",
        "ar": "مجموعة من أحدث أدوات تشخيص الكمبيوتر واستعادته، مجمعة في حزمة USB حية سهلة الاستخدام.",
        "az": "İstifadəsi asan canlı USB alət dəstində toplanmış ən son kompüter diaqnostika və bərpa vasitələrinin seçimi.",
        "bg": "Подборка от най-новите инструменти за диагностика и възстановяване на компютри, събрани в лесен за използване Live USB пакет.",
        "bn": "সহজে ব্যবহারযোগ্য একটি লাইভ USB টুলকিটে সংকলিত সর্বশেষ কম্পিউটার ডায়াগনস্টিক ও পুনরুদ্ধার সরঞ্জামের সংগ্রহ।",
        "bs": "Izbor najnovijih alata za dijagnostiku i oporavak računara, objedinjenih u jednostavan Live USB alat.",
        "cs": "Výběr nejnovějších nástrojů pro diagnostiku a obnovu počítače v snadno použitelném Live USB balíčku.",
        "da": "Et udvalg af de nyeste værktøjer til computerdiagnostik og gendannelse samlet i et brugervenligt Live USB-værktøjssæt.",
        "de": "Eine Auswahl der neuesten Diagnose- und Wiederherstellungstools für Computer, zusammengestellt in einem benutzerfreundlichen Live-USB-Toolkit.",
        "el": "Μια συλλογή από τα πιο πρόσφατα εργαλεία διάγνωσης και αποκατάστασης υπολογιστών, συγκεντρωμένα σε ένα εύχρηστο Live USB toolkit.",
        "es": "Una selección de las herramientas más recientes de diagnóstico y recuperación para equipos, reunidas en un práctico kit Live USB.",
        "et": "Valik uusimaid arvuti diagnostika- ja taastetööriistu, koondatud hõlpsasti kasutatavasse Live USB tööriistakomplekti.",
        "fa": "مجموعه‌ای از جدیدترین ابزارهای عیب‌یابی و بازیابی رایانه، گردآوری‌شده در یک مجموعه Live USB با کاربری آسان.",
        "fi": "Valikoima uusimpia tietokoneen diagnostiikka- ja palautustyökaluja helppokäyttöisessä Live USB -työkalupaketissa.",
        "fr": "Une sélection des derniers outils de diagnostic et de récupération pour ordinateur, regroupés dans une boîte à outils Live USB facile à utiliser.",
        "ga": "Rogha de na huirlisí diagnóise agus aisghabhála ríomhaire is déanaí, curtha le chéile i bhfoireann Live USB atá éasca le húsáid.",
        "he": "אוסף של כלי האבחון והשחזור העדכניים ביותר למחשבים, המרוכזים בערכת Live USB קלה לשימוש.",
        "hi": "नवीनतम कंप्यूटर डायग्नोस्टिक और रिकवरी टूल्स का चयन, एक उपयोग में आसान लाइव USB टूलकिट में संकलित।",
        "hr": "Odabir najnovijih alata za dijagnostiku i oporavak računala, objedinjenih u jednostavan Live USB paket.",
        "hu": "A legújabb számítógép-diagnosztikai és helyreállító eszközök gyűjteménye egy könnyen használható Live USB csomagban.",
        "hy": "Համակարգչի ախտորոշման և վերականգնման նորագույն գործիքների հավաքածու՝ մեկ հեշտ օգտագործվող Live USB փաթեթում։",
        "id": "Pilihan alat diagnostik dan pemulihan komputer terbaru yang dikemas dalam toolkit Live USB yang mudah digunakan.",
        "is": "Úrval nýjustu greiningar- og endurheimtartækja fyrir tölvur, safnað saman í auðvelt Live USB verkfærasett.",
        "it": "Una selezione dei più recenti strumenti di diagnostica e ripristino del computer, raccolti in un pratico toolkit Live USB.",
        "ja": "最新のコンピューター診断および復旧ツールを、使いやすい Live USB ツールキットとしてまとめたものです。",
        "ka": "კომპიუტერის დიაგნოსტიკისა და აღდგენის უახლესი ხელსაწყოების ნაკრები, გაერთიანებული მარტივად გამოსაყენებელ Live USB ინსტრუმენტებში.",
        "km": "សំណុំឧបករណ៍វិភាគ និងស្តារកុំព្យូទ័រចុងក្រោយបំផុត ដែលបានប្រមូលផ្តុំជាឧបករណ៍ Live USB ងាយស្រួលប្រើ។",
        "ko": "최신 컴퓨터 진단 및 복구 도구를 사용하기 쉬운 Live USB 툴킷으로 모아 놓았습니다.",
        "lo": "ຊຸດເຄື່ອງມືວິນິດໄສ ແລະ ກູ້ຄືນຄອມພິວເຕີລ່າສຸດ ທີ່ລວບລວມໄວ້ໃນ Live USB ທີ່ໃຊ້ງານງ່າຍ.",
        "lt": "Naujausių kompiuterio diagnostikos ir atkūrimo įrankių rinkinys patogiame Live USB pakete.",
        "lv": "Jaunāko datora diagnostikas un atkopšanas rīku izlase, apkopota viegli lietojamā Live USB rīkkopā.",
        "mn": "Компьютерийн оношлогоо болон сэргээх хамгийн сүүлийн үеийн хэрэгслүүдийг нэгтгэсэн ашиглахад хялбар Live USB хэрэгслийн багц.",
        "ms": "Pilihan alat diagnostik dan pemulihan komputer terkini yang dihimpunkan dalam toolkit Live USB yang mudah digunakan.",
        "my": "အသုံးပြုရလွယ်ကူသော Live USB ကိရိယာအစုံတွင် စုစည်းထားသော နောက်ဆုံးပေါ် ကွန်ပျူတာ စမ်းသပ်ခြင်းနှင့် ပြန်လည်ရယူရေး ကိရိယာများ။",
        "nb": "Et utvalg av de nyeste verktøyene for datamaskindiagnostikk og gjenoppretting samlet i et brukervennlig Live USB-verktøysett.",
        "ne": "प्रयोग गर्न सजिलो Live USB टूलकिटमा समावेश गरिएका नवीनतम कम्प्युटर निदान र पुनःप्राप्ति उपकरणहरूको संग्रह।",
        "nl": "Een selectie van de nieuwste diagnose- en herstelhulpmiddelen voor computers, samengebracht in een eenvoudig te gebruiken Live USB-toolkit.",
        "pl": "Zestaw najnowszych narzędzi do diagnostyki i odzyskiwania komputerów, zebranych w łatwym w użyciu pakiecie Live USB.",
        "pt": "Uma seleção das mais recentes ferramentas de diagnóstico e recuperação de computadores reunidas em um kit Live USB fácil de usar.",
        "ro": "O selecție a celor mai noi instrumente de diagnosticare și recuperare a computerelor, reunite într-un pachet Live USB ușor de utilizat.",
        "ru": "Подборка новейших инструментов для диагностики и восстановления компьютеров, собранных в удобный Live USB-комплект.",
        "sk": "Výber najnovších nástrojov na diagnostiku a obnovu počítača v ľahko použiteľnom Live USB balíku.",
        "sl": "Izbor najnovejših orodij za diagnostiko in obnovitev računalnika, združenih v enostaven Live USB komplet.",
        "sq": "Përzgjedhje e mjeteve më të fundit për diagnostikimin dhe rikuperimin e kompjuterëve, të përmbledhura në një paketë Live USB të lehtë për përdorim.",
        "sr": "Избор најновијих алата за дијагностику и опоравак рачунара, обједињених у једноставан Live USB пакет.",
        "sv": "Ett urval av de senaste verktygen för datordiagnostik och återställning, samlade i ett lättanvänt Live USB-verktygspaket.",
        "sw": "Mkusanyiko wa zana za hivi karibuni za uchunguzi na urejeshaji wa kompyuta katika kifurushi rahisi kutumia cha Live USB.",
        "ta": "பயன்படுத்த எளிதான Live USB கருவித்தொகுப்பில் தொகுக்கப்பட்ட சமீபத்திய கணினி கண்டறிதல் மற்றும் மீட்பு கருவிகளின் தொகுப்பு.",
        "tg": "Маҷмӯи воситаҳои навтарини ташхис ва барқарорсозии компютер, ки дар як маҷмӯаи осони Live USB ҷамъ оварда шудаанд.",
        "th": "ชุดเครื่องมือ Live USB ที่ใช้งานง่าย ซึ่งรวมเครื่องมือวินิจฉัยและกู้คืนคอมพิวเตอร์รุ่นล่าสุดไว้ด้วยกัน",
        "tl": "Isang koleksyon ng pinakabagong mga kasangkapan para sa pagsusuri at pag-recover ng computer na pinagsama sa isang madaling gamitin na Live USB toolkit.",
        "tr": "Kullanımı kolay bir Live USB araç setinde bir araya getirilmiş en güncel bilgisayar tanılama ve kurtarma araçlarından oluşan seçki.",
        "uk": "Добірка найновіших інструментів для діагностики та відновлення комп'ютерів, зібраних у зручному наборі Live USB.",
        "ur": "کمپیوٹر کی تشخیص اور بحالی کے جدید ترین ٹولز کا مجموعہ، جو ایک آسان Live USB ٹول کٹ میں فراہم کیا گیا ہے۔",
        "uz": "Foydalanish oson Live USB to‘plamiga jamlangan eng so‘nggi kompyuter diagnostikasi va tiklash vositalari.",
        "vi": "Tuyển chọn các công cụ chẩn đoán và khôi phục máy tính mới nhất, được tích hợp trong một bộ công cụ Live USB dễ sử dụng.",
        "zh": "精选最新的计算机诊断和恢复工具，整合到一个易于使用的 Live USB 工具包中。"
    },

    "umipp_desc": {
        "am": "የከርነል መለኪያ በመጠቀም CPU UMIPን ያሰናክላል። አንዳንድ የተወሰኑ የWindows መተግበሪያዎችን በ WINE/Proton ለማስኬድ ሊያስፈልግ ይችላል።",
        "ar": "يعطّل ميزة UMIP في المعالج باستخدام معلمة للنواة. قد يكون ذلك مطلوبًا لتشغيل بعض تطبيقات Windows عبر WINE/Proton.",
        "az": "Nüvə parametrindən istifadə edərək CPU UMIP funksiyasını söndürür. Bəzi Windows tətbiqlərini WINE/Proton vasitəsilə işlətmək üçün lazım ola bilər.",
        "bg": "Деактивира CPU UMIP чрез параметър на ядрото. Може да е необходимо за стартиране на някои приложения за Windows чрез WINE/Proton.",
        "bn": "কার্নেল প্যারামিটারের মাধ্যমে CPU UMIP নিষ্ক্রিয় করে। WINE/Proton-এর মাধ্যমে কিছু নির্দিষ্ট Windows অ্যাপ চালাতে প্রয়োজন হতে পারে।",
        "bs": "Onemogućava CPU UMIP putem parametra jezgre. Može biti potrebno za pokretanje određenih Windows aplikacija putem WINE/Proton.",
        "cs": "Zakáže CPU UMIP pomocí parametru jádra. Může být potřeba pro spuštění některých aplikací Windows přes WINE/Proton.",
        "da": "Deaktiverer CPU UMIP via en kerneparameter. Kan være nødvendigt for at køre visse Windows-programmer gennem WINE/Proton.",
        "de": "Deaktiviert CPU-UMIP über einen Kernel-Parameter. Kann erforderlich sein, um bestimmte Windows-Anwendungen über WINE/Proton auszuführen.",
        "el": "Απενεργοποιεί το CPU UMIP μέσω παραμέτρου του πυρήνα. Μπορεί να απαιτείται για την εκτέλεση ορισμένων εφαρμογών Windows μέσω WINE/Proton.",
        "es": "Desactiva UMIP de la CPU mediante un parámetro del kernel. Puede ser necesario para ejecutar determinadas aplicaciones de Windows mediante WINE/Proton.",
        "et": "Keelab CPU UMIP-i kerneli parameetri abil. Võib olla vajalik mõne Windowsi rakenduse käivitamiseks WINE/Protoni kaudu.",
        "fa": "ویژگی UMIP پردازنده را از طریق پارامتر کرنل غیرفعال می‌کند. ممکن است برای اجرای برخی برنامه‌های ویندوزی از طریق WINE/Proton لازم باشد.",
        "fi": "Poistaa CPU:n UMIP-toiminnon käytöstä ytimen parametrilla. Saattaa olla tarpeen joidenkin Windows-sovellusten suorittamiseen WINE/Protonin kautta.",
        "fr": "Désactive UMIP du processeur via un paramètre du noyau. Peut être nécessaire pour exécuter certaines applications Windows avec WINE/Proton.",
        "ga": "Díchumasaíonn sé UMIP an LAP trí pharaiméadar eithne. D'fhéadfadh sé a bheith riachtanach chun roinnt feidhmchlár Windows a rith trí WINE/Proton.",
        "he": "משבית את UMIP של המעבד באמצעות פרמטר ליבה. ייתכן שיידרש להפעלת יישומי Windows מסוימים דרך WINE/Proton.",
        "hi": "कर्नेल पैरामीटर के माध्यम से CPU UMIP को अक्षम करता है। WINE/Proton के माध्यम से कुछ Windows अनुप्रयोग चलाने के लिए आवश्यक हो सकता है।",
        "hr": "Onemogućuje CPU UMIP putem parametra jezgre. Može biti potrebno za pokretanje određenih Windows aplikacija putem WINE/Proton.",
        "hu": "Letiltja a CPU UMIP funkcióját egy kernelparaméter segítségével. Szükséges lehet egyes Windows-alkalmazások futtatásához WINE/Proton alatt.",
        "hy": "Անջատում է CPU UMIP-ը միջուկի պարամետրով։ Կարող է պահանջվել որոշ Windows ծրագրեր WINE/Proton-ի միջոցով գործարկելու համար։",
        "id": "Menonaktifkan CPU UMIP melalui parameter kernel. Mungkin diperlukan untuk menjalankan aplikasi Windows tertentu melalui WINE/Proton.",
        "is": "Gerir CPU UMIP óvirkt með kjarnabreytu. Getur verið nauðsynlegt til að keyra ákveðin Windows-forrit í gegnum WINE/Proton.",
        "it": "Disabilita UMIP della CPU tramite un parametro del kernel. Potrebbe essere necessario per eseguire alcune applicazioni Windows tramite WINE/Proton.",
        "ja": "カーネルパラメータを使用して CPU の UMIP を無効化します。WINE/Proton 経由で一部の Windows アプリケーションを実行するために必要な場合があります。",
        "ka": "თიშავს CPU UMIP-ს ბირთვის პარამეტრის მეშვეობით. შესაძლოა საჭირო იყოს ზოგიერთი Windows პროგრამის WINE/Proton-ით გასაშვებად.",
        "km": "បិទ CPU UMIP តាមរយៈប៉ារ៉ាម៉ែត្រខឺណែល។ អាចត្រូវការសម្រាប់ដំណើរការកម្មវិធី Windows មួយចំនួនតាមរយៈ WINE/Proton។",
        "ko": "커널 매개변수를 통해 CPU UMIP를 비활성화합니다. 일부 Windows 프로그램을 WINE/Proton으로 실행하는 데 필요할 수 있습니다.",
        "lo": "ປິດ CPU UMIP ຜ່ານພາຣາມິເຕີຂອງເຄີເນວ. ອາດຈຳເປັນສຳລັບການໃຊ້ງານບາງແອັບ Windows ຜ່ານ WINE/Proton.",
        "lt": "Išjungia CPU UMIP naudodamas branduolio parametrą. Gali būti reikalinga kai kurioms Windows programoms paleisti per WINE/Proton.",
        "lv": "Atspējo CPU UMIP, izmantojot kodola parametru. Tas var būt nepieciešams dažu Windows lietotņu palaišanai ar WINE/Proton.",
        "mn": "CPU UMIP-ийг цөмийн параметрээр идэвхгүй болгоно. WINE/Proton-оор зарим Windows програмыг ажиллуулахад шаардлагатай байж болно.",
        "ms": "Melumpuhkan CPU UMIP melalui parameter kernel. Mungkin diperlukan untuk menjalankan aplikasi Windows tertentu melalui WINE/Proton.",
        "my": "Kernel parameter မှတစ်ဆင့် CPU UMIP ကို ပိတ်ထားသည်။ WINE/Proton ဖြင့် Windows အက်ပ်အချို့ကို လုပ်ဆောင်ရန် လိုအပ်နိုင်သည်။",
        "nb": "Deaktiverer CPU UMIP via en kjerneparameter. Kan være nødvendig for å kjøre enkelte Windows-programmer gjennom WINE/Proton.",
        "ne": "कर्नेल प्यारामिटरमार्फत CPU UMIP अक्षम गर्दछ। WINE/Proton मार्फत केही Windows अनुप्रयोग चलाउन आवश्यक पर्न सक्छ।",
        "nl": "Schakelt CPU UMIP uit via een kernelparameter. Kan nodig zijn om bepaalde Windows-toepassingen via WINE/Proton uit te voeren.",
        "pl": "Wyłącza funkcję UMIP procesora za pomocą parametru jądra. Może być wymagane do uruchamiania niektórych aplikacji Windows przez WINE/Proton.",
        "pt": "Desativa o UMIP da CPU por meio de um parâmetro do kernel. Pode ser necessário para executar alguns aplicativos específicos do Windows através do WINE/Proton.",
        "ro": "Dezactivează UMIP al procesorului printr-un parametru al nucleului. Poate fi necesar pentru rularea unor aplicații Windows prin WINE/Proton.",
        "ru": "Отключает UMIP процессора с помощью параметра ядра. Может потребоваться для запуска некоторых приложений Windows через WINE/Proton.",
        "sk": "Zakáže CPU UMIP pomocou parametra jadra. Môže byť potrebné na spustenie niektorých aplikácií Windows cez WINE/Proton.",
        "sl": "Onemogoči CPU UMIP prek parametra jedra. Morda bo potrebno za zagon nekaterih programov Windows prek WINE/Proton.",
        "sq": "Çaktivizon CPU UMIP përmes një parametri të kernelit. Mund të nevojitet për të ekzekutuar disa aplikacione Windows përmes WINE/Proton.",
        "sr": "Онемогућава CPU UMIP путем параметра језгра. Може бити потребно за покретање појединих Windows апликација преко WINE/Proton.",
        "sv": "Inaktiverar CPU UMIP via en kärnparameter. Kan behövas för att köra vissa Windows-program genom WINE/Proton.",
        "sw": "Huzima CPU UMIP kupitia kigezo cha kernel. Huenda ikahitajika ili kuendesha baadhi ya programu za Windows kupitia WINE/Proton.",
        "ta": "கர்னல் அளவுரு மூலம் CPU UMIP-ஐ முடக்குகிறது. WINE/Proton மூலம் சில Windows செயலிகளை இயக்க இது தேவைப்படலாம்.",
        "tg": "UMIP-и CPU-ро тавассути параметри ядро ғайрифаъол мекунад. Барои иҷрои баъзе барномаҳои Windows тавассути WINE/Proton лозим шуда метавонад.",
        "th": "ปิดใช้งาน CPU UMIP ผ่านพารามิเตอร์ของเคอร์เนล อาจจำเป็นสำหรับการเรียกใช้แอปพลิเคชัน Windows บางตัวผ่าน WINE/Proton",
        "tl": "Hindi pinapagana ang CPU UMIP sa pamamagitan ng kernel parameter. Maaaring kailanganin upang mapatakbo ang ilang Windows application gamit ang WINE/Proton.",
        "tr": "Bir çekirdek parametresi aracılığıyla CPU UMIP'yi devre dışı bırakır. Bazı Windows uygulamalarını WINE/Proton üzerinden çalıştırmak için gerekebilir.",
        "uk": "Вимикає UMIP процесора за допомогою параметра ядра. Може знадобитися для запуску деяких програм Windows через WINE/Proton.",
        "ur": "کرنل پیرامیٹر کے ذریعے CPU UMIP کو غیر فعال کرتا ہے۔ WINE/Proton کے ذریعے کچھ مخصوص Windows ایپلی کیشنز چلانے کے لیے ضروری ہو سکتا ہے۔",
        "uz": "Yadro parametri orqali CPU UMIP funksiyasini o‘chiradi. Ayrim Windows dasturlarini WINE/Proton orqali ishga tushirish uchun kerak bo‘lishi mumkin.",
        "vi": "Vô hiệu hóa CPU UMIP thông qua một tham số của nhân. Có thể cần thiết để chạy một số ứng dụng Windows bằng WINE/Proton.",
        "zh": "通过内核参数禁用 CPU UMIP。运行某些 Windows 应用程序（通过 WINE/Proton）时可能需要此选项。"
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

import json
import os

# Directory containing the language files
lang_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "p3/libs/lang/")

# Translations dictionary: key -> {lang_code: translation}
translations = {
    "bbr_desc": {
    "am": "‘Bottleneck Bandwidth and Round-trip propagation time’፣ የኔትወርክ ፍሰትን ከፍ ለማድረግ እና መዘግየትን ለመቀነስ በGoogle የተነደፈ የላቀ የመጨናነቅ መቆጣጠሪያ አልጎሪዝም።",
    "ar": "‏‘Bottleneck Bandwidth and Round-trip propagation time’، خوارزمية Google المتقدمة للتحكم في الازدحام، والمصممة لزيادة معدل نقل الشبكة إلى أقصى حد وتقليل زمن الاستجابة.",
    "az": "‘Bottleneck Bandwidth and Round-trip propagation time’, şəbəkə ötürmə qabiliyyətini maksimuma çatdırmaq və gecikməni minimuma endirmək üçün Google tərəfindən hazırlanmış qabaqcıl sıxlıq idarəetmə alqoritmi.",
    "bg": "„Bottleneck Bandwidth and Round-trip propagation time“ — усъвършенстван алгоритъм на Google за контрол на претоварването, създаден да увеличи максимално пропускателната способност на мрежата и да сведе до минимум закъснението.",
    "bn": "‘Bottleneck Bandwidth and Round-trip propagation time’, নেটওয়ার্ক থ্রুপুট সর্বাধিক এবং লেটেন্সি সর্বনিম্ন করার জন্য Google-এর তৈরি উন্নত কনজেশন কন্ট্রোল অ্যালগরিদম।",
    "bs": "‘Bottleneck Bandwidth and Round-trip propagation time’, Googleov napredni algoritam za kontrolu zagušenja dizajniran da poveća propusnost mreže i smanji kašnjenje.",
    "cs": "„Bottleneck Bandwidth and Round-trip propagation time“, pokročilý algoritmus řízení zahlcení od Googlu navržený pro maximalizaci propustnosti sítě a minimalizaci latence.",
    "da": "‘Bottleneck Bandwidth and Round-trip propagation time’, Googles avancerede algoritme til overbelastningsstyring, der er designet til at maksimere netværkets gennemløb og minimere latenstid.",
    "de": "„Bottleneck Bandwidth and Round-trip propagation time“, Googles fortschrittlicher Algorithmus zur Überlastungssteuerung, der den Netzwerkdurchsatz maximieren und die Latenz minimieren soll.",
    "el": "‘Bottleneck Bandwidth and Round-trip propagation time’, ο προηγμένος αλγόριθμος ελέγχου συμφόρησης της Google, σχεδιασμένος για τη μεγιστοποίηση της απόδοσης του δικτύου και την ελαχιστοποίηση της καθυστέρησης.",
    "es": "‘Bottleneck Bandwidth and Round-trip propagation time’, el avanzado algoritmo de control de congestión de Google diseñado para maximizar el rendimiento de la red y minimizar la latencia.",
    "et": "„Bottleneck Bandwidth and Round-trip propagation time“, Google'i täiustatud ülekoormuse juhtimise algoritm, mis on loodud võrgu läbilaskevõime maksimeerimiseks ja latentsuse minimeerimiseks.",
    "fa": "‏‘Bottleneck Bandwidth and Round-trip propagation time’، الگوریتم پیشرفته کنترل ازدحام Google که برای به حداکثر رساندن توان عملیاتی شبکه و به حداقل رساندن تأخیر طراحی شده است.",
    "fi": "‘Bottleneck Bandwidth and Round-trip propagation time’, Googlen edistynyt ruuhkanhallinta-algoritmi, joka on suunniteltu maksimoimaan verkon läpäisykyky ja minimoimaan viive.",
    "fr": "« Bottleneck Bandwidth and Round-trip propagation time », l’algorithme avancé de contrôle de congestion de Google conçu pour maximiser le débit réseau et minimiser la latence.",
    "ga": "‘Bottleneck Bandwidth and Round-trip propagation time’, ard-algartam rialaithe plódaithe Google atá deartha chun tréchur líonra a uasmhéadú agus aga folaigh a íoslaghdú.",
    "he": "‏‘Bottleneck Bandwidth and Round-trip propagation time’, אלגוריתם בקרת העומס המתקדם של Google, שנועד למקסם את תפוקת הרשת ולמזער את זמן ההשהיה.",
    "hi": "‘Bottleneck Bandwidth and Round-trip propagation time’, Google का उन्नत कंजेशन कंट्रोल एल्गोरिदम, जिसे नेटवर्क थ्रूपुट को अधिकतम और लेटेंसी को न्यूनतम करने के लिए डिज़ाइन किया गया है।",
    "hr": "‘Bottleneck Bandwidth and Round-trip propagation time’, Googleov napredni algoritam za kontrolu zagušenja osmišljen za povećanje propusnosti mreže i smanjenje latencije.",
    "hu": "„Bottleneck Bandwidth and Round-trip propagation time”, a Google fejlett torlódásvezérlő algoritmusa, amelyet a hálózati átviteli teljesítmény maximalizálására és a késleltetés minimalizálására terveztek.",
    "hy": "‘Bottleneck Bandwidth and Round-trip propagation time’, Google-ի առաջադեմ գերբեռնվածության կառավարման ալգորիթմը, որը նախատեսված է ցանցի թողունակությունը առավելագույնի և ուշացումը նվազագույնի հասցնելու համար։",
    "id": "‘Bottleneck Bandwidth and Round-trip propagation time’, algoritma kontrol kemacetan canggih Google yang dirancang untuk memaksimalkan throughput jaringan dan meminimalkan latensi.",
    "is": "‘Bottleneck Bandwidth and Round-trip propagation time’, háþróað reiknirit Google fyrir stýringu á netþrengslum, hannað til að hámarka afköst netsins og lágmarka töf.",
    "it": "‘Bottleneck Bandwidth and Round-trip propagation time’, l'algoritmo avanzato di Google per il controllo della congestione, progettato per massimizzare il throughput della rete e ridurre al minimo la latenza.",
    "ja": "「Bottleneck Bandwidth and Round-trip propagation time」。ネットワークのスループットを最大化し、レイテンシを最小限に抑えるために Google が設計した高度な輻輳制御アルゴリズムです。",
    "ka": "‘Bottleneck Bandwidth and Round-trip propagation time’ — Google-ის მოწინავე გადატვირთვის კონტროლის ალგორითმი, რომელიც შექმნილია ქსელის გამტარუნარიანობის მაქსიმალურად გაზრდისა და დაყოვნების მინიმუმამდე შემცირებისთვის.",
    "km": "‘Bottleneck Bandwidth and Round-trip propagation time’ ជាអាល់ហ្គរីធម៍គ្រប់គ្រងការកកស្ទះកម្រិតខ្ពស់របស់ Google ដែលត្រូវបានរចនាឡើងដើម្បីបង្កើនលំហូរទិន្នន័យបណ្តាញឱ្យអតិបរមា និងកាត់បន្ថយភាពយឺតយ៉ាវឱ្យអប្បបរមា។",
    "ko": "‘Bottleneck Bandwidth and Round-trip propagation time’, 네트워크 처리량을 극대화하고 지연 시간을 최소화하도록 설계된 Google의 고급 혼잡 제어 알고리즘입니다.",
    "lo": "‘Bottleneck Bandwidth and Round-trip propagation time’, ອັນກໍຣິທຶມຄວບຄຸມຄວາມແອອັດຂັ້ນສູງຂອງ Google ທີ່ອອກແບບມາເພື່ອເພີ່ມປະສິດທິພາບການຮັບສົ່ງຂອງເຄືອຂ່າຍໃຫ້ສູງສຸດ ແລະຫຼຸດຄວາມຫນ່ວງໃຫ້ຕ່ຳສຸດ.",
    "lt": "„Bottleneck Bandwidth and Round-trip propagation time“ – pažangus Google perkrovos valdymo algoritmas, sukurtas maksimaliai padidinti tinklo pralaidumą ir sumažinti delsą.",
    "lv": "„Bottleneck Bandwidth and Round-trip propagation time“ — Google uzlabotais pārslodzes kontroles algoritms, kas izstrādāts, lai maksimāli palielinātu tīkla caurlaidspēju un samazinātu latentumu.",
    "mn": "‘Bottleneck Bandwidth and Round-trip propagation time’, сүлжээний дамжуулах чадварыг дээд хэмжээнд хүргэж, саатлыг багасгах зорилготой Google-ийн дэвшилтэт түгжрэлийн хяналтын алгоритм.",
    "ms": "‘Bottleneck Bandwidth and Round-trip propagation time’, algoritma kawalan kesesakan lanjutan Google yang direka untuk memaksimumkan daya pemprosesan rangkaian dan meminimumkan kependaman.",
    "my": "‘Bottleneck Bandwidth and Round-trip propagation time’၊ ကွန်ရက် throughput ကို အမြင့်ဆုံးနှင့် latency ကို အနည်းဆုံးဖြစ်စေရန် Google မှ ဒီဇိုင်းထုတ်ထားသော အဆင့်မြင့် congestion control algorithm ဖြစ်သည်။",
    "nb": "‘Bottleneck Bandwidth and Round-trip propagation time’, Googles avanserte algoritme for overbelastningskontroll, utviklet for å maksimere nettverkskapasiteten og minimere forsinkelsen.",
    "ne": "‘Bottleneck Bandwidth and Round-trip propagation time’, नेटवर्क थ्रुपुट अधिकतम र विलम्बता न्यूनतम बनाउन Google द्वारा डिजाइन गरिएको उन्नत कन्जेसन नियन्त्रण एल्गोरिदम।",
    "nl": "‘Bottleneck Bandwidth and Round-trip propagation time’, Googles geavanceerde algoritme voor congestiebeheer, ontworpen om de netwerkdoorvoer te maximaliseren en de latentie te minimaliseren.",
    "pl": "„Bottleneck Bandwidth and Round-trip propagation time”, zaawansowany algorytm kontroli przeciążenia firmy Google, zaprojektowany w celu maksymalizacji przepustowości sieci i minimalizacji opóźnień.",
    "pt": "‘Bottleneck Bandwidth and Round-trip propagation time’, o algoritmo avançado de controle de congestionamento do Google, desenvolvido para maximizar a taxa de transferência da rede e minimizar a latência.",
    "ro": "„Bottleneck Bandwidth and Round-trip propagation time”, algoritmul avansat de control al congestiei de la Google, conceput pentru a maximiza debitul rețelei și a minimiza latența.",
    "ru": "«Bottleneck Bandwidth and Round-trip propagation time» — усовершенствованный алгоритм Google для управления перегрузкой, разработанный для максимизации пропускной способности сети и минимизации задержки.",
    "sk": "„Bottleneck Bandwidth and Round-trip propagation time“, pokročilý algoritmus riadenia zahltenia od Googlu navrhnutý na maximalizáciu priepustnosti siete a minimalizáciu latencie.",
    "sl": "»Bottleneck Bandwidth and Round-trip propagation time«, Googlov napredni algoritem za nadzor prezasedenosti, zasnovan za povečanje prepustnosti omrežja in zmanjšanje zakasnitve.",
    "sq": "‘Bottleneck Bandwidth and Round-trip propagation time’, algoritmi i avancuar i Google për kontrollin e mbingarkesës, i projektuar për të maksimizuar xhiron e rrjetit dhe minimizuar vonesën.",
    "sr": "„Bottleneck Bandwidth and Round-trip propagation time“, Google-ов напредни алгоритам за контролу загушења, дизајниран да максимизује пропусност мреже и минимизује кашњење.",
    "sv": "‘Bottleneck Bandwidth and Round-trip propagation time’, Googles avancerade algoritm för överbelastningskontroll, utformad för att maximera nätverkets genomströmning och minimera latensen.",
    "sw": "‘Bottleneck Bandwidth and Round-trip propagation time’, algoriti ya hali ya juu ya Google ya kudhibiti msongamano, iliyoundwa kuongeza upitishaji wa mtandao na kupunguza ucheleweshaji.",
    "ta": "‘Bottleneck Bandwidth and Round-trip propagation time’, நெட்வொர்க் செயல்திறனை அதிகரிக்கவும் தாமதத்தைக் குறைக்கவும் Google வடிவமைத்த மேம்பட்ட நெரிசல் கட்டுப்பாட்டு அல்காரிதம்.",
    "tg": "‘Bottleneck Bandwidth and Round-trip propagation time’, алгоритми пешрафтаи Google барои идоракунии серборӣ, ки барои ба ҳадди аксар расонидани гузарониши шабака ва кам кардани таъхир тарҳрезӣ шудааст.",
    "th": "‘Bottleneck Bandwidth and Round-trip propagation time’ อัลกอริทึมควบคุมความแออัดขั้นสูงของ Google ที่ออกแบบมาเพื่อเพิ่มปริมาณงานของเครือข่ายให้สูงสุดและลดเวลาแฝงให้เหลือน้อยที่สุด",
    "tl": "‘Bottleneck Bandwidth and Round-trip propagation time’, advanced congestion control algorithm ng Google na idinisenyo para i-maximize ang network throughput at i-minimize ang latency.",
    "tr": "‘Bottleneck Bandwidth and Round-trip propagation time’, ağ verimini en üst düzeye çıkarmak ve gecikmeyi en aza indirmek için Google tarafından tasarlanan gelişmiş bir tıkanıklık kontrol algoritması.",
    "uk": "«Bottleneck Bandwidth and Round-trip propagation time» — удосконалений алгоритм Google для керування перевантаженням, розроблений для максимізації пропускної здатності мережі та мінімізації затримки.",
    "ur": "‏‘Bottleneck Bandwidth and Round-trip propagation time’، Google کا جدید کنجیشن کنٹرول الگورتھم، جسے نیٹ ورک تھروپٹ کو زیادہ سے زیادہ اور لیٹنسی کو کم سے کم کرنے کے لیے ڈیزائن کیا گیا ہے۔",
    "uz": "‘Bottleneck Bandwidth and Round-trip propagation time’, tarmoq o'tkazuvchanligini maksimal darajada oshirish va kechikishni minimallashtirish uchun Google tomonidan ishlab chiqilgan ilg'or tirbandlikni boshqarish algoritmi.",
    "vi": "‘Bottleneck Bandwidth and Round-trip propagation time’, thuật toán kiểm soát tắc nghẽn tiên tiến của Google được thiết kế để tối đa hóa thông lượng mạng và giảm thiểu độ trễ.",
    "zh": "“Bottleneck Bandwidth and Round-trip propagation time”，Google 设计的高级拥塞控制算法，旨在最大化网络吞吐量并尽可能降低延迟。"
    },
    "category_available": {
        "am": "የሚገኝ",
        "ar": "متاح",
        "az": "Mövcud",
        "bg": "Налично",
        "bn": "উপলব্ধ",
        "bs": "Dostupno",
        "cs": "Dostupné",
        "da": "Tilgængelig",
        "de": "Verfügbar",
        "el": "Διαθέσιμο",
        "es": "Disponible",
        "et": "Saadaval",
        "fa": "موجود",
        "fi": "Saatavilla",
        "fr": "Disponible",
        "ga": "Ar fáil",
        "he": "זמין",
        "hi": "उपलब्ध",
        "hr": "Dostupno",
        "hu": "Elérhető",
        "hy": "Հասանելի",
        "id": "Tersedia",
        "is": "Í boði",
        "it": "Disponibile",
        "ja": "利用可能",
        "ka": "ხელმისაწვდომი",
        "km": "មាន",
        "ko": "사용 가능",
        "lo": "ມີໃຫ້ໃຊ້",
        "lt": "Pasiekiama",
        "lv": "Pieejams",
        "mn": "Боломжтой",
        "ms": "Tersedia",
        "my": "ရရှိနိုင်သည်",
        "nb": "Tilgjengelig",
        "ne": "उपलब्ध",
        "nl": "Beschikbaar",
        "pl": "Dostępne",
        "pt": "Disponível",
        "ro": "Disponibil",
        "ru": "Доступно",
        "sk": "Dostupné",
        "sl": "Na voljo",
        "sq": "E disponueshme",
        "sr": "Доступно",
        "sv": "Tillgänglig",
        "sw": "Inapatikana",
        "ta": "கிடைக்கிறது",
        "tg": "Дастрас",
        "th": "พร้อมใช้งาน",
        "tl": "Available",
        "tr": "Mevcut",
        "uk": "Доступно",
        "ur": "دستیاب",
        "uz": "Mavjud",
        "vi": "Có sẵn",
        "zh": "可用"
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

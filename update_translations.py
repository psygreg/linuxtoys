import json
import os

# Dictionary of translations for each language
translations = {
    'am': {
        'cachyconfs_desc': 'Օպտիմիզացված կոնֆիգուրացիաներ ավելի լավ կատարման և արձագանքման համար, ինչպես նաև փոքր շտկումներ տիպիկ խնդիրների համար, որոնք լռելյայն օգտագործվում են CachyOS-ում, զտված համընդհանուր համատեղելիության համար.',
        'cachyconfs': 'CachyOS systemd կոնֆիգուրացիա'
    },
    'ar': {
        'cachyconfs_desc': 'التكوينات المحسنة لأداء أفضل واستجابة أسرع، وإصلاحات صغيرة للمشكلات النموذجية المستخدمة افتراضيًا في CachyOS، تم تصفيتها للتوافق العالمي.',
        'cachyconfs': 'تكوين systemd CachyOS'
    },
    'az': {
        'cachyconfs_desc': 'CachyOS-da standart olaraq istifadə olunan tipik problemlər üçün daha yaxşı performans və cavabdehlik, həmçinin kiçik düzəlişlər üçün optimallaşdırılmış konfiqurasiyalar, universal uyğunluq üçün süzülmüş.',
        'cachyconfs': 'CachyOS systemd Konfiqurasiyası'
    },
    'bg': {
        'cachyconfs_desc': 'Оптимизирани конфигурации за по-добра производителност и отзивчивост, както и малки корекции за типични проблеми, използвани по подразбиране в CachyOS, филтрирани за универсална съвместимост.',
        'cachyconfs': 'Конфигурация на systemd за CachyOS'
    },
    'bn': {
        'cachyconfs_desc': 'CachyOS-এ ডিফল্টরূপে ব্যবহৃত আরও ভাল পারফরম্যান্স এবং প্রতিক্রিয়াশীলতার জন্য অপ্টিমাইজড কনফিগারেশন, এবং টাইপিকাল সমস্যাগুলির জন্য ছোট ফিক্স, ইউনিভার্সাল কম্প্যাটিবিলিটির জন্য ফিল্টার করা হয়েছে।',
        'cachyconfs': 'CachyOS systemd কনফিগারেশন'
    },
    'bs': {
        'cachyconfs_desc': 'Optimizirane konfiguracije za bolje performanse i odzivnost, kao i male ispravke za tipična pitanja koja se koriste po defaultu na CachyOS-u, filtrirane za univerzalnu kompatibilnost.',
        'cachyconfs': 'CachyOS systemd Konfiguracija'
    },
    'cs': {
        'cachyconfs_desc': 'Optimalizované konfigurace pro lepší výkon a odezvu, stejně jako malé opravy typických problémů používaných ve výchozím nastavení na CachyOS, filtrované pro univerzální kompatibilitu.',
        'cachyconfs': 'Konfigurace systemd CachyOS'
    },
    'da': {
        'cachyconfs_desc': 'Optimerede konfigurationer for bedre ydeevne og responsivitet, samt små rettelser til typiske problemer, der bruges som standard på CachyOS, filtreret for universel kompatibilitet.',
        'cachyconfs': 'CachyOS systemd Konfiguration'
    },
    'el': {
        'cachyconfs_desc': 'Βελτιστοποιημένες διαμορφώσεις για καλύτερη απόδοση και ανταποκρισιμότητα, καθώς και μικρές διορθώσεις για τυπικά προβλήματα που χρησιμοποιούνται από προεπιλογή στο CachyOS, φιλτραρισμένες για καθολική συμβατότητα.',
        'cachyconfs': 'Διαμόρφωση systemd CachyOS'
    },
    'et': {
        'cachyconfs_desc': 'Optimeeritud konfiguratsioonid parema jõudluse ja reageerimisvõime jaoks ning väikesed parandused tüüpiliste probleemide jaoks, mida kasutatakse vaikimisi CachyOS-is, filtreeritud universaalse ühilduvuse jaoks.',
        'cachyconfs': 'CachyOS systemd Konfiguratsioon'
    },
    'fa': {
        'cachyconfs_desc': 'پیکربندی‌های بهینه‌سازی شده برای عملکرد بهتر و پاسخگویی، و همچنین اصلاحات کوچک برای مشکلات معمول که به طور پیش‌فرض در CachyOS استفاده می‌شود، فیلتر شده برای سازگاری جهانی.',
        'cachyconfs': 'پیکربندی systemd CachyOS'
    },
    'fi': {
        'cachyconfs_desc': 'Optimoitu konfiguraatiot paremman suorituskyvyn ja vasteajan sekä pienet korjaukset tyypillisiin ongelmiin, joita käytetään oletuksena CachyOS:ssa, suodatettu universaalia yhteensopivuutta varten.',
        'cachyconfs': 'CachyOS systemd -konfiguraatio'
    },
    'ga': {
        'cachyconfs_desc': 'Cumraíochtaí optamaithe le haghaidh feidhmíocht níos fearr agus freagrúlacht, chomh maith le socruithe beaga do fhadhbanna tipiciúla a úsáidtear de réir réamhshocraithe ar CachyOS, scagtha le haghaidh comhoiriúnacht uilíoch.',
        'cachyconfs': 'Cumraíocht systemd CachyOS'
    },
    'he': {
        'cachyconfs_desc': 'תצורות מותאמות לביצועים טובים יותר ותגובה, וכן תיקונים קטנים לבעיות טיפוסיות המשמשות כברירת מחדל ב-CachyOS, מסוננות לתאימות אוניברסלית.',
        'cachyconfs': 'תצורת systemd של CachyOS'
    },
    'hi': {
        'cachyconfs_desc': 'CachyOS पर डिफ़ॉल्ट रूप से उपयोग किए जाने वाले बेहतर प्रदर्शन और प्रतिक्रियाशीलता के लिए अनुकूलित कॉन्फ़िगरेशन, और विशिष्ट मुद्दों के लिए छोटे सुधार, सार्वभौमिक संगतता के लिए फ़िल्टर किए गए।',
        'cachyconfs': 'CachyOS systemd कॉन्फ़िगरेशन'
    },
    'hr': {
        'cachyconfs_desc': 'Optimizirane konfiguracije za bolje performanse i odzivnost, kao i male ispravke za tipične probleme koji se koriste prema zadanim postavkama na CachyOS-u, filtrirane za univerzalnu kompatibilnost.',
        'cachyconfs': 'Konfiguracija systemd CachyOS'
    },
    'hu': {
        'cachyconfs_desc': 'Optimalizált konfigurációk jobb teljesítmény és reagálóképesség érdekében, valamint kis javítások a tipikus problémákra, amelyeket alapértelmezés szerint használnak a CachyOS-ban, szűrve az univerzális kompatibilitás érdekében.',
        'cachyconfs': 'CachyOS systemd konfiguráció'
    },
    'hy': {
        'cachyconfs_desc': 'Օպտիմիզացված կոնֆիգուրացիաներ ավելի լավ կատարման և արձագանքման համար, ինչպես նաև փոքր շտկումներ տիպիկ խնդիրների համար, որոնք լռելյայն օգտագործվում են CachyOS-ում, զտված համընդհանուր համատեղելիության համար.',
        'cachyconfs': 'CachyOS systemd կոնֆիգուրացիա'
    },
    'id': {
        'cachyconfs_desc': 'Konfigurasi yang dioptimalkan untuk performa dan responsivitas yang lebih baik, serta perbaikan kecil untuk masalah umum yang digunakan secara default di CachyOS, disaring untuk kompatibilitas universal.',
        'cachyconfs': 'Konfigurasi systemd CachyOS'
    },
    'is': {
        'cachyconfs_desc': 'Fínstilltar stillingar fyrir betri afköst og viðbragðsgetu, auk smár lagfæringar fyrir dæmigerð vandamál sem notuð eru sjálfgefið á CachyOS, síað fyrir alheimssamræmi.',
        'cachyconfs': 'CachyOS systemd stilling'
    },
    'ka': {
        'cachyconfs_desc': 'ოპტიმიზირებული კონფიგურაციები უკეთესი წარმადობისა და რეაგირებისთვის, ასევე პატარა შესწორებები ტიპიური პრობლემებისთვის, რომლებიც ნაგულისხმევად გამოიყენება CachyOS-ში, გაფილტრული უნივერსალური თავსებადობისთვის.',
        'cachyconfs': 'CachyOS systemd კონფიგურაცია'
    },
    'km': {
        'cachyconfs_desc': 'ការកំណត់រចនាសម្ព័ន្ធដែលបានបង្កើនប្រសិទ្ធភាពសម្រាប់ការអនុវត្តការងារដែលប្រសើរឡើង និងការឆ្លើយតប ក៏ដូចជាការជួសជុលតូចៗសម្រាប់បញ្ហាធម្មតាដែលប្រើជាលំនាំដើមនៅលើ CachyOS ត្រូវបានច្រោះសម្រាប់ភាពเข้ากันបានសកល។',
        'cachyconfs': 'ការកំណត់រចនាសម្ព័ន្ធរបស់ CachyOS systemd'
    },
    'lo': {
        'cachyconfs_desc': 'ການຕັ້ງຄ່າທີ່ໄດ້ຮັບການປັບປຸງເພື່ອການປະຕິບັດງານທີ່ດີກວ່າ ແລະການຕອບສະໜອງ, ແລະການສ້ອມແປງນ້ອຍໆສໍາລັບບັນຫາທົ່ວໄປທີ່ໃຊ້ເປັນຄ່າເລີ່ມຕົ້ນໃນ CachyOS, ຖືກກັ່ນຕອງເພື່ອການເຂົ້າກັນໄດ້ທົ່ວໂລກ.',
        'cachyconfs': 'ການຕັ້ງຄ່າ systemd CachyOS'
    },
    'lt': {
        'cachyconfs_desc': 'Optimizuotos konfigūracijos geresniam našumui ir atsiliepimui, taip pat nedideli pataisymai tipiškoms problemoms, kurios naudojamos pagal numatytuosius nustatymus CachyOS, filtruojamos universaliu suderinamumui.',
        'cachyconfs': 'CachyOS systemd konfigūracija'
    },
    'lv': {
        'cachyconfs_desc': 'Optimizētas konfigurācijas labākai veiktspējai un atsaucībai, kā arī nelieli labojumi tipiskām problēmām, kas tiek izmantotas pēc noklusējuma CachyOS, filtrētas universālai saderībai.',
        'cachyconfs': 'CachyOS systemd konfigurācija'
    },
    'mn': {
        'cachyconfs_desc': 'CachyOS-д анхдагч байдлаар ашигладаг илүү сайн гүйцэтгэл ба хариу үйлдэл, мөн ердийн асуудлуудын жижиг засваруудын хувьд оновчлосон тохиргоо, ерөнхий нийцтэй байдлын хувьд шүүсэн.',
        'cachyconfs': 'CachyOS systemd тохиргоо'
    },
    'ms': {
        'cachyconfs_desc': 'Konfigurasi yang dioptimumkan untuk prestasi dan responsiviti yang lebih baik, serta pembaikan kecil untuk masalah biasa yang digunakan secara lalai di CachyOS, ditapis untuk keserasian universal.',
        'cachyconfs': 'Konfigurasi systemd CachyOS'
    },
    'my': {
        'cachyconfs_desc': 'CachyOS တွင် ပုံသေအဖြစ် အသုံးပြုသော ပိုမိုကောင်းမွန်သော စွမ်းဆောင်ရည်နှင့် တုံ့ပြန်မှုအတွက် အကောင်းဆုံး ပြင်ဆင်မှုများ၊ နှင့် ပုံမှန် ပြဿနာများအတွက် သေးငယ်သော ပြင်ဆင်မှုများ၊ ကမ္ဘာလုံးဆိုင်ရာ တွဲဖက်အသုံးပြုနိုင်မှုအတွက် စစ်ထုတ်ထားသည်။',
        'cachyconfs': 'CachyOS systemd ပြင်ဆင်မှု'
    },
    'nb': {
        'cachyconfs_desc': 'Optimaliserte konfigurasjoner for bedre ytelse og responsivitet, samt små rettelser for typiske problemer som brukes som standard på CachyOS, filtrert for universell kompatibilitet.',
        'cachyconfs': 'CachyOS systemd konfigurasjon'
    },
    'ne': {
        'cachyconfs_desc': 'CachyOS मा पूर्वनिर्धारित रूपमा प्रयोग गरिने राम्रो प्रदर्शन र प्रतिक्रियाका लागि अनुकूलित कन्फिगरेसनहरू, र विशिष्ट समस्याहरूका लागि साना सुधारहरू, विश्वव्यापी अनुकूलताका लागि फिल्टर गरिएको।',
        'cachyconfs': 'CachyOS systemd कन्फिगरेसन'
    },
    'ro': {
        'cachyconfs_desc': 'Configurații optimizate pentru performanță și responsivitate mai bune, precum și mici remedieri pentru probleme tipice utilizate implicit în CachyOS, filtrate pentru compatibilitate universală.',
        'cachyconfs': 'Configurație systemd CachyOS'
    },
    'sk': {
        'cachyconfs_desc': 'Optimalizované konfigurácie pre lepší výkon a odozvu, ako aj malé opravy typických problémov používaných štandardne v CachyOS, filtrované pre univerzálnu kompatibilitu.',
        'cachyconfs': 'Konfigurácia systemd CachyOS'
    },
    'sl': {
        'cachyconfs_desc': 'Optimizirane konfiguracije za boljšo učinkovitost in odzivnost, kot tudi majhne popravke za tipične težave, ki se uporabljajo privzeto v CachyOS, filtrirane za univerzalno združljivost.',
        'cachyconfs': 'Konfiguracija systemd CachyOS'
    },
    'sq': {
        'cachyconfs_desc': 'Konfigurime të optimizuara për performancë dhe përgjegjshmëri më të mirë, si dhe riparime të vogla për probleme tipike që përdoren si parazgjedhje në CachyOS, të filtruara për pajtueshmëri universale.',
        'cachyconfs': 'Konfigurimi systemd CachyOS'
    },
    'sr': {
        'cachyconfs_desc': 'Оптимизоване конфигурације за боље перформансе и одзивност, као и мале исправке за типичне проблеме који се користе подразумевано у CachyOS-у, филтриране за универзалну компатибилност.',
        'cachyconfs': 'Конфигурација systemd CachyOS'
    },
    'sw': {
        'cachyconfs_desc': 'Mipangilio iliyoboreshwa kwa utendaji bora na majibu, na marekebisho madogo kwa matatizo ya kawaida yanayotumiwa kwa chaguo-msingi kwenye CachyOS, yaliyochujwa kwa uwezo wa kuoana ulimwenguni.',
        'cachyconfs': 'Mpangilio wa systemd wa CachyOS'
    },
    'ta': {
        'cachyconfs_desc': 'CachyOS-ல் இயல்பாகப் பயன்படுத்தப்படும் சிறந்த செயல்பாடு மற்றும் பதிலளிக்கும் தன்மைக்கான மேம்படுத்தப்பட்ட கட்டமைப்புகள், மற்றும் பொதுவான சிக்கல்களுக்கு சிறிய சரிசெய்தல்கள், உலகளாவிய இணக்கத்திற்காக வடிகட்டப்பட்டது.',
        'cachyconfs': 'CachyOS systemd கட்டமைப்பு'
    },
    'tg': {
        'cachyconfs_desc': 'Барои иҷрои беҳтар ва ҷавобгӯӣ, инчунин ислоҳоти хурд барои мушкилоти типикӣ, ки дар CachyOS бо нобаёнӣ истифода мешаванд, барои мутобиқати умумиҷаҳонӣ филтршуда.',
        'cachyconfs': 'Танзимоти systemd CachyOS'
    },
    'th': {
        'cachyconfs_desc': 'การกำหนดค่าที่ปรับให้เหมาะสมสำหรับประสิทธิภาพและการตอบสนองที่ดีขึ้น รวมถึงการแก้ไขเล็กน้อยสำหรับปัญหาทั่วไปที่ใช้โดยค่าเริ่มต้นใน CachyOS กรองสำหรับความเข้ากันได้สากล',
        'cachyconfs': 'การกำหนดค่า systemd CachyOS'
    },
    'tl': {
        'cachyconfs_desc': 'Mga na-optimize na configuration para sa mas mahusay na pagganap at responsiveness, pati na rin maliit na mga fix para sa mga tipikal na isyu na ginagamit bilang default sa CachyOS, na-filter para sa universal na compatibility.',
        'cachyconfs': 'CachyOS systemd Configuration'
    },
    'tr': {
        'cachyconfs_desc': 'CachyOS\'ta varsayılan olarak kullanılan daha iyi performans ve yanıt verme için optimize edilmiş yapılandırmalar ve tipik sorunlar için küçük düzeltmeler, evrensel uyumluluk için filtrelenmiştir.',
        'cachyconfs': 'CachyOS systemd Yapılandırması'
    },
    'uk': {
        'cachyconfs_desc': 'Оптимізовані конфігурації для кращої продуктивності та чутливості, а також невеликі виправлення для типових проблем, які використовуються за замовчуванням у CachyOS, відфільтровані для універсальної сумісності.',
        'cachyconfs': 'Конфігурація systemd CachyOS'
    },
    'ur': {
        'cachyconfs_desc': 'CachyOS پر پہلے سے طے شدہ طور پر استعمال ہونے والی بہتر کارکردگی اور ردعمل کے لیے بہتر کردہ کنفیگریشنز، اور عام مسائل کے لیے چھوٹے اصلاحات، عالمی مطابقت کے لیے فلٹر کیے گئے۔',
        'cachyconfs': 'CachyOS systemd کنفیگریشن'
    },
    'uz': {
        'cachyconfs_desc': 'CachyOS-da sukut bo\'yicha ishlatiladigan yaxshi ishlash va javob berish uchun optimallashtirilgan konfiguratsiyalar, shuningdek, tipik muammolar uchun kichik tuzatishlar, universal moslik uchun filtrlangan.',
        'cachyconfs': 'CachyOS systemd konfiguratsiyasi'
    },
    'vi': {
        'cachyconfs_desc': 'Cấu hình được tối ưu hóa cho hiệu suất và khả năng đáp ứng tốt hơn, cũng như các bản sửa lỗi nhỏ cho các vấn đề điển hình được sử dụng mặc định trên CachyOS, được lọc cho khả năng tương thích phổ quát.',
        'cachyconfs': 'Cấu hình systemd CachyOS'
    }
}

lang_dir = '/var/home/psygreg/hdd/dev/linuxtoys/p3/libs/lang'

for lang, trans in translations.items():
    file_path = os.path.join(lang_dir, f'{lang}.json')
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for key, value in trans.items():
            data[key] = value
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f'Updated {lang}.json')
    else:
        print(f'File {lang}.json not found')
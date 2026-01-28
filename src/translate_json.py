import json
import os

# Directory containing the language files
lang_dir = '../p3/libs/lang/'

# Translations dictionary: key -> {lang_code: translation}
translations = {
    'nala_desc': {
        'am': 'ለ libapt-pkg የተሻሻለ የውፅዓት ቅርጸት እና ትይዩ አውርድ ድጋፍ ያለው በይነገፅ።',
        'ar': 'واجهة لـ libapt-pkg مع تنسيق إخراج أفضل ودعم التنزيل المتوازي.',
        'az': 'Daha yaxşı çıxış formatlaşdırması və paralel yükləmə dəstəyi ilə libapt-pkg üçün interfeys.',
        'bg': 'Интерфейс за libapt-pkg с по-добро форматиране на изхода и поддръжка на паралелно изтегляне.',
        'bn': 'উন্নত আউটপুট ফর্ম্যাটিং এবং সমান্তরাল ডাউনলোড সমর্থন সহ libapt-pkg এর জন্য একটি ইন্টারফেস।',
        'bs': 'Interfejs za libapt-pkg sa boljim formatiranjem izlaza i podrškom za paralelno preuzimanje.',
        'cs': 'Rozhraní pro libapt-pkg s lepším formátováním výstupu a podporou paralelního stahování.',
        'da': 'En grænseflade til libapt-pkg med bedre outputformatering og parallel downloadunderstøttelse.',
        'de': 'Eine Schnittstelle für libapt-pkg mit besserer Ausgabeformatierung und Unterstützung für paralleles Herunterladen.',
        'el': 'Μια διεπαφή για το libapt-pkg με καλύτερη μορφοποίηση εξόδου και υποστήριξη παράλληλης λήψης.',
        'es': 'Una interfaz para libapt-pkg con mejor formato de salida y soporte para descarga paralela.',
        'et': 'Liides libapt-pkg jaoks parema väljundi vorminduse ja paralleelse allalaadimise toega.',
        'fa': 'یک رابط برای libapt-pkg با قالب‌بندی خروجی بهتر و پشتیبانی از دانلود موازی.',
        'fi': 'Käyttöliittymä libapt-pkg:lle paremmalla tulosteen muotoilulla ja rinnakkaisen latauksen tuella.',
        'fr': 'Une interface pour libapt-pkg avec un meilleur formatage de sortie et un support de téléchargement parallèle.',
        'ga': 'Comhéadan le haghaidh libapt-pkg le formáidiú aschuir níos fearr agus tacaíocht íoslódála comhthreomhar.',
        'he': 'ממשק ל-libapt-pkg עם עיצוב פלט משופר ותמיכה בהורדה מקבילה.',
        'hi': 'बेहतर आउटपुट फॉर्मेटिंग और समानांतर डाउनलोड समर्थन के साथ libapt-pkg के लिए एक इंटरफ़ेस।',
        'hr': 'Sučelje za libapt-pkg s boljim formatiranjem izlaza i podrškom za paralelno preuzimanje.',
        'hu': 'Egy felület a libapt-pkg számára jobb kimeneti formázással és párhuzamos letöltés támogatással.',
        'hy': 'Միջերես libapt-pkg-ի համար ավելի լավ ելքի ձևաչափավորմամբ և զուգահեռ ներբեռնման աջակցությամբ:',
        'id': 'Antarmuka untuk libapt-pkg dengan pemformatan output yang lebih baik dan dukungan unduhan paralel.',
        'is': 'Viðmót fyrir libapt-pkg með betri úttaksformi og stuðning við samhliða niðurhal.',
        'it': 'Un\'interfaccia per libapt-pkg con una migliore formattazione dell\'output e supporto per il download parallelo.',
        'ja': 'より良い出力フォーマットと並列ダウンロードサポートを備えたlibapt-pkgのインターフェース。',
        'ka': 'ინტერფეისი libapt-pkg-სთვის უკეთესი გამოსავლის ფორმატირებით და პარალელური ჩამოტვირთვის მხარდაჭერით.',
        'km': 'ចំណុចប្រទាក់សម្រាប់ libapt-pkg ជាមួយការធ្វើទ្រង់ទ្រាយលទ្ធផលប្រសើរជាងនិងការគាំទ្រការទាញយកស្របគ្នា។',
        'ko': '더 나은 출력 형식 및 병렬 다운로드 지원을 갖춘 libapt-pkg 인터페이스입니다.',
        'lo': 'ການໂຕ້ຕອບສໍາລັບ libapt-pkg ດ້ວຍການຈັດຮູບແບບຜົນໄດ້ຮັບທີ່ດີກວ່າແລະການສະໜັບສະໜູນການດາວໂຫລດແບບຂະຫນານ.',
        'lt': 'Sąsaja libapt-pkg su geresniu išvesties formatavimu ir lygiagrečios atsisiuntimo palaikymu.',
        'lv': 'Saskarne libapt-pkg ar labāku izvades formatēšanu un paralēlās lejupielādes atbalstu.',
        'mn': 'Илүү сайн гаралтын форматтай болон зэрэгцээ татаж авалтын дэмжлэгтэй libapt-pkg-ийн интерфэйс.',
        'ms': 'Antara muka untuk libapt-pkg dengan pemformatan output yang lebih baik dan sokongan muat turun selari.',
        'my': 'ပိုမိုကောင်းမွန်သော ထွက်ရှိချက် ဖော်မတ်ပြုလုပ်ခြင်းနှင့် အပြိုင်ဒေါင်းလုဒ်ထောက်ပံ့မှုဖြင့် libapt-pkg အတွက် အင်တာဖေ့စ်။',
        'nb': 'Et grensesnitt for libapt-pkg med bedre utdataformatering og støtte for parallell nedlasting.',
        'ne': 'राम्रो आउटपुट ढाँचा र समानान्तर डाउनलोड समर्थन सहित libapt-pkg को लागि एक इन्टरफेस।',
        'nl': 'Een interface voor libapt-pkg met betere uitvoeropmaak en ondersteuning voor parallel downloaden.',
        'pl': 'Interfejs dla libapt-pkg z lepszym formatowaniem wyjścia i obsługą równoległego pobierania.',
        'pt': 'Uma interface para libapt-pkg com melhor formatação de saída e suporte para download paralelo.',
        'ro': 'O interfață pentru libapt-pkg cu formatare mai bună a ieșirii și suport pentru descărcare paralelă.',
        'ru': 'Интерфейс для libapt-pkg с улучшенным форматированием вывода и поддержкой параллельной загрузки.',
        'sk': 'Rozhranie pre libapt-pkg s lepším formátovaním výstupu a podporou paralelného sťahovania.',
        'sl': 'Vmesnik za libapt-pkg z boljšim oblikovanjem izhoda in podporo za vzporedno prenašanje.',
        'sq': 'Një ndërfaqe për libapt-pkg me formatim më të mirë të daljes dhe mbështetje për shkarkimin paralel.',
        'sr': 'Интерфејс за libapt-pkg са бољим форматирањем излаза и подршком за паралелно преузимање.',
        'sv': 'Ett gränssnitt för libapt-pkg med bättre utdataformatering och stöd för parallell nedladdning.',
        'sw': 'Kiolesura cha libapt-pkg chenye muundo bora wa matokeo na msaada wa kupakua kwa uwazi.',
        'ta': 'சிறந்த வெளியீடு வடிவமைப்பு மற்றும் இணையான பதிவிறக்க ஆதரவுடன் libapt-pkg க்கான இடைமுகம்.',
        'tg': 'Интерфейс барои libapt-pkg бо қолаббандии беҳтари натиҷа ва дастгирии боргирии паралелӣ.',
        'th': 'อินเทอร์เฟซสำหรับ libapt-pkg ที่มีการจัดรูปแบบเอาต์พุตที่ดีขึ้นและการสนับสนุนการดาวน์โหลดแบบขนาน',
        'tl': 'Isang interface para sa libapt-pkg na may mas mahusay na pag-format ng output at suporta sa parallel na pag-download.',
        'tr': 'Daha iyi çıktı biçimlendirmesi ve paralel indirme desteği ile libapt-pkg için bir arayüz.',
        'uk': 'Інтерфейс для libapt-pkg з кращим форматуванням виводу та підтримкою паралельного завантаження.',
        'ur': 'بہتر آؤٹ پٹ فارمیٹنگ اور متوازی ڈاؤن لوڈ سپورٹ کے ساتھ libapt-pkg کے لیے ایک انٹرفیس۔',
        'uz': 'Yaxshi chiqish formatlash va parallel yuklab olish qo\'llab-quvvatlash bilan libapt-pkg uchun interfeys.',
        'vi': 'Giao diện cho libapt-pkg với định dạng đầu ra tốt hơn và hỗ trợ tải xuống song song.',
        'zh': '一个用于 libapt-pkg 的界面，具有更好的输出格式和并行下载支持。'
    },

    'glight_desc': {
        'am': 'የማህበረሰብ ሰሪው የ Xbox አውትድ ክላይንት።',
        'ar': 'عميل مجتمعي لـ Xbox XCloud.',
        'az': 'Xbox XCloud üçün icma tərəfindən hazırlanmış müştəri.',
        'bg': 'Клиент, създаден от общността за Xbox XCloud.',
        'bn': 'Xbox এর XCloud এর জন্য একটি সম্প্রদায়-নির্মিত ক্লায়েন্ট।',
        'bs': 'Klijent napravljen od strane zajednice za Xbox XCloud.',
        'cs': 'Klient vytvořený komunitou pro Xbox XCloud.',
        'da': 'En klient lavet af fællesskabet til Xbox XCloud.',
        'de': 'Ein von der Community erstellter Client für Xbox XCloud.',
        'el': 'Ένας πελάτης που δημιουργήθηκε από την κοινότητα για το Xbox XCloud.',
        'es': 'Un cliente hecho por la comunidad para Xbox XCloud.',
        'et': 'Ühenduse loodud klient Xbox XCloud jaoks.',
        'fa': 'یک کلاینت ساخته شده توسط جامعه برای Xbox XCloud.',
        'fi': 'Yhteisön tekemä asiakas Xbox XCloudille.',
        'fr': 'Un client créé par la communauté pour Xbox XCloud.',
        'ga': 'Cliant déanta ag an bpobal do Xbox XCloud.',
        'he': 'לקוח שנוצר על ידי הקהילה עבור Xbox XCloud.',
        'hi': 'Xbox XCloud के लिए एक समुदाय-निर्मित ग्राहक।',
        'hr': 'Klijent izrađen od strane zajednice za Xbox XCloud.',
        'hu': 'Egy közösség által készített kliens az Xbox XCloud-hoz.',
        'hy': 'Համայնքի կողմից ստեղծված հաճախորդ Xbox XCloud-ի համար:',
        'id': 'Klien buatan komunitas untuk Xbox XCloud.',
        'is': 'Viðskiptavinur gerður af samfélaginu fyrir Xbox XCloud.',
        'it': 'Un client creato dalla comunità per Xbox XCloud.',
        'ja': 'Xbox XCloud のコミュニティ製クライアント。',
        'ka': 'კლიენტი, რომელიც შექმნა საზოგადოებამ Xbox XCloud-ისთვის.',
        'km': 'ម៉ាស៊ីនភ្ញៀវដែលបានបង្កើតដោយសហគមន៍សម្រាប់ Xbox XCloud។',
        'ko': 'Xbox XCloud를 위한 커뮤니티 제작 클라이언트.',
        'lo': 'ລູກຄ້າທີ່ສ້າງຂື້ນຈາກຊຸມຊົນສໍາລັບ Xbox XCloud.',
        'lt': 'Bendruomenės sukurtas klientas Xbox XCloud.',
        'lv': 'Kopienas izveidots klients Xbox XCloud.',
        'mn': 'Xbox XCloud-д зориулсан нийгэмлэгээр бүтээсэн үйлчлүүлэгч.',
        'ms': 'Klien buatan komuniti untuk Xbox XCloud.',
        'my': 'Xbox XCloud အတွက် အသိုင်းအဝိုင်းဖန်တီးထားသော လက်ခံသူ။',
        'nb': 'En klient laget av fellesskapet for Xbox XCloud.',
        'ne': 'Xbox XCloud को लागि समुदाय-निर्मित ग्राहक।',
        'nl': 'Een door de gemeenschap gemaakte client voor Xbox XCloud.',
        'pl': 'Klient stworzony przez społeczność dla Xbox XCloud.',
        'pt': 'Um cliente feito pela comunidade para Xbox XCloud.',
        'ro': 'Un client creat de comunitate pentru Xbox XCloud.',
        'ru': 'Клиент, созданный сообществом для Xbox XCloud.',
        'sk': 'Klient vytvorený komunitou pre Xbox XCloud.',
        'sl': 'Odjemalec, ki ga je ustvarila skupnost za Xbox XCloud.',
        'sq': 'Një klient i bërë nga komuniteti për Xbox XCloud.',
        'sr': 'Клијент направљен од стране заједнице за Xbox XCloud.',
        'sv': 'En klient gjord av gemenskapen för Xbox XCloud.',
        'sw': 'Mteja aliyetengenezwa na jamii kwa Xbox XCloud.',
        'ta': 'Xbox XCloud க்கான ஒரு சமூகம்-உருவாக்கிய வாடிக்கையாளர்.',
        'tg': 'Мизоҷи сохташудаи ҷомеа барои Xbox XCloud.',
        'th': 'ลูกค้าที่สร้างโดยชุมชนสำหรับ Xbox XCloud',
        'tl': 'Isang kliyente na ginawa ng komunidad para sa Xbox XCloud.',
        'tr': 'Xbox XCloud için topluluk tarafından yapılan bir istemci.',
        'uk': 'Клієнт, створений спільнотою для Xbox XCloud.',
        'ur': 'Xbox XCloud کے لیے کمیونٹی کی طرف سے بنایا گیا کلائنٹ۔',
        'uz': 'Xbox XCloud uchun hamjamiyat tomonidan yaratilgan mijoz.',
        'vi': 'Một ứng dụng khách được tạo bởi cộng đồng cho Xbox XCloud.',
        'zh': 'Xbox XCloud 的社区制作客户端。'
    }
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
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
    "specials_desc": {
        "am": "በLinuxToys የተመረጡ ሶፍትዌሮች እና የመጫኛ ስክሪፕቶች።",
        "ar": "برامج ونصوص تثبيت منتقاة من LinuxToys.",
        "az": "LinuxToys tərəfindən seçilmiş proqram təminatı və quraşdırma skriptləri.",
        "bg": "Софтуер и инсталационни скриптове, подбрани от LinuxToys.",
        "bn": "LinuxToys দ্বারা নির্বাচিত সফটওয়্যার এবং ইনস্টলেশন স্ক্রিপ্ট।",
        "bs": "Softver i instalacijske skripte koje je odabrao LinuxToys.",
        "cs": "Software a instalační skripty vybrané LinuxToys.",
        "da": "Software og installationsscripts udvalgt af LinuxToys.",
        "de": "Von LinuxToys ausgewählte Software und Installationsskripte.",
        "el": "Λογισμικό και σενάρια εγκατάστασης επιλεγμένα από το LinuxToys.",
        "es": "Software y scripts de instalación seleccionados por LinuxToys.",
        "et": "LinuxToysi valitud tarkvara ja paigaldusskriptid.",
        "fa": "نرم‌افزارها و اسکریپت‌های نصب منتخب LinuxToys.",
        "fi": "LinuxToysin valitsemat ohjelmistot ja asennusskriptit.",
        "fr": "Logiciels et scripts d’installation sélectionnés par LinuxToys.",
        "ga": "Bogearraí agus scripteanna suiteála roghnaithe ag LinuxToys.",
        "he": "תוכנות וסקריפטים להתקנה שנבחרו על ידי LinuxToys.",
        "hi": "LinuxToys द्वारा चुने गए सॉफ़्टवेयर और इंस्टॉलेशन स्क्रिप्ट।",
        "hr": "Softver i instalacijske skripte koje je odabrao LinuxToys.",
        "hu": "A LinuxToys által válogatott szoftverek és telepítési szkriptek.",
        "hy": "LinuxToys-ի կողմից ընտրված ծրագրեր և տեղադրման սկրիպտներ։",
        "id": "Perangkat lunak dan skrip instalasi pilihan LinuxToys.",
        "is": "Hugbúnaður og uppsetningarskriftur valdar af LinuxToys.",
        "it": "Software e script di installazione selezionati da LinuxToys.",
        "ja": "LinuxToysが厳選したソフトウェアとインストールスクリプト。",
        "ka": "LinuxToys-ის მიერ შერჩეული პროგრამები და ინსტალაციის სკრიპტები.",
        "km": "កម្មវិធី និងស្គ្រីបដំឡើងដែលជ្រើសរើសដោយ LinuxToys។",
        "ko": "LinuxToys가 엄선한 소프트웨어 및 설치 스크립트.",
        "lo": "ຊອບແວ ແລະ ສະຄຣິບຕິດຕັ້ງທີ່ຄັດເລືອກໂດຍ LinuxToys.",
        "lt": "LinuxToys atrinkta programinė įranga ir diegimo scenarijai.",
        "lv": "LinuxToys atlasīta programmatūra un instalēšanas skripti.",
        "mn": "LinuxToys-оос сонгосон програм хангамж болон суулгах скриптүүд.",
        "ms": "Perisian dan skrip pemasangan pilihan LinuxToys.",
        "my": "LinuxToys မှ ရွေးချယ်ထားသော ဆော့ဖ်ဝဲနှင့် တပ်ဆင်ရေး script များ။",
        "nb": "Programvare og installasjonsskript utvalgt av LinuxToys.",
        "ne": "LinuxToys द्वारा छानिएका सफ्टवेयर र स्थापना स्क्रिप्टहरू।",
        "nl": "Door LinuxToys geselecteerde software en installatiescripts.",
        "pl": "Oprogramowanie i skrypty instalacyjne wybrane przez LinuxToys.",
        "pt": "Softwares e scripts de instalação selecionados pelo LinuxToys.",
        "ro": "Software și scripturi de instalare selectate de LinuxToys.",
        "ru": "Программы и сценарии установки, отобранные LinuxToys.",
        "sk": "Softvér a inštalačné skripty vybrané LinuxToys.",
        "sl": "Programska oprema in namestitveni skripti, ki jih je izbral LinuxToys.",
        "sq": "Programe dhe skripte instalimi të përzgjedhura nga LinuxToys.",
        "sr": "Софтвер и инсталационе скрипте које је одабрао LinuxToys.",
        "sv": "Programvara och installationsskript utvalda av LinuxToys.",
        "sw": "Programu na hati za usakinishaji zilizochaguliwa na LinuxToys.",
        "ta": "LinuxToys தேர்ந்தெடுத்த மென்பொருட்கள் மற்றும் நிறுவல் ஸ்கிரிப்ட்கள்.",
        "tg": "Нармафзор ва скриптҳои насбкунӣ, ки аз ҷониби LinuxToys интихоб шудаанд.",
        "th": "ซอฟต์แวร์และสคริปต์ติดตั้งที่คัดสรรโดย LinuxToys",
        "tl": "Software at mga script sa pag-install na pinili ng LinuxToys.",
        "tr": "LinuxToys tarafından seçilen yazılımlar ve kurulum betikleri.",
        "uk": "Програми та сценарії встановлення, відібрані LinuxToys.",
        "ur": "LinuxToys کے منتخب کردہ سافٹ ویئر اور انسٹالیشن اسکرپٹس۔",
        "uz": "LinuxToys tomonidan saralangan dasturlar va o‘rnatish skriptlari.",
        "vi": "Phần mềm và tập lệnh cài đặt do LinuxToys tuyển chọn.",
        "zh": "由 LinuxToys 精选的软件和安装脚本。"
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

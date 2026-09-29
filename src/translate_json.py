import json
import os

# Directory containing the language files
lang_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "p3/libs/lang/")

# Translations dictionary: key -> {lang_code: translation}
translations = {
    "snap_desc": {
        "am": "የCanonical Snapcraft ማከማቻዎች ከsnapd አገልግሎታቸው ጋር።",
        "ar": "مستودعات Canonical Snapcraft مع خدمة snapd الخاصة بها.",
        "az": "Canonical Snapcraft repozitoriyaları və onların snapd xidməti.",
        "bg": "Хранилищата Canonical Snapcraft с тяхната услуга snapd.",
        "bn": "Canonical Snapcraft রিপোজিটরি এবং এর snapd পরিষেবা।",
        "bs": "Canonical Snapcraft repozitoriji s njihovom snapd uslugom.",
        "cs": "Repozitáře Canonical Snapcraft se službou snapd.",
        "da": "Canonical Snapcraft-arkiver med deres snapd-tjeneste.",
        "de": "Canonical-Snapcraft-Paketquellen mit dem zugehörigen snapd-Dienst.",
        "el": "Αποθετήρια Canonical Snapcraft με την υπηρεσία snapd.",
        "es": "Repositorios de Canonical Snapcraft con su servicio snapd.",
        "et": "Canonical Snapcrafti hoidlad koos snapd-teenusega.",
        "fa": "مخازن Canonical Snapcraft به همراه سرویس snapd.",
        "fi": "Canonical Snapcraft -pakettivarastot ja niiden snapd-palvelu.",
        "fr": "Dépôts Canonical Snapcraft avec leur service snapd.",
        "ga": "Stórtha Canonical Snapcraft lena seirbhís snapd.",
        "he": "מאגרי Canonical Snapcraft עם שירות snapd שלהם.",
        "hi": "Canonical Snapcraft रिपॉज़िटरी और उनकी snapd सेवा।",
        "hr": "Canonical Snapcraft repozitoriji s njihovom uslugom snapd.",
        "hu": "Canonical Snapcraft-tárolók a hozzájuk tartozó snapd szolgáltatással.",
        "hy": "Canonical Snapcraft շտեմարանները՝ իրենց snapd ծառայությամբ։",
        "id": "Repositori Canonical Snapcraft beserta layanan snapd.",
        "is": "Canonical Snapcraft-hugbúnaðarsöfn með snapd-þjónustunni.",
        "it": "Repository Canonical Snapcraft con il relativo servizio snapd.",
        "ja": "snapd サービスを使用する Canonical Snapcraft リポジトリ。",
        "ka": "Canonical Snapcraft-ის რეპოზიტორიები snapd სერვისთან ერთად.",
        "km": "ឃ្លាំង Canonical Snapcraft ជាមួយសេវាកម្ម snapd របស់វា។",
        "ko": "snapd 서비스를 사용하는 Canonical Snapcraft 저장소.",
        "lo": "ຄັງຊອບແວ Canonical Snapcraft ພ້ອມກັບບໍລິການ snapd.",
        "lt": "Canonical Snapcraft saugyklos su snapd paslauga.",
        "lv": "Canonical Snapcraft repozitoriji ar snapd pakalpojumu.",
        "mn": "Canonical Snapcraft репозиторууд болон тэдгээрийн snapd үйлчилгээ.",
        "ms": "Repositori Canonical Snapcraft bersama perkhidmatan snapd.",
        "my": "Canonical Snapcraft repository များနှင့် ၎င်းတို့၏ snapd service။",
        "nb": "Canonical Snapcraft-pakkebrønner med tilhørende snapd-tjeneste.",
        "ne": "Canonical Snapcraft रिपोजिटरीहरू र तिनको snapd सेवा।",
        "nl": "Canonical Snapcraft-pakketbronnen met de bijbehorende snapd-service.",
        "pl": "Repozytoria Canonical Snapcraft wraz z usługą snapd.",
        "pt": "Repositórios Snapcraft da Canonical com seu serviço snapd.",
        "ro": "Depozitele Canonical Snapcraft împreună cu serviciul snapd.",
        "ru": "Репозитории Canonical Snapcraft вместе со службой snapd.",
        "sk": "Repozitáre Canonical Snapcraft so službou snapd.",
        "sl": "Repozitoriji Canonical Snapcraft s storitvijo snapd.",
        "sq": "Depot e Canonical Snapcraft me shërbimin e tyre snapd.",
        "sr": "Canonical Snapcraft репозиторијуми са њиховом snapd услугом.",
        "sv": "Canonical Snapcraft-förråd med tillhörande snapd-tjänst.",
        "sw": "Hazina za Canonical Snapcraft pamoja na huduma yake ya snapd.",
        "ta": "Canonical Snapcraft மென்பொருள் களஞ்சியங்கள் மற்றும் அதன் snapd சேவை.",
        "tg": "Анборҳои Canonical Snapcraft бо хидмати snapd.",
        "th": "คลัง Canonical Snapcraft พร้อมบริการ snapd",
        "tl": "Mga repository ng Canonical Snapcraft kasama ang snapd service nito.",
        "tr": "Canonical Snapcraft depoları ve bunların snapd hizmeti.",
        "uk": "Репозиторії Canonical Snapcraft разом зі службою snapd.",
        "ur": "Canonical Snapcraft ریپوزٹریز اور ان کی snapd سروس۔",
        "uz": "Canonical Snapcraft repozitoriylari va ularning snapd xizmati.",
        "vi": "Các kho phần mềm Canonical Snapcraft cùng với dịch vụ snapd.",
        "zh": "Canonical Snapcraft 软件仓库及其 snapd 服务。"
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

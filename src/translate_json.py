import json
import os

# Directory containing the language files
lang_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "p3/libs/lang/")

# Translations dictionary: key -> {lang_code: translation}
translations = {
    "resolveaac_desc": {
        "am": "በLinux ላይ ለDaVinci Resolve Studio የAAC ማስመጣት/ማጫወት እና ወደ ውጭ መላክ።",
        "ar": "استيراد/تشغيل وتصدير AAC في DaVinci Resolve Studio على Linux.",
        "az": "Linux-da DaVinci Resolve Studio üçün AAC idxalı/oxudulması və ixracı.",
        "bg": "Импортиране/възпроизвеждане и експортиране на AAC за DaVinci Resolve Studio под Linux.",
        "bn": "Linux-এ DaVinci Resolve Studio-এর জন্য AAC ইমপোর্ট/প্লেব্যাক এবং এক্সপোর্ট।",
        "bs": "AAC uvoz/reprodukcija i izvoz za DaVinci Resolve Studio na Linuxu.",
        "cs": "Import/přehrávání a export AAC pro DaVinci Resolve Studio v Linuxu.",
        "da": "AAC-import/afspilning og eksport til DaVinci Resolve Studio på Linux.",
        "de": "AAC-Import/-Wiedergabe und -Export für DaVinci Resolve Studio unter Linux.",
        "el": "Εισαγωγή/αναπαραγωγή και εξαγωγή AAC για το DaVinci Resolve Studio στο Linux.",
        "es": "Importación/reproducción y exportación de AAC para DaVinci Resolve Studio en Linux.",
        "et": "AAC import/esitus ja eksport DaVinci Resolve Studio jaoks Linuxis.",
        "fa": "وارد کردن/پخش و خروجی AAC برای DaVinci Resolve Studio در Linux.",
        "fi": "AAC-tuonti/toisto ja vienti DaVinci Resolve Studioon Linuxissa.",
        "fr": "Importation/lecture et exportation AAC pour DaVinci Resolve Studio sous Linux.",
        "ga": "Iompórtáil/athsheinm agus easpórtáil AAC do DaVinci Resolve Studio ar Linux.",
        "he": "ייבוא/השמעה וייצוא של AAC עבור DaVinci Resolve Studio ב-Linux.",
        "hi": "Linux पर DaVinci Resolve Studio के लिए AAC इंपोर्ट/प्लेबैक और एक्सपोर्ट।",
        "hr": "AAC uvoz/reprodukcija i izvoz za DaVinci Resolve Studio na Linuxu.",
        "hu": "AAC-import/lejátszás és exportálás a DaVinci Resolve Studio számára Linuxon.",
        "hy": "AAC ներմուծում/նվագարկում և արտահանում DaVinci Resolve Studio-ի համար Linux-ում։",
        "id": "Impor/pemutaran dan ekspor AAC untuk DaVinci Resolve Studio di Linux.",
        "is": "AAC-innflutningur/afspilun og útflutningur fyrir DaVinci Resolve Studio á Linux.",
        "it": "Importazione/riproduzione ed esportazione AAC per DaVinci Resolve Studio su Linux.",
        "ja": "Linux 版 DaVinci Resolve Studio での AAC のインポート/再生およびエクスポート。",
        "ka": "AAC-ის იმპორტი/დაკვრა და ექსპორტი DaVinci Resolve Studio-სთვის Linux-ზე.",
        "km": "ការនាំចូល/ចាក់ និងនាំចេញ AAC សម្រាប់ DaVinci Resolve Studio លើ Linux។",
        "ko": "Linux용 DaVinci Resolve Studio에서 AAC 가져오기/재생 및 내보내기.",
        "lo": "ການນຳເຂົ້າ/ຫຼິ້ນ ແລະ ສົ່ງອອກ AAC ສຳລັບ DaVinci Resolve Studio ເທິງ Linux.",
        "lt": "AAC importavimas / atkūrimas ir eksportavimas „DaVinci Resolve Studio“ sistemoje „Linux“.",
        "lv": "AAC importēšana/atskaņošana un eksportēšana DaVinci Resolve Studio operētājsistēmā Linux.",
        "mn": "Linux дээрх DaVinci Resolve Studio-д AAC импорт/тоглуулах болон экспортлох.",
        "ms": "Import/main balik dan eksport AAC untuk DaVinci Resolve Studio di Linux.",
        "my": "Linux ပေါ်ရှိ DaVinci Resolve Studio အတွက် AAC import/playback နှင့် export။",
        "nb": "AAC-import/avspilling og eksport for DaVinci Resolve Studio på Linux.",
        "ne": "Linux मा DaVinci Resolve Studio का लागि AAC आयात/प्लेब्याक र निर्यात।",
        "nl": "AAC-import/-afspelen en export voor DaVinci Resolve Studio op Linux.",
        "pl": "Import/odtwarzanie i eksport AAC dla DaVinci Resolve Studio w systemie Linux.",
        "pt": "Importação/reprodução e exportação de AAC para o DaVinci Resolve Studio no Linux.",
        "ro": "Import/redare și export AAC pentru DaVinci Resolve Studio pe Linux.",
        "ru": "Импорт/воспроизведение и экспорт AAC для DaVinci Resolve Studio в Linux.",
        "sk": "Import/prehrávanie a export AAC pre DaVinci Resolve Studio v Linuxe.",
        "sl": "Uvoz/predvajanje in izvoz AAC za DaVinci Resolve Studio v Linuxu.",
        "sq": "Importim/riprodhim dhe eksportim AAC për DaVinci Resolve Studio në Linux.",
        "sr": "AAC увоз/репродукција и извоз за DaVinci Resolve Studio на Linux-у.",
        "sv": "AAC-import/uppspelning och export för DaVinci Resolve Studio på Linux.",
        "sw": "Uingizaji/uchezaji na uhamishaji wa AAC kwa DaVinci Resolve Studio kwenye Linux.",
        "ta": "Linux-இல் DaVinci Resolve Studio-க்கான AAC இறக்குமதி/இயக்கம் மற்றும் ஏற்றுமதி.",
        "tg": "Воридот/пахш ва содироти AAC барои DaVinci Resolve Studio дар Linux.",
        "th": "การนำเข้า/เล่นและส่งออก AAC สำหรับ DaVinci Resolve Studio บน Linux",
        "tl": "Pag-import/pag-playback at pag-export ng AAC para sa DaVinci Resolve Studio sa Linux.",
        "tr": "Linux'ta DaVinci Resolve Studio için AAC içe aktarma/oynatma ve dışa aktarma.",
        "uk": "Імпорт/відтворення та експорт AAC для DaVinci Resolve Studio у Linux.",
        "ur": "Linux پر DaVinci Resolve Studio کے لیے AAC درآمد/پلے بیک اور برآمد۔",
        "uz": "Linux'da DaVinci Resolve Studio uchun AAC import/ijro etish va eksport.",
        "vi": "Nhập/phát và xuất AAC cho DaVinci Resolve Studio trên Linux.",
        "zh": "在 Linux 上为 DaVinci Resolve Studio 提供 AAC 导入/播放和导出支持。"
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

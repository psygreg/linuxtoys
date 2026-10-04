import json
import os

# Directory containing the language files
lang_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "p3/libs/lang/")

# Translations dictionary: key -> {lang_code: translation}
translations = {
    "homebrew_catalog_unavailable": {
        "am": "የHomebrew ሜታዳታ አይገኝም። ቆይተው እንደገና ይሞክሩ።",
        "ar": "بيانات Homebrew الوصفية غير متاحة. حاول مرة أخرى لاحقًا.",
        "az": "Homebrew metadatası əlçatan deyil. Daha sonra yenidən cəhd edin.",
        "bg": "Метаданните на Homebrew не са налични. Опитайте отново по-късно.",
        "bn": "Homebrew মেটাডেটা উপলব্ধ নয়। পরে আবার চেষ্টা করুন।",
        "bs": "Homebrew metapodaci nisu dostupni. Pokušajte ponovo kasnije.",
        "cs": "Metadata Homebrew nejsou dostupná. Zkuste to znovu později.",
        "da": "Homebrew-metadata er ikke tilgængelige. Prøv igen senere.",
        "de": "Homebrew-Metadaten sind nicht verfügbar. Versuchen Sie es später erneut.",
        "el": "Τα μεταδεδομένα του Homebrew δεν είναι διαθέσιμα. Δοκιμάστε ξανά αργότερα.",
        "es": "Los metadatos de Homebrew no están disponibles. Inténtalo de nuevo más tarde.",
        "et": "Homebrew metaandmed pole saadaval. Proovige hiljem uuesti.",
        "fa": "فراداده Homebrew در دسترس نیست. بعداً دوباره تلاش کنید.",
        "fi": "Homebrew-metatiedot eivät ole saatavilla. Yritä myöhemmin uudelleen.",
        "fr": "Les métadonnées Homebrew ne sont pas disponibles. Réessayez plus tard.",
        "ga": "Níl meiteashonraí Homebrew ar fáil. Bain triail eile as ar ball.",
        "he": "מטא-נתוני Homebrew אינם זמינים. נסו שוב מאוחר יותר.",
        "hi": "Homebrew मेटाडेटा उपलब्ध नहीं है। बाद में फिर से प्रयास करें।",
        "hr": "Homebrew metapodaci nisu dostupni. Pokušajte ponovno kasnije.",
        "hu": "A Homebrew metaadatai nem érhetők el. Próbálja újra később.",
        "hy": "Homebrew մետատվյալները հասանելի չեն։ Կրկին փորձեք ավելի ուշ։",
        "id": "Metadata Homebrew tidak tersedia. Coba lagi nanti.",
        "is": "Homebrew-lýsigögn eru ekki tiltæk. Reyndu aftur síðar.",
        "it": "I metadati di Homebrew non sono disponibili. Riprova più tardi.",
        "ja": "Homebrew のメタデータを利用できません。後でもう一度お試しください。",
        "ka": "Homebrew-ის მეტამონაცემები მიუწვდომელია. მოგვიანებით სცადეთ ხელახლა.",
        "km": "ទិន្នន័យមេតា Homebrew មិនអាចប្រើបានទេ។ សូមព្យាយាមម្តងទៀតនៅពេលក្រោយ។",
        "ko": "Homebrew 메타데이터를 사용할 수 없습니다. 나중에 다시 시도하세요.",
        "lo": "ຂໍ້ມູນເມຕາ Homebrew ບໍ່ພ້ອມໃຊ້ງານ. ລອງໃໝ່ພາຍຫຼັງ.",
        "lt": "Homebrew metaduomenys nepasiekiami. Bandykite dar kartą vėliau.",
        "lv": "Homebrew metadati nav pieejami. Mēģiniet vēlreiz vēlāk.",
        "mn": "Homebrew мета өгөгдөл боломжгүй байна. Дараа дахин оролдоно уу.",
        "ms": "Metadata Homebrew tidak tersedia. Cuba lagi kemudian.",
        "my": "Homebrew metadata မရရှိနိုင်ပါ။ နောက်မှ ထပ်စမ်းကြည့်ပါ။",
        "nb": "Homebrew-metadata er utilgjengelige. Prøv igjen senere.",
        "ne": "Homebrew मेटाडेटा उपलब्ध छैन। पछि फेरि प्रयास गर्नुहोस्।",
        "nl": "Homebrew-metadata zijn niet beschikbaar. Probeer het later opnieuw.",
        "pl": "Metadane Homebrew są niedostępne. Spróbuj ponownie później.",
        "pt": "Os metadados do Homebrew estão indisponíveis. Tente novamente mais tarde.",
        "ro": "Metadatele Homebrew nu sunt disponibile. Încercați din nou mai târziu.",
        "ru": "Метаданные Homebrew недоступны. Повторите попытку позже.",
        "sk": "Metadáta Homebrew nie sú dostupné. Skúste to znova neskôr.",
        "sl": "Metapodatki Homebrew niso na voljo. Poskusite znova pozneje.",
        "sq": "Metadatat e Homebrew nuk janë të disponueshme. Provoni përsëri më vonë.",
        "sr": "Homebrew метаподаци нису доступни. Покушајте поново касније.",
        "sv": "Homebrew-metadata är inte tillgängliga. Försök igen senare.",
        "sw": "Metadata ya Homebrew haipatikani. Jaribu tena baadaye.",
        "ta": "Homebrew மெட்டாடேட்டா கிடைக்கவில்லை. பின்னர் மீண்டும் முயற்சிக்கவும்.",
        "tg": "Метамаълумоти Homebrew дастрас нест. Баъдтар дубора кӯшиш кунед.",
        "th": "ข้อมูลเมตาของ Homebrew ไม่พร้อมใช้งาน โปรดลองอีกครั้งในภายหลัง",
        "tl": "Hindi available ang Homebrew metadata. Subukan ulit mamaya.",
        "tr": "Homebrew meta verileri kullanılamıyor. Daha sonra tekrar deneyin.",
        "uk": "Метадані Homebrew недоступні. Спробуйте ще раз пізніше.",
        "ur": "Homebrew میٹا ڈیٹا دستیاب نہیں ہے۔ بعد میں دوبارہ کوشش کریں۔",
        "uz": "Homebrew metadata ma'lumotlari mavjud emas. Keyinroq qayta urinib ko'ring.",
        "vi": "Siêu dữ liệu Homebrew không khả dụng. Hãy thử lại sau.",
        "zh": "Homebrew 元数据不可用。请稍后重试。"
    },
    "homebrew_category_desc": {
        "am": "ከHomebrew ጥቅሎችን ያስሱ።",
        "ar": "تصفح الحزم من Homebrew.",
        "az": "Homebrew paketlərinə nəzər salın.",
        "bg": "Разглеждайте пакети от Homebrew.",
        "bn": "Homebrew থেকে প্যাকেজ ব্রাউজ করুন।",
        "bs": "Pregledajte pakete iz Homebrew-a.",
        "cs": "Procházejte balíčky z Homebrew.",
        "da": "Gennemse pakker fra Homebrew.",
        "de": "Pakete aus Homebrew durchsuchen.",
        "el": "Περιηγηθείτε σε πακέτα από το Homebrew.",
        "es": "Explora paquetes de Homebrew.",
        "et": "Sirvige Homebrew pakette.",
        "fa": "بسته‌های Homebrew را مرور کنید.",
        "fi": "Selaa Homebrew-paketteja.",
        "fr": "Parcourez les paquets de Homebrew.",
        "ga": "Brabhsáil pacáistí ó Homebrew.",
        "he": "עיינו בחבילות מ-Homebrew.",
        "hi": "Homebrew से पैकेज ब्राउज़ करें।",
        "hr": "Pregledajte pakete iz Homebrew-a.",
        "hu": "Böngésszen a Homebrew csomagjai között.",
        "hy": "Դիտեք Homebrew-ի փաթեթները։",
        "id": "Jelajahi paket dari Homebrew.",
        "is": "Skoðaðu pakka frá Homebrew.",
        "it": "Sfoglia i pacchetti di Homebrew.",
        "ja": "Homebrew のパッケージを閲覧します。",
        "ka": "დაათვალიერეთ პაკეტები Homebrew-დან.",
        "km": "រកមើលកញ្ចប់ពី Homebrew។",
        "ko": "Homebrew의 패키지를 찾아봅니다.",
        "lo": "ເບິ່ງແພັກເກດຈາກ Homebrew.",
        "lt": "Naršykite Homebrew paketus.",
        "lv": "Pārlūkojiet Homebrew pakotnes.",
        "mn": "Homebrew дахь багцуудыг үзэх.",
        "ms": "Semak imbas pakej daripada Homebrew.",
        "my": "Homebrew မှ package များကို ရှာဖွေကြည့်ရှုပါ။",
        "nb": "Bla gjennom pakker fra Homebrew.",
        "ne": "Homebrew का प्याकेजहरू ब्राउज गर्नुहोस्।",
        "nl": "Blader door pakketten van Homebrew.",
        "pl": "Przeglądaj pakiety z Homebrew.",
        "pt": "Explore pacotes do Homebrew.",
        "ro": "Răsfoiți pachetele din Homebrew.",
        "ru": "Просматривайте пакеты из Homebrew.",
        "sk": "Prehliadajte balíky z Homebrew.",
        "sl": "Brskajte po paketih iz Homebrew.",
        "sq": "Shfletoni paketat nga Homebrew.",
        "sr": "Прегледајте пакете из Homebrew-а.",
        "sv": "Bläddra bland paket från Homebrew.",
        "sw": "Vinjari vifurushi kutoka Homebrew.",
        "ta": "Homebrew-இலிருந்து தொகுப்புகளை உலாவுங்கள்.",
        "tg": "Бастаҳои Homebrew-ро аз назар гузаронед.",
        "th": "เรียกดูแพ็กเกจจาก Homebrew",
        "tl": "Mag-browse ng mga package mula sa Homebrew.",
        "tr": "Homebrew paketlerine göz atın.",
        "uk": "Переглядайте пакети з Homebrew.",
        "ur": "Homebrew سے پیکیجز براؤز کریں۔",
        "uz": "Homebrew paketlarini ko'rib chiqing.",
        "vi": "Duyệt các gói từ Homebrew.",
        "zh": "浏览 Homebrew 中的软件包。"
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

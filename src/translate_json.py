import json
import os

# Directory containing the language files
lang_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "p3/libs/lang/")

# Translations dictionary: key -> {lang_code: translation}
translations = {
        "occt_desc": {
        "am": "የመረጋጋት ሙከራ እና የአፈጻጸም መለኪያ መሣሪያ።",
        "ar": "أداة لاختبار الاستقرار وقياس الأداء.",
        "az": "Sabitlik testi və performans ölçmə aləti.",
        "bg": "Инструмент за тестване на стабилността и производителността.",
        "bn": "স্থিতিশীলতা পরীক্ষা এবং বেঞ্চমার্ক টুল।",
        "bs": "Alat za testiranje stabilnosti i mjerenje performansi.",
        "cs": "Nástroj pro testování stability a měření výkonu.",
        "da": "Værktøj til stabilitetstest og benchmark.",
        "de": "Werkzeug zum Testen der Stabilität und Benchmarken.",
        "el": "Εργαλείο δοκιμής σταθερότητας και αξιολόγησης επιδόσεων.",
        "es": "Herramienta de pruebas de estabilidad y rendimiento.",
        "et": "Stabiilsuse testimise ja jõudluse võrdlemise tööriist.",
        "fa": "ابزار تست پایداری و بنچمارک.",
        "fi": "Vakavuustestaus- ja suorituskyvyn vertailutyökalu.",
        "fr": "Outil de test de stabilité et de benchmark.",
        "ga": "Uirlis tástála cobhsaíochta agus tagarmharcála.",
        "he": "כלי לבדיקת יציבות וביצועים.",
        "hi": "स्थिरता परीक्षण और बेंचमार्क टूल।",
        "hr": "Alat za testiranje stabilnosti i mjerenje performansi.",
        "hu": "Stabilitástesztelő és teljesítménymérő eszköz.",
        "hy": "Կայունության փորձարկման և արտադրողականության չափման գործիք։",
        "id": "Alat pengujian stabilitas dan benchmark.",
        "is": "Verkfæri fyrir stöðugleikaprófanir og afkastamælingar.",
        "it": "Strumento per test di stabilità e benchmark.",
        "ja": "安定性テストおよびベンチマークツール。",
        "ka": "სტაბილურობის ტესტირებისა და წარმადობის საზომი ინსტრუმენტი.",
        "km": "ឧបករណ៍សាកល្បងស្ថេរភាព និងវាស់ស្ទង់ប្រសិទ្ធភាព។",
        "ko": "안정성 테스트 및 벤치마크 도구.",
        "lo": "ເຄື່ອງມືທົດສອບຄວາມສະຖຽນ ແລະ ວັດປະສິດທິພາບ.",
        "lt": "Stabilumo testavimo ir našumo matavimo įrankis.",
        "lv": "Stabilitātes testēšanas un veiktspējas mērīšanas rīks.",
        "mn": "Тогтвортой байдлын тест болон гүйцэтгэлийн хэмжилтийн хэрэгсэл.",
        "ms": "Alat ujian kestabilan dan penanda aras prestasi.",
        "my": "တည်ငြိမ်မှုစမ်းသပ်ခြင်းနှင့် စွမ်းဆောင်ရည်တိုင်းတာခြင်း ကိရိယာ။",
        "nb": "Verktøy for stabilitetstesting og ytelsesmåling.",
        "ne": "स्थिरता परीक्षण र बेन्चमार्क उपकरण।",
        "nl": "Hulpmiddel voor stabiliteitstests en benchmarks.",
        "pl": "Narzędzie do testowania stabilności i wydajności.",
        "pt": "Ferramenta de teste de estabilidade e benchmark.",
        "ro": "Instrument pentru testarea stabilității și măsurarea performanței.",
        "ru": "Инструмент для тестирования стабильности и производительности.",
        "sk": "Nástroj na testovanie stability a meranie výkonu.",
        "sl": "Orodje za testiranje stabilnosti in merjenje zmogljivosti.",
        "sq": "Mjet për testimin e stabilitetit dhe matjen e performancës.",
        "sr": "Алат за тестирање стабилности и мерење перформанси.",
        "sv": "Verktyg för stabilitetstestning och prestandamätning.",
        "sw": "Zana ya kupima uthabiti na utendaji.",
        "ta": "நிலைத்தன்மை சோதனை மற்றும் செயல்திறன் அளவீட்டு கருவி.",
        "tg": "Асбоб барои санҷиши устуворӣ ва ченкунии маҳсулнокӣ.",
        "th": "เครื่องมือทดสอบเสถียรภาพและวัดประสิทธิภาพ.",
        "tl": "Kasangkapan para sa pagsubok ng katatagan at pag-benchmark.",
        "tr": "Kararlılık testi ve performans ölçüm aracı.",
        "uk": "Інструмент для тестування стабільності та вимірювання продуктивності.",
        "ur": "استحکام کی جانچ اور کارکردگی کا بینچ مارک کرنے کا آلہ۔",
        "uz": "Barqarorlikni sinash va unumdorlikni o‘lchash vositasi.",
        "vi": "Công cụ kiểm tra độ ổn định và đo hiệu năng.",
        "zh": "稳定性测试和性能基准测试工具。"
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

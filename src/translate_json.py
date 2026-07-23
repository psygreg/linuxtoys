import json
import os

# Directory containing the language files
lang_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "p3/libs/lang/")

# Translations dictionary: key -> {lang_code: translation}
translations = {
    "atkinson_desc": {
        "am": "ዝቅተኛ እይታ ላላቸው አንባቢዎች የጽሑፍ ግልጽነትን እና ንባብን ለማሻሻል የተነደፈ የፊደል ቅርጽ።",
        "ar": "خط مصمم لتحسين وضوح النص وسهولة قراءته للأشخاص ضعاف البصر.",
        "az": "Görmə qabiliyyəti zəif olan oxucular üçün mətnin aydınlığını və oxunaqlılığını artırmaq məqsədilə hazırlanmış şrift.",
        "bg": "Шрифт, създаден за подобряване на четливостта и удобството при четене за хора със слабо зрение.",
        "bn": "কম দৃষ্টিশক্তিসম্পন্ন পাঠকদের জন্য পাঠযোগ্যতা ও স্পষ্টতা বাড়ানোর উদ্দেশ্যে তৈরি একটি ফন্ট।",
        "bs": "Font dizajniran za poboljšanje čitljivosti i preglednosti osobama sa slabijim vidom.",
        "cs": "Písmo navržené pro lepší čitelnost a srozumitelnost pro čtenáře se zhoršeným zrakem.",
        "da": "En skrifttype designet til at forbedre læsbarhed og tydelighed for personer med nedsat syn.",
        "de": "Eine Schriftart, die entwickelt wurde, um Lesbarkeit und Erkennbarkeit für Menschen mit Sehbehinderung zu verbessern.",
        "el": "Μια γραμματοσειρά σχεδιασμένη για τη βελτίωση της ευκρίνειας και της αναγνωσιμότητας για άτομα με μειωμένη όραση.",
        "es": "Una tipografía diseñada para mejorar la legibilidad y la facilidad de lectura de personas con baja visión.",
        "et": "Kirjatüüp, mis on loodud parandama loetavust ja lugemismugavust vaegnägijatele.",
        "fa": "یک قلم طراحی‌شده برای بهبود خوانایی و وضوح متن برای افراد کم‌بینا.",
        "fi": "Kirjasin, joka on suunniteltu parantamaan luettavuutta ja selkeyttä heikkonäköisille lukijoille.",
        "fr": "Une police conçue pour améliorer la lisibilité des personnes malvoyantes.",
        "ga": "Cló deartha chun inléiteacht agus soiléireacht a fheabhsú do dhaoine lagamhairc.",
        "he": "גופן שתוכנן לשפר את הקריאות והבהירות עבור אנשים עם לקות ראייה.",
        "hi": "कम दृष्टि वाले पाठकों के लिए पठनीयता और स्पष्टता बढ़ाने हेतु डिज़ाइन किया गया फ़ॉन्ट।",
        "hr": "Font dizajniran za poboljšanje čitljivosti osobama sa slabijim vidom.",
        "hu": "Betűtípus, amelyet a gyengénlátók számára a jobb olvashatóság érdekében terveztek.",
        "hy": "Տառատեսակ, որը նախատեսված է թույլ տեսողություն ունեցող ընթերցողների համար ընթեռնելիությունն ու հստակությունը բարելավելու նպատակով։",
        "id": "Font yang dirancang untuk meningkatkan keterbacaan bagi pembaca dengan gangguan penglihatan.",
        "is": "Leturgerð hönnuð til að bæta læsileika fyrir fólk með skerta sjón.",
        "it": "Un carattere progettato per migliorare la leggibilità per le persone con problemi di vista.",
        "ja": "弱視の人の視認性と読みやすさを向上させるために設計された書体です。",
        "ka": "შრიფტი, რომელიც შექმნილია დაბალი მხედველობის მქონე მკითხველებისთვის წაკითხვადობის გასაუმჯობესებლად.",
        "km": "ពុម្ពអក្សរដែលត្រូវបានរចនាឡើងដើម្បីបង្កើនភាពងាយស្រួលក្នុងការអានសម្រាប់អ្នកដែលមានចក្ខុវិស័យខ្សោយ។",
        "ko": "저시력 사용자의 가독성과 판독성을 향상시키도록 설계된 글꼴입니다.",
        "lo": "ແບບອັກສອນທີ່ອອກແບບເພື່ອປັບປຸງຄວາມຊັດເຈນ ແລະ ຄວາມອ່ານງ່າຍສຳລັບຜູ້ທີ່ມີສາຍຕາບົກພ່ອງ.",
        "lt": "Šriftas, sukurtas pagerinti teksto įskaitomumą ir skaitomumą silpnaregiams.",
        "lv": "Fonts, kas izstrādāts, lai uzlabotu salasāmību cilvēkiem ar vāju redzi.",
        "mn": "Хараа муутай хүмүүст зориулан уншихад хялбар байдлыг сайжруулах зорилготой фонт.",
        "ms": "Fon yang direka untuk meningkatkan kebolehbacaan bagi pembaca yang mempunyai masalah penglihatan.",
        "my": "အမြင်အာရုံအားနည်းသူများအတွက် စာဖတ်ရလွယ်ကူစေရန် ဒီဇိုင်းထုတ်ထားသော ဖောင့်။",
        "nb": "En skrifttype utviklet for å forbedre lesbarheten for personer med nedsatt syn.",
        "ne": "कम दृष्टि भएका पाठकहरूका लागि स्पष्टता र पढ्न सजिलो बनाउन डिजाइन गरिएको फन्ट।",
        "nl": "Een lettertype dat is ontworpen om de leesbaarheid voor mensen met een verminderd gezichtsvermogen te verbeteren.",
        "pl": "Krój pisma zaprojektowany w celu poprawy czytelności dla osób słabowidzących.",
        "pt": "Uma fonte projetada para melhorar a legibilidade e a facilidade de leitura para pessoas com baixa visão.",
        "ro": "Un font conceput pentru a îmbunătăți lizibilitatea pentru persoanele cu vedere redusă.",
        "ru": "Шрифт, разработанный для улучшения читаемости и разборчивости текста для людей с ослабленным зрением.",
        "sk": "Písmo navrhnuté na zlepšenie čitateľnosti pre ľudí so zhoršeným zrakom.",
        "sl": "Pisava, zasnovana za izboljšanje berljivosti za ljudi s slabšim vidom.",
        "sq": "Një font i projektuar për të përmirësuar lexueshmërinë për personat me shikim të dobët.",
        "sr": "Фонт дизајниран да побољша читљивост за особе са слабим видом.",
        "sv": "Ett typsnitt utformat för att förbättra läsbarheten för personer med nedsatt syn.",
        "sw": "Fonti iliyoundwa kuboresha usomaji kwa watu wenye uoni hafifu.",
        "ta": "குறைந்த பார்வை கொண்டவர்களுக்கு வாசிப்புத் தெளிவையும் வாசிக்க எளிமையையும் மேம்படுத்த வடிவமைக்கப்பட்ட எழுத்துரு.",
        "tg": "Ҳуруфе, ки барои беҳтар кардани хонданпазирӣ барои шахсони дорои биноии суст тарҳрезӣ шудааст.",
        "th": "แบบอักษรที่ออกแบบมาเพื่อเพิ่มความชัดเจนและความสามารถในการอ่านข้อความสำหรับผู้ที่มีสายตาเลือนราง",
        "tl": "Isang typeface na idinisenyo upang mapabuti ang pagiging madaling basahin para sa mga taong may mahinang paningin.",
        "tr": "Az gören kişilerin metinleri daha rahat okuyabilmesi için tasarlanmış bir yazı tipi.",
        "uk": "Шрифт, розроблений для покращення читабельності для людей зі слабким зором.",
        "ur": "ایک فونٹ جو کم بینائی والے افراد کے لیے متن کو زیادہ واضح اور قابلِ مطالعہ بنانے کے لیے تیار کیا گیا ہے۔",
        "uz": "Ko‘rish qobiliyati zaif o‘quvchilar uchun matnning o‘qilishini yaxshilash maqsadida ishlab chiqilgan shrift.",
        "vi": "Phông chữ được thiết kế để cải thiện khả năng đọc cho người có thị lực kém.",
        "zh": "一种旨在提高低视力读者文字辨识度和可读性的字体。"
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

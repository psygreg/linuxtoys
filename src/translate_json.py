import json
import os

# Directory containing the language files
lang_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "p3/libs/lang/")

# Translations dictionary: key -> {lang_code: translation}
translations = {
"app_page_snap_revert_confirm_message": {
    "am": "LinuxToys '{app_name}'ን ቀደም ሲል ወደተጫነው የSnap ክለሳ ይመልሳል።\n\nመቀጠል ይፈልጋሉ?",
    "ar": "سيعيد LinuxToys تطبيق '{app_name}' إلى مراجعة Snap المثبتة سابقًا.\n\nهل تريد المتابعة؟",
    "az": "LinuxToys '{app_name}' tətbiqini əvvəllər quraşdırılmış Snap reviziyasına qaytaracaq.\n\nDavam etmək istəyirsiniz?",
    "bg": "LinuxToys ще върне „{app_name}“ към предишната инсталирана ревизия на Snap.\n\nИскате ли да продължите?",
    "bn": "LinuxToys '{app_name}'-কে পূর্বে ইনস্টল করা Snap রিভিশনে ফিরিয়ে দেবে।\n\nআপনি কি চালিয়ে যেতে চান?",
    "bs": "LinuxToys će vratiti '{app_name}' na prethodno instaliranu Snap reviziju.\n\nŽelite li nastaviti?",
    "cs": "LinuxToys vrátí aplikaci „{app_name}“ na dříve nainstalovanou revizi Snap.\n\nChcete pokračovat?",
    "da": "LinuxToys vil tilbageføre '{app_name}' til den tidligere installerede Snap-revision.\n\nVil du fortsætte?",
    "de": "LinuxToys setzt „{app_name}“ auf die zuvor installierte Snap-Revision zurück.\n\nMöchten Sie fortfahren?",
    "el": "Το LinuxToys θα επαναφέρει το '{app_name}' στην προηγουμένως εγκατεστημένη αναθεώρηση Snap.\n\nΘέλετε να συνεχίσετε;",
    "es": "LinuxToys revertirá '{app_name}' a la revisión de Snap instalada anteriormente.\n\n¿Quieres continuar?",
    "et": "LinuxToys taastab rakenduse „{app_name}“ varem paigaldatud Snapi versioonile.\n\nKas soovite jätkata?",
    "fa": "LinuxToys برنامه '{app_name}' را به ویرایش Snap که قبلاً نصب شده بود بازمی‌گرداند.\n\nآیا می‌خواهید ادامه دهید؟",
    "fi": "LinuxToys palauttaa sovelluksen '{app_name}' aiemmin asennettuun Snap-revisioon.\n\nHaluatko jatkaa?",
    "fr": "LinuxToys rétablira « {app_name} » à la révision Snap précédemment installée.\n\nVoulez-vous continuer ?",
    "ga": "Fillfidh LinuxToys '{app_name}' ar ais chuig an leasú Snap a bhí suiteáilte roimhe seo.\n\nAr mhaith leat leanúint ar aghaidh?",
    "he": "LinuxToys יחזיר את '{app_name}' לגרסת ה-Snap שהייתה מותקנת קודם לכן.\n\nהאם להמשיך?",
    "hi": "LinuxToys '{app_name}' को पहले इंस्टॉल किए गए Snap रिविज़न पर वापस ले जाएगा।\n\nक्या आप जारी रखना चाहते हैं?",
    "hr": "LinuxToys će vratiti '{app_name}' na prethodno instaliranu Snap reviziju.\n\nŽelite li nastaviti?",
    "hu": "A LinuxToys visszaállítja a(z) „{app_name}” alkalmazást a korábban telepített Snap-revízióra.\n\nSzeretné folytatni?",
    "hy": "LinuxToys-ը '{app_name}'-ը կվերադարձնի նախկինում տեղադրված Snap վերանայմանը։\n\nՑանկանո՞ւմ եք շարունակել։",
    "id": "LinuxToys akan mengembalikan '{app_name}' ke revisi Snap yang sebelumnya terinstal.\n\nApakah Anda ingin melanjutkan?",
    "is": "LinuxToys færir '{app_name}' aftur í áður uppsetta Snap-útgáfu.\n\nViltu halda áfram?",
    "it": "LinuxToys ripristinerà '{app_name}' alla revisione Snap installata in precedenza.\n\nVuoi continuare?",
    "ja": "LinuxToys は「{app_name}」を以前インストールされていた Snap リビジョンに戻します。\n\n続行しますか？",
    "ka": "LinuxToys დააბრუნებს '{app_name}'-ს ადრე დაყენებულ Snap რევიზიაზე.\n\nგსურთ გაგრძელება?",
    "km": "LinuxToys នឹងត្រឡប់ '{app_name}' ទៅកំណែ Snap ដែលបានដំឡើងពីមុន។\n\nតើអ្នកចង់បន្តទេ?",
    "ko": "LinuxToys가 '{app_name}'을(를) 이전에 설치된 Snap 리비전으로 되돌립니다.\n\n계속하시겠습니까?",
    "lo": "LinuxToys ຈະຍ້ອນ '{app_name}' ກັບໄປຫາ Snap revision ທີ່ເຄີຍຕິດຕັ້ງກ່ອນໜ້ານີ້.\n\nທ່ານຕ້ອງການສືບຕໍ່ບໍ?",
    "lt": "LinuxToys grąžins „{app_name}“ į anksčiau įdiegtą Snap reviziją.\n\nAr norite tęsti?",
    "lv": "LinuxToys atgriezīs „{app_name}“ uz iepriekš instalēto Snap revīziju.\n\nVai vēlaties turpināt?",
    "mn": "LinuxToys '{app_name}'-ийг өмнө нь суулгасан Snap хувилбар руу буцаана.\n\nҮргэлжлүүлэх үү?",
    "ms": "LinuxToys akan mengembalikan '{app_name}' kepada revisi Snap yang dipasang sebelum ini.\n\nAdakah anda mahu meneruskan?",
    "my": "LinuxToys သည် '{app_name}' ကို ယခင်က ထည့်သွင်းထားသော Snap revision သို့ ပြန်ပြောင်းမည်။\n\nဆက်လုပ်လိုပါသလား?",
    "nb": "LinuxToys vil tilbakestille '{app_name}' til den tidligere installerte Snap-revisjonen.\n\nVil du fortsette?",
    "ne": "LinuxToys ले '{app_name}' लाई पहिले स्थापना गरिएको Snap संशोधनमा फर्काउनेछ।\n\nके तपाईं जारी राख्न चाहनुहुन्छ?",
    "nl": "LinuxToys zet '{app_name}' terug naar de eerder geïnstalleerde Snap-revisie.\n\nWilt u doorgaan?",
    "pl": "LinuxToys przywróci „{app_name}” do poprzednio zainstalowanej rewizji Snap.\n\nCzy chcesz kontynuować?",
    "pt": "O LinuxToys reverterá '{app_name}' para a revisão do Snap instalada anteriormente.\n\nDeseja continuar?",
    "ro": "LinuxToys va reveni pentru „{app_name}” la revizia Snap instalată anterior.\n\nDoriți să continuați?",
    "ru": "LinuxToys откатит «{app_name}» до ранее установленной ревизии Snap.\n\nПродолжить?",
    "sk": "LinuxToys vráti aplikáciu „{app_name}“ na predtým nainštalovanú revíziu Snap.\n\nChcete pokračovať?",
    "sl": "LinuxToys bo »{app_name}« povrnil na predhodno nameščeno revizijo Snap.\n\nAli želite nadaljevati?",
    "sq": "LinuxToys do ta rikthejë '{app_name}' te rishikimi Snap i instaluar më parë.\n\nDëshironi të vazhdoni?",
    "sr": "LinuxToys ће вратити „{app_name}“ на претходно инсталирану Snap ревизију.\n\nЖелите ли да наставите?",
    "sv": "LinuxToys återställer '{app_name}' till den tidigare installerade Snap-revisionen.\n\nVill du fortsätta?",
    "sw": "LinuxToys itarejesha '{app_name}' kwenye toleo la Snap lililosakinishwa awali.\n\nUnataka kuendelea?",
    "ta": "LinuxToys '{app_name}'-ஐ முன்பு நிறுவப்பட்ட Snap revision-க்கு மாற்றும்.\n\nதொடர விரும்புகிறீர்களா?",
    "tg": "LinuxToys '{app_name}'-ро ба ревизияи Snap, ки қаблан насб шуда буд, бармегардонад.\n\nМехоҳед идома диҳед?",
    "th": "LinuxToys จะย้อน '{app_name}' กลับไปเป็น revision ของ Snap ที่ติดตั้งไว้ก่อนหน้านี้\n\nคุณต้องการดำเนินการต่อหรือไม่?",
    "tl": "Ibabalik ng LinuxToys ang '{app_name}' sa dating naka-install na Snap revision.\n\nGusto mo bang magpatuloy?",
    "tr": "LinuxToys, '{app_name}' uygulamasını daha önce yüklü olan Snap revizyonuna geri döndürecek.\n\nDevam etmek istiyor musunuz?",
    "uk": "LinuxToys відкотить «{app_name}» до раніше встановленої ревізії Snap.\n\nПродовжити?",
    "ur": "LinuxToys '{app_name}' کو پہلے انسٹال شدہ Snap ریویژن پر واپس لے جائے گا۔\n\nکیا آپ جاری رکھنا چاہتے ہیں؟",
    "uz": "LinuxToys '{app_name}' ilovasini avval o'rnatilgan Snap reviziyasiga qaytaradi.\n\nDavom etishni xohlaysizmi?",
    "vi": "LinuxToys sẽ hoàn nguyên '{app_name}' về bản sửa đổi Snap đã được cài đặt trước đó.\n\nBạn có muốn tiếp tục không?",
    "zh": "LinuxToys 会将“{app_name}”还原到之前安装的 Snap 修订版本。\n\n是否继续？"
},
"app_page_snap_revert": {
    "am": " ወደ ቀድሞው መልስ ",
    "ar": " رجوع ",
    "az": " Geri qaytar ",
    "bg": " Връщане ",
    "bn": " ফিরিয়ে নিন ",
    "bs": " Vrati ",
    "cs": " Vrátit ",
    "da": " Tilbagefør ",
    "de": " Zurücksetzen ",
    "el": " Επαναφορά ",
    "es": " Revertir ",
    "et": " Taasta ",
    "fa": " بازگردانی ",
    "fi": " Palauta ",
    "fr": " Rétablir ",
    "ga": " Fill ar ais ",
    "he": " החזרה ",
    "hi": " वापस लौटाएँ ",
    "hr": " Vrati ",
    "hu": " Visszaállítás ",
    "hy": " Վերադարձնել ",
    "id": " Kembalikan ",
    "is": " Færa aftur ",
    "it": " Ripristina ",
    "ja": " 元に戻す ",
    "ka": " დაბრუნება ",
    "km": " ត្រឡប់ ",
    "ko": " 되돌리기 ",
    "lo": " ຍ້ອນກັບ ",
    "lt": " Grąžinti ",
    "lv": " Atgriezt ",
    "mn": " Буцаах ",
    "ms": " Kembalikan ",
    "my": " ပြန်ပြောင်းရန် ",
    "nb": " Tilbakestill ",
    "ne": " फर्काउनुहोस् ",
    "nl": " Terugzetten ",
    "pl": " Przywróć ",
    "pt": " Reverter ",
    "ro": " Revino ",
    "ru": " Откатить ",
    "sk": " Vrátiť ",
    "sl": " Povrni ",
    "sq": " Rikthe ",
    "sr": " Врати ",
    "sv": " Återställ ",
    "sw": " Rejesha ",
    "ta": " மாற்றியமை ",
    "tg": " Баргардондан ",
    "th": " ย้อนกลับ ",
    "tl": " I-revert ",
    "tr": " Geri al ",
    "uk": " Відкотити ",
    "ur": " واپس کریں ",
    "uz": " Qaytarish ",
    "vi": " Hoàn nguyên ",
    "zh": " 还原 "
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

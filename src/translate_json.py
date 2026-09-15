import json
import os

# Directory containing the language files
lang_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "p3/libs/lang/")

# Translations dictionary: key -> {lang_code: translation}
translations = {
    "bug_report_outdated_title": {
        "am": "የሳንካ ሪፖርት አይገኝም",
        "ar": "الإبلاغ عن الأخطاء غير متاح",
        "az": "Xəta hesabatı əlçatan deyil",
        "bg": "Докладването на грешка не е достъпно",
        "bn": "বাগ রিপোর্ট উপলব্ধ নয়",
        "bs": "Prijava greške nije dostupna",
        "cs": "Hlášení chyby není dostupné",
        "da": "Fejlrapportering er ikke tilgængelig",
        "de": "Fehlerbericht nicht verfügbar",
        "el": "Η αναφορά σφάλματος δεν είναι διαθέσιμη",
        "es": "Informe de errores no disponible",
        "et": "Veateade pole saadaval",
        "fa": "گزارش اشکال در دسترس نیست",
        "fi": "Virheraportointi ei ole käytettävissä",
        "fr": "Rapport de bug indisponible",
        "ga": "Níl tuairisciú fabhtanna ar fáil",
        "he": "דיווח על באג אינו זמין",
        "hi": "बग रिपोर्ट उपलब्ध नहीं है",
        "hr": "Prijava greške nije dostupna",
        "hu": "A hibajelentés nem érhető el",
        "hy": "Սխալի զեկույցն անհասանելի է",
        "id": "Laporan bug tidak tersedia",
        "is": "Villutilkynning er ekki í boði",
        "it": "Segnalazione bug non disponibile",
        "ja": "バグ報告は利用できません",
        "ka": "შეცდომის ანგარიში მიუწვდომელია",
        "km": "ការរាយការណ៍កំហុសមិនអាចប្រើបាន",
        "ko": "버그 보고를 사용할 수 없음",
        "lo": "ບໍ່ສາມາດລາຍງານບັກໄດ້",
        "lt": "Pranešimas apie klaidą nepasiekiamas",
        "lv": "Kļūdas ziņojums nav pieejams",
        "mn": "Алдааны тайлан илгээх боломжгүй",
        "ms": "Laporan pepijat tidak tersedia",
        "my": "Bug report ကို အသုံးမပြုနိုင်ပါ",
        "nb": "Feilrapportering er ikke tilgjengelig",
        "ne": "बग रिपोर्ट उपलब्ध छैन",
        "nl": "Bugrapportage niet beschikbaar",
        "pl": "Zgłaszanie błędów jest niedostępne",
        "pt": "Relatório de erro indisponível",
        "ro": "Raportarea erorilor nu este disponibilă",
        "ru": "Отчёт об ошибке недоступен",
        "sk": "Hlásenie chyby nie je dostupné",
        "sl": "Poročanje o napaki ni na voljo",
        "sq": "Raportimi i gabimeve nuk është i disponueshëm",
        "sr": "Пријава грешке није доступна",
        "sv": "Felrapportering är inte tillgänglig",
        "sw": "Ripoti ya hitilafu haipatikani",
        "ta": "பிழை அறிக்கை கிடைக்கவில்லை",
        "tg": "Гузориши хато дастрас нест",
        "th": "ไม่สามารถรายงานข้อบกพร่องได้",
        "tl": "Hindi available ang pag-report ng bug",
        "tr": "Hata bildirimi kullanılamıyor",
        "uk": "Звіт про помилку недоступний",
        "ur": "بگ رپورٹ دستیاب نہیں ہے",
        "uz": "Xatolik hisoboti mavjud emas",
        "vi": "Không thể báo cáo lỗi",
        "zh": "无法提交错误报告"
    },

    "bug_report_outdated_message": {
        "am": "LinuxToys ${current} እየተጠቀሙ ነው፣ ነገር ግን የአሁኑ ስሪት ${latest} ነው። የሳንካ ሪፖርት ከማስገባትዎ በፊት LinuxToysን እባክዎ ያዘምኑ።",
        "ar": "أنت تستخدم LinuxToys ${current}، لكن الإصدار الحالي هو ${latest}. يرجى تحديث LinuxToys قبل إرسال تقرير عن خطأ.",
        "az": "Siz LinuxToys ${current} istifadə edirsiniz, lakin cari versiya ${latest}-dir. Xəta hesabatı göndərməzdən əvvəl LinuxToys-u yeniləyin.",
        "bg": "Използвате LinuxToys ${current}, но текущата версия е ${latest}. Моля, обновете LinuxToys, преди да изпратите доклад за грешка.",
        "bn": "আপনি LinuxToys ${current} ব্যবহার করছেন, কিন্তু বর্তমান সংস্করণ হলো ${latest}। বাগ রিপোর্ট জমা দেওয়ার আগে অনুগ্রহ করে LinuxToys আপডেট করুন।",
        "bs": "Koristite LinuxToys ${current}, ali trenutna verzija je ${latest}. Ažurirajte LinuxToys prije slanja prijave greške.",
        "cs": "Používáte LinuxToys ${current}, ale aktuální verze je ${latest}. Před odesláním hlášení chyby prosím LinuxToys aktualizujte.",
        "da": "Du kører LinuxToys ${current}, men den aktuelle version er ${latest}. Opdater venligst LinuxToys, før du indsender en fejlrapport.",
        "de": "Sie verwenden LinuxToys ${current}, die aktuelle Version ist jedoch ${latest}. Bitte aktualisieren Sie LinuxToys, bevor Sie einen Fehlerbericht einreichen.",
        "el": "Χρησιμοποιείτε το LinuxToys ${current}, αλλά η τρέχουσα έκδοση είναι η ${latest}. Ενημερώστε το LinuxToys πριν υποβάλετε αναφορά σφάλματος.",
        "es": "Estás ejecutando LinuxToys ${current}, pero la versión actual es ${latest}. Actualiza LinuxToys antes de enviar un informe de errores.",
        "et": "Kasutate LinuxToysi versiooni ${current}, kuid praegune versioon on ${latest}. Enne veateate esitamist uuendage LinuxToys.",
        "fa": "شما در حال اجرای LinuxToys ${current} هستید، اما نسخه فعلی ${latest} است. لطفاً پیش از ارسال گزارش اشکال، LinuxToys را به‌روزرسانی کنید.",
        "fi": "Käytössäsi on LinuxToys ${current}, mutta nykyinen versio on ${latest}. Päivitä LinuxToys ennen virheraportin lähettämistä.",
        "fr": "Vous utilisez LinuxToys ${current}, mais la version actuelle est ${latest}. Veuillez mettre à jour LinuxToys avant d'envoyer un rapport de bug.",
        "ga": "Tá LinuxToys ${current} á rith agat, ach is é ${latest} an leagan reatha. Nuashonraigh LinuxToys sula gcuireann tú tuairisc fabhtanna isteach.",
        "he": "אתה משתמש ב-LinuxToys ${current}, אך הגרסה הנוכחית היא ${latest}. יש לעדכן את LinuxToys לפני שליחת דיווח על באג.",
        "hi": "आप LinuxToys ${current} चला रहे हैं, लेकिन वर्तमान संस्करण ${latest} है। बग रिपोर्ट सबमिट करने से पहले कृपया LinuxToys को अपडेट करें।",
        "hr": "Koristite LinuxToys ${current}, ali trenutačna verzija je ${latest}. Ažurirajte LinuxToys prije slanja prijave greške.",
        "hu": "A LinuxToys ${current} verzióját használja, de a jelenlegi verzió ${latest}. Hibajelentés beküldése előtt frissítse a LinuxToyst.",
        "hy": "Դուք օգտագործում եք LinuxToys ${current}, սակայն ընթացիկ տարբերակը ${latest} է։ Խնդրում ենք թարմացնել LinuxToys-ը՝ նախքան սխալի զեկույց ուղարկելը։",
        "id": "Anda menjalankan LinuxToys ${current}, tetapi versi saat ini adalah ${latest}. Harap perbarui LinuxToys sebelum mengirim laporan bug.",
        "is": "Þú ert að keyra LinuxToys ${current}, en núverandi útgáfa er ${latest}. Uppfærðu LinuxToys áður en þú sendir inn villutilkynningu.",
        "it": "Stai utilizzando LinuxToys ${current}, ma la versione attuale è ${latest}. Aggiorna LinuxToys prima di inviare una segnalazione di bug.",
        "ja": "LinuxToys ${current} を実行していますが、現在のバージョンは ${latest} です。バグ報告を送信する前に LinuxToys を更新してください。",
        "ka": "თქვენ იყენებთ LinuxToys ${current}-ს, მაგრამ მიმდინარე ვერსიაა ${latest}. შეცდომის ანგარიშის გაგზავნამდე გთხოვთ განაახლოთ LinuxToys.",
        "km": "អ្នកកំពុងប្រើ LinuxToys ${current} ប៉ុន្តែកំណែបច្ចុប្បន្នគឺ ${latest}។ សូមធ្វើបច្ចុប្បន្នភាព LinuxToys មុនពេលដាក់ស្នើរបាយការណ៍កំហុស។",
        "ko": "LinuxToys ${current}을(를) 실행 중이지만 현재 버전은 ${latest}입니다. 버그 보고서를 제출하기 전에 LinuxToys를 업데이트해 주세요.",
        "lo": "ທ່ານກຳລັງໃຊ້ LinuxToys ${current}, ແຕ່ເວີຊັນປັດຈຸບັນແມ່ນ ${latest}. ກະລຸນາອັບເດດ LinuxToys ກ່ອນສົ່ງລາຍງານບັກ.",
        "lt": "Naudojate LinuxToys ${current}, tačiau dabartinė versija yra ${latest}. Prieš pateikdami pranešimą apie klaidą, atnaujinkite LinuxToys.",
        "lv": "Jūs izmantojat LinuxToys ${current}, bet pašreizējā versija ir ${latest}. Pirms kļūdas ziņojuma iesniegšanas, lūdzu, atjauniniet LinuxToys.",
        "mn": "Та LinuxToys ${current} хувилбарыг ашиглаж байна, харин одоогийн хувилбар нь ${latest}. Алдааны тайлан илгээхээсээ өмнө LinuxToys-ийг шинэчилнэ үү.",
        "ms": "Anda sedang menjalankan LinuxToys ${current}, tetapi versi semasa ialah ${latest}. Sila kemas kini LinuxToys sebelum menghantar laporan pepijat.",
        "my": "သင်သည် LinuxToys ${current} ကို အသုံးပြုနေသော်လည်း လက်ရှိဗားရှင်းမှာ ${latest} ဖြစ်သည်။ Bug report မတင်မီ LinuxToys ကို update လုပ်ပါ။",
        "nb": "Du kjører LinuxToys ${current}, men gjeldende versjon er ${latest}. Oppdater LinuxToys før du sender inn en feilrapport.",
        "ne": "तपाईं LinuxToys ${current} चलाउँदै हुनुहुन्छ, तर हालको संस्करण ${latest} हो। बग रिपोर्ट पेश गर्नुअघि कृपया LinuxToys अद्यावधिक गर्नुहोस्।",
        "nl": "Je gebruikt LinuxToys ${current}, maar de huidige versie is ${latest}. Werk LinuxToys bij voordat je een bugrapport indient.",
        "pl": "Używasz LinuxToys ${current}, ale aktualna wersja to ${latest}. Zaktualizuj LinuxToys przed wysłaniem zgłoszenia błędu.",
        "pt": "Você está usando o LinuxToys ${current}, mas a versão atual é ${latest}. Atualize o LinuxToys antes de enviar um relatório de erro.",
        "ro": "Folosiți LinuxToys ${current}, dar versiunea actuală este ${latest}. Actualizați LinuxToys înainte de a trimite un raport de eroare.",
        "ru": "Вы используете LinuxToys ${current}, но текущая версия — ${latest}. Обновите LinuxToys перед отправкой отчёта об ошибке.",
        "sk": "Používate LinuxToys ${current}, ale aktuálna verzia je ${latest}. Pred odoslaním hlásenia chyby aktualizujte LinuxToys.",
        "sl": "Uporabljate LinuxToys ${current}, vendar je trenutna različica ${latest}. Pred oddajo poročila o napaki posodobite LinuxToys.",
        "sq": "Po përdorni LinuxToys ${current}, por versioni aktual është ${latest}. Përditësoni LinuxToys përpara se të dërgoni një raport gabimi.",
        "sr": "Користите LinuxToys ${current}, али тренутна верзија је ${latest}. Ажурирајте LinuxToys пре слања пријаве грешке.",
        "sv": "Du kör LinuxToys ${current}, men den aktuella versionen är ${latest}. Uppdatera LinuxToys innan du skickar in en felrapport.",
        "sw": "Unatumia LinuxToys ${current}, lakini toleo la sasa ni ${latest}. Tafadhali sasisha LinuxToys kabla ya kuwasilisha ripoti ya hitilafu.",
        "ta": "நீங்கள் LinuxToys ${current} பதிப்பைப் பயன்படுத்துகிறீர்கள், ஆனால் தற்போதைய பதிப்பு ${latest}. பிழை அறிக்கையைச் சமர்ப்பிக்கும் முன் LinuxToys-ஐப் புதுப்பிக்கவும்.",
        "tg": "Шумо LinuxToys ${current}-ро истифода мебаред, аммо версияи ҷорӣ ${latest} аст. Пеш аз фиристодани гузориши хато LinuxToys-ро навсозӣ кунед.",
        "th": "คุณกำลังใช้ LinuxToys ${current} แต่เวอร์ชันปัจจุบันคือ ${latest} โปรดอัปเดต LinuxToys ก่อนส่งรายงานข้อบกพร่อง",
        "tl": "Gumagamit ka ng LinuxToys ${current}, ngunit ang kasalukuyang bersyon ay ${latest}. Paki-update ang LinuxToys bago magsumite ng bug report.",
        "tr": "LinuxToys ${current} sürümünü kullanıyorsunuz, ancak güncel sürüm ${latest}. Hata bildirimi göndermeden önce lütfen LinuxToys'u güncelleyin.",
        "uk": "Ви використовуєте LinuxToys ${current}, але поточна версія — ${latest}. Оновіть LinuxToys перед надсиланням звіту про помилку.",
        "ur": "آپ LinuxToys ${current} استعمال کر رہے ہیں، لیکن موجودہ ورژن ${latest} ہے۔ بگ رپورٹ جمع کرانے سے پہلے براہ کرم LinuxToys کو اپ ڈیٹ کریں۔",
        "uz": "Siz LinuxToys ${current} versiyasidan foydalanmoqdasiz, ammo joriy versiya ${latest}. Xatolik hisobotini yuborishdan oldin LinuxToys-ni yangilang.",
        "vi": "Bạn đang chạy LinuxToys ${current}, nhưng phiên bản hiện tại là ${latest}. Vui lòng cập nhật LinuxToys trước khi gửi báo cáo lỗi.",
        "zh": "您正在运行 LinuxToys ${current}，但当前版本为 ${latest}。请先更新 LinuxToys，再提交错误报告。"
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

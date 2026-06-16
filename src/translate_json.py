import json
import os

# Directory containing the language files
lang_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "p3/libs/lang/")

# Translations dictionary: key -> {lang_code: translation}
translations = {
    "featured_scripts": {
        "am": "ለመሞከር ሊፈልጉ ይችላሉ...",
        "ar": "قد تود أن تجرب...",
        "az": "Sınayıb görmək istəyə bilərsiniz...",
        "bg": "Можеш да опиташ...",
        "bn": "আপনি চেষ্টা করতে চাইতে পারেন...",
        "bs": "Možda ćeš htjeti pokušati...",
        "cs": "Možná byste chtěli vyzkoušet...",
        "da": "Du vil måske gerne prøve...",
        "de": "Möglicherweise möchten Sie versuchen...",
        "el": "Μπορεί να θέλετε να δοκιμάσετε...",
        "es": "Quizás quieras probar...",
        "et": "Võibolla tahaksid proovida...",
        "fa": "شاید می‌خواهید سعی کنید...",
        "fi": "Saatat haluta kokeilla...",
        "fr": "Vous voudrez peut-être essayer...",
        "ga": "D'fhéadfá a bheith i gceist agat a dhéanamh...",
        "he": "אולי תרצה לנסות...",
        "hi": "आप कोशिश करना चाह सकते हैं...",
        "hr": "Možda bi trebao pokušati...",
        "hu": "Talán szeretnél megpróbálni...",
        "hy": "Հավանաբար կցանկանաք փորձել...",
        "id": "Anda mungkin ingin mencoba...",
        "is": "Þú gætir viljað prófa...",
        "it": "Potresti voler provare...",
        "ja": "試してみたいかもしれません...",
        "ka": "შესაძლოა გსურთ სცადოთ...",
        "km": "អ្នកប្រហែលជាចង់ព្យាយាម...",
        "ko": "시도해볼 수 있습니다...",
        "lo": "ເຈົ້າອາດຈະຕ້ອງການທົດລອງ...",
        "lt": "Jūs galbūt norėtumėte bandyti...",
        "lv": "Iespējams, vēlēsies mēģināt...",
        "mn": "Та оролдож үзэхийг хүсч болно...",
        "ms": "Anda mungkin ingin mencuba...",
        "my": "သင်စည်းမျုံသည့်တွေးခေါ်အရ...",
        "nb": "Du vil kanskje gjerne prøve...",
        "ne": "तपाइं प्रयास गर्न चाहनुहुन्छ...",
        "nl": "Je zult misschien willen proberen...",
        "pl": "Możesz chcieć spróbować...",
        "pt": "Você pode querer tentar...",
        "ro": "Ai putea dori să încerci...",
        "ru": "Вы можете попробовать...",
        "sk": "Možno by ste chceli skúsiť...",
        "sl": "Mogoče bi rad poskusil...",
        "sq": "Mund të dëshirosh të provosh...",
        "sr": "Можда би требало да покушаш...",
        "sv": "Du kanske vill prova...",
        "sw": "Unaweza kuwa unataka kujaribu...",
        "ta": "நீங்கள் முயற்சி செய்ய விரும்பலாம்...",
        "tg": "Шояд шумо кӯшиш карданро мехоҳед...",
        "th": "คุณอาจต้องการลอง...",
        "tl": "Maaari mong gustong subukan...",
        "tr": "Denemek isteyebilirsin...",
        "uk": "Можливо, ви захочете спробувати...",
        "ur": "آپ کوشش کرنا چاہ سکتے ہیں...",
        "uz": "Siz sinab ko'rishni xohlashingiz mumkin...",
        "vi": "Bạn có thể muốn thử...",
        "zh": "您可能想尝试..."
    },
    "ostree_info_message": {
        "am": "ይህ ስርዓት ለአቶሚክ ማዘመኒያዎች rpm-ostree ይጠቀማል። ስ Flatpaks ያልሆኑ ዋናFiles በስርዓት ዳግም ሲጀምር ብቻ ተዘጋጅተው ይገኛሉ።",
        "ar": "هذا النظام يستخدم rpm-ostree للتحديثات الذرية. أي حزم مثبتة حديثًا ليست flatpaks سيتم نشرها وتتوفر فقط بعد إعادة تشغيل النظام.",
        "az": "Bu sistem atom yeniləmələr üçün rpm-ostree istifadə edir. Flatpaks olmayan heç bir yeni quraşdırılmış paket yalnız sistem yenidən başlatıldıqdan sonra yerləşdirilib mövcud olacaq.",
        "bg": "Тази система използва rpm-ostree за атомни актуализации. Всички новоинсталирани пакети, които не са flatpaks, ще бъдат разположени и налични само след рестартиране на системата.",
        "bn": "এই সিস্টেম পারমাণবিক আপডেটের জন্য rpm-ostree ব্যবহার করে। নতুনভাবে ইনস্টল করা কোনও প্যাকেজ যা flatpaks নয় সিস্টেম পুনরায় চালু করার পরে শুধুমাত্র স্থাপন এবং উপলব্ধ হবে।",
        "bs": "Ovaj sistem koristi rpm-ostree za atomske ažuriranja. Svi novougrađeni paketi koji nisu flatpaks će biti implementirani i dostupni samo nakon ponovnog pokretanja sistema.",
        "cs": "Tento systém používá rpm-ostree pro atomické aktualizace. Všechny nově nainstalované balíčky, které nejsou flatpaky, budou nasazeny a dostupné až po restartování systému.",
        "da": "Dette system bruger rpm-ostree til atomare opdateringer. Alle nyligt installerede pakker, der ikke er flatpaks, vil kun blive implementeret og tilgængelige efter en systemgenstart.",
        "de": "Dieses System verwendet rpm-ostree für atomare Updates. Alle neu installierten Pakete, die keine Flatpaks sind, werden erst nach einem Systemneustart bereitgestellt und verfügbar sein.",
        "el": "Αυτό το σύστημα χρησιμοποιεί rpm-ostree για ατομικές ενημερώσεις. Όλα τα πρόσφατα εγκατεστημένα πακέτα που δεν είναι flatpaks θα αναπτυχθούν και θα είναι διαθέσιμα μόνο μετά την επανεκκίνηση του συστήματος.",
        "es": "Este sistema utiliza rpm-ostree para actualizaciones atómicas. Todos los paquetes recién instalados que no sean flatpaks se implementarán y estarán disponibles solo después de reiniciar el sistema.",
        "et": "See süsteem kasutab rpm-ostree aatomi värskenduste jaoks. Kõik äsja installitud paketid, mis ei ole flatpaks, juurutatakse ja on saadaval ainult pärast süsteemi taaskäivitamist.",
        "fa": "این سیستم از rpm-ostree برای بروزرسانی‌های اتمی استفاده می‌کند. هر بسته‌ای که اخیراً نصب شده است و flatpak نیست، فقط پس از راه‌اندازی مجدد سیستم مستقر و در دسترس خواهد بود.",
        "fi": "Tämä järjestelmä käyttää rpm-ostree-kansioita atomiintuotteisiin. Kaikki äskettäin asennetut paketit, jotka eivät ole flatpaks, otetaan käyttöön ja ovat saatavilla vain järjestelmän uudelleenkäynnistyksen jälkeen.",
        "fr": "Ce système utilise rpm-ostree pour les mises à jour atomiques. Tous les paquets nouvellement installés qui ne sont pas des flatpaks ne seront déployés et disponibles qu'après un redémarrage du système.",
        "ga": "Úsáideann an córas seo rpm-ostree do dhíolúna adamhacha. Ní bheidh aon pháicéid nua-suiteáilte nach flatpaks ann curtha i bhfeidhm agus ar fáil ach tar éis an chóras a aththosú.",
        "he": "מערכת זו משתמשת ב-rpm-ostree לעדכונים אטומיים. כל החבילות שהותקנו לאחרונה שאינן flatpaks יופעלו וזמינות רק לאחר הפעלה מחדש של המערכת.",
        "hi": "यह सिस्टम परमाणु अपडेट के लिए rpm-ostree का उपयोग करता है। सभी नवस्थापित पैकेज जो flatpaks नहीं हैं, सिस्टम रीबूट के बाद ही तैनात और उपलब्ध होंगे।",
        "hr": "Ovaj sustav koristi rpm-ostree za atomske ažuriranja. Svi novougrađeni paketi koji nisu flatpaks bit će implementirani i dostupni samo nakon ponovnog pokretanja sustava.",
        "hu": "Ez a rendszer rpm-ostree-t használ atomfrissítésekhez. Az újonnan telepített, nem flatpak csomagok csak a rendszer újraindítása után kerülnek telepítésre és lesznek elérhetőek.",
        "hy": "Այս համակարգը օգտագործում է rpm-ostree ատոմային թարմացումների համար: Բոլոր նոր տեղադրված փաթեթները, որոնք flatpaks չեն, կտեղակայվեն և կլինեն հասանելի միայն համակարգի վերագործարկումից հետո:",
        "id": "Sistem ini menggunakan rpm-ostree untuk pembaruan atom. Semua paket yang baru diinstal yang bukan flatpaks hanya akan dikerahkan dan tersedia setelah sistem dihidupkan kembali.",
        "is": "Þetta kerfi notar rpm-ostree fyrir atóma uppfærslur. Öll nýlega sett inn pakki sem eru ekki flatpaks verða aðeins sett upp og tiltæk eftir endurkomu kerfisins.",
        "it": "Questo sistema utilizza rpm-ostree per gli aggiornamenti atomici. Tutti i pacchetti appena installati che non sono flatpaks saranno distribuiti e disponibili solo dopo un riavvio del sistema.",
        "ja": "このシステムはアトミック更新にrpm-ostreeを使用します。 flatpaksではない新しくインストールされたパッケージは、システムの再起動後にのみデプロイされ、利用可能になります。",
        "ka": "ეს სისტემა იყენებს rpm-ostree-ს ატომური ანახლებებისთვის. ყველა ახლად დაინსტალირებული პაკეტი, რომელიც არ არის flatpaks, შედგა და ხელმისაწვდომი იქნება მხოლოდ სისტემის გადატვირთვის შემდეგ.",
        "km": "ប្រព័ន្ធនេះប្រើ rpm-ostree សម្រាប់ការធ្វើបច្ចុប្បន្នភាពអាតូម។ 패ッケջ ដែលបានដំឡើងថ្មីក្រោយ ដែលមិនមែន flatpaks នឹងត្រូវបានផ្សព្វផ្សាយ ហើយមាន តែបន្ទាប់ពីការចាប់ផ្តើមប្រព័ន្ធឡើងវិញ។",
        "ko": "이 시스템은 원자적 업데이트에 rpm-ostree를 사용합니다. flatpaks가 아닌 새로 설치된 모든 패키지는 시스템 재부팅 후에만 배포되고 사용 가능합니다.",
        "lo": "ລະບົບນີ້ໃຊ້ rpm-ostree ສໍາລັບການອັບເດດ atomic. ທຸກໆແພັກເກັດທີ່ຖືກຕິດຕັ້ງໃໝ່ທີ່ບໍ່ແມ່ນ flatpaks ຈະຖືກຈັດໃຫ້ແລະ ສາມາດໃຊ້ໄດ້ພຽງຫຼັງຈາກການຣີສະตາର์ຕລະບົບ.",
        "lt": "Ši sistema rpm-ostree naudoja atominiam atnaujinimui. Visi neseniai įdiegti paketai, kurie nėra flatpaks, bus diegiami ir prieinami tik po sistemos perkrovimo.",
        "lv": "Šī sistēma rpm-ostree izmanto atomu atjauninājumiem. Visi nesen instalētie paketi, kas nav flatpaks, tiks izvietoti un pieejami tikai pēc sistēmas restarta.",
        "mn": "Энэ систем атомын шинэчлэлтийн хувьд rpm-ostree ашигладаг. Шинээр суулгасан бүх пакет (flatpaks биш) нь системийг дахин эхлүүлсний дараа л байрлалаа өөрчилж, ашигладаг байх болно.",
        "ms": "Sistem ini menggunakan rpm-ostree untuk pembaruan atom. Semua paket yang baru dipasang yang bukan flatpaks hanya akan dikerahkan dan tersedia setelah sistem dimulai ulang.",
        "my": "ဤစနစ်သည် အက်တမ်အဆင့်မြှင့်တင်မှုအတွက် rpm-ostree ကိုအသုံးပြုသည်။ flatpaks မဟုတ်သည့်နွေးထပ်တင်ထားသည့်패ッケജအားလုံးသည် စနစ်ကို ပြန်လည်စတင်ပြီးနောက်ပိုင်းတွင်သာ လိုက်နာအောင်ပြုလုပ်ပြီး ရရှိနိုင်ပါသည်။",
        "nb": "Dette systemet bruker rpm-ostree for atomiske oppdateringer. Alle nylig installerte pakker som ikke er flatpaks vil kun bli implementert og tilgjengelig etter en systemomstart.",
        "ne": "यो सिस्टम परमाणु अपडेटको लागि rpm-ostree प्रयोग गर्छ। सबै नयाँ स्थापित प्याकेजहरू जो flatpaks छैनन् सिस्टम रीबुट पछि मात्र तैनात र उपलब्ध हुनेछन्।",
        "nl": "Dit systeem gebruikt rpm-ostree voor atomaire updates. Alle recent geïnstalleerde pakketten die geen flatpaks zijn, worden alleen na een systeemherstart geïmplementeerd en beschikbaar.",
        "pl": "System ten używa rpm-ostree do atomowych aktualizacji. Wszystkie nowo zainstalowane pakiety, które nie są flatpaks, będą wdrażane i dostępne dopiero po ponownym uruchomieniu systemu.",
        "pt": "Este sistema usa rpm-ostree para atualizações atômicas. Todos os pacotes recém-instalados que não sejam flatpaks serão implantados e disponibilizados apenas após uma reinicialização do sistema.",
        "ro": "Acest sistem utilizează rpm-ostree pentru actualizări atomice. Toate pachetele recent instalate care nu sunt flatpaks vor fi implementate și disponibile doar după o repornire a sistemului.",
        "ru": "Эта система использует rpm-ostree для атомных обновлений. Все недавно установленные пакеты, которые не являются flatpaks, будут развернуты и доступны только после перезагрузки системы.",
        "sk": "Tento systém používa rpm-ostree na atómové aktualizácie. Všetky nowo nainštalované balíčky, ktoré nie sú flatpakmi, budú nasadené a dostupné len po reštarte systému.",
        "sl": "Ta sistem uporablja rpm-ostree za atomske posodobitve. Vsi novo nameščeni paketi, ki niso flatpaks, bodo nameščeni in dostopni samo po ponovnem zagonu sistema.",
        "sq": "Ky sistem përdor rpm-ostree për përditësime atomike. Të gjithë paketat e sapo instaluara që nuk janë flatpaks do të shpërndahen dhe do të jenë të disponueshme vetëm pas një rimjete të sistemit.",
        "sr": "Овај систем користи rpm-ostree за атомске ажурирања. Сви недавно инсталирани пакети који нису flatpaks ће бити постављени и доступни само после поновног покретања система.",
        "sv": "Det här systemet använder rpm-ostree för atomiska uppdateringar. Alla nyligen installerade paket som inte är flatpaks kommer endast att distribueras och vara tillgängliga efter en systemomstart.",
        "sw": "Mfumo huu unatumia rpm-ostree kwa sasisho la atomiki. Pakiti zote zilizosakinishi hivi karibuni ambazo sio flatpaks zitakuwa zimefanywa kazi na zitakuwa zinapatikana tu baada ya kusimama upya kwa mfumo.",
        "ta": "இந்த கணினி அணு மேம்பாടுக்கு rpm-ostree ஐ பயன்படுத்துகிறது. சமீபத்தில் நிறுவப்பட்ட அனைத்து பொதிப்புகளும் flatpaks அல்ல, கணினி மீண்டும் தொடங்கிய பின்பு மட்டுமே நிবந்தனை செய்யப்பட்டு கிடைக்கும்।",
        "tg": "Ин система rpm-ostree-ро барои навасозии атомӣ истифода мебарад. Ҳама-и бастаҳои оро ҳол суб кардашудае, ки flatpaks нестанд, танҳо баъди инициализатсияи такрорӣ системаи барқарор карда мешавад ва дастрас мешавад.",
        "th": "ระบบนี้ใช้ rpm-ostree สำหรับการอัปเดตแบบอะตอมิก แพคเกจใหม่ที่ติดตั้งทั้งหมดที่ไม่ใช่ flatpaks จะถูกปรับใช้และพร้อมใช้งานได้เฉพาะหลังจากการรีสตาร์ทระบบ",
        "tl": "Ang sistemang ito ay gumagamit ng rpm-ostree para sa atomic updates. Lahat ng bagong nakalunsad na pakete na hindi flatpaks ay idideployar at magiging available lamang pagkatapos ng system restart.",
        "tr": "Bu sistem atomik güncellemeler için rpm-ostree kullanır. Yeni kurulan flatpaklar olmayan tüm paketler yalnızca sistem yeniden başlatıldıktan sonra dağıtılacak ve kullanılabilir olacaktır.",
        "uk": "Ця система використовує rpm-ostree для атомних оновлень. Усі недавно встановлені пакети, які не є flatpaks, будуть розгорнуті та доступні лише після перезавантаження системи.",
        "ur": "یہ نظام ایٹمی اپ ڈیٹس کے لیے rpm-ostree استعمال کرتا ہے۔ تمام حال ہی میں انسٹال کردہ پیکیجز جو flatpaks نہیں ہیں صرف سسٹم ری بوٹ کے بعد ہی تعینات اور دستیاب ہوں گے۔",
        "uz": "Bu sistema atom yangartirish uchun rpm-ostree-dan foydalanadi. Yaqinda o'rnatilgan flatpaks bo'lmagan barcha paketlar sistem qayta ishga tushurilgandan keyin amalga oshiriladi va mavjud bo'ladi.",
        "vi": "Hệ thống này sử dụng rpm-ostree để cập nhật nguyên tử. Tất cả các gói mới được cài đặt không phải flatpaks sẽ chỉ được triển khai và có sẵn sau khi khởi động lại hệ thống.",
        "zh": "此系统使用rpm-ostree进行原子更新。任何新安装的不是flatpaks的软件包只有在系统重新启动后才会部署并可用。"
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

#!/usr/bin/env python3
"""
Script to add translations to all language .lib files
"""

import os

# The base directory containing language files
LANG_DIR = "../p3/libs/lang"

# Translations for all messages across all supported languages
TRANSLATIONS = {
    'am.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="dnsmasq ተገኝቷል። እንደ DNS መሸጎጫ እየተጠቀሙበት ከሆነ፣ libvirt ችግር ሊፈጥር እና ግንኙነትዎ የDNS ጥያቄዎችን መፍታት እንዳይችል ሊያደርግ ይችላል። ለማንኛውም ይቀጥሉ?"'
    },
    'ar.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="تم اكتشاف dnsmasq. إذا كنت تستخدمه كذاكرة تخزين مؤقت لـ DNS، فقد يتسبب libvirt في حدوث مشكلات ويجعل اتصالك غير قادر على حل طلبات DNS. هل تريد المتابعة على أي حال؟"'
    },
    'az.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="dnsmasq aşkarlandı. Əgər onu DNS keşi kimi istifadə edirsinizsə, libvirt problemlər yarada və bağlantınızın DNS sorğularını həll etməsinə mane ola bilər. Yenə də davam edilsin?"'
    },
    'bg.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="Открит е dnsmasq. Ако го използвате като DNS кеш, libvirt може да причини проблеми и да попречи на връзката ви да разрешава DNS заявки. Искате ли да продължите въпреки това?"'
    },
    'bn.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="dnsmasq শনাক্ত করা হয়েছে। আপনি যদি এটিকে DNS ক্যাশ হিসেবে ব্যবহার করেন, তাহলে libvirt সমস্যা সৃষ্টি করতে পারে এবং আপনার সংযোগকে DNS অনুরোধ সমাধান করতে অক্ষম করে দিতে পারে। তবুও এগিয়ে যাবেন?"'
    },
    'bs.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="Otkriven je dnsmasq. Ako ga koristite kao DNS keš, libvirt može uzrokovati probleme i onemogućiti vašoj vezi razrješavanje DNS zahtjeva. Ipak nastaviti?"'
    },
    'cs.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="Byl zjištěn dnsmasq. Pokud jej používáte jako mezipaměť DNS, může libvirt způsobit problémy a znemožnit vašemu připojení překlad DNS požadavků. Přesto pokračovat?"'
    },
    'da.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="dnsmasq blev fundet. Hvis du bruger den som DNS-cache, kan libvirt forårsage problemer og gøre din forbindelse ude af stand til at opløse DNS-forespørgsler. Fortsæt alligevel?"'
    },
    'de.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="dnsmasq wurde erkannt. Wenn Sie es als DNS-Cache verwenden, kann libvirt Probleme verursachen und dazu führen, dass Ihre Verbindung keine DNS-Anfragen mehr auflösen kann. Trotzdem fortfahren?"'
    },
    'el.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="Εντοπίστηκε το dnsmasq. Εάν το χρησιμοποιείτε ως προσωρινή μνήμη DNS, το libvirt ενδέχεται να προκαλέσει προβλήματα και να εμποδίσει τη σύνδεσή σας να επιλύει αιτήματα DNS. Συνέχεια ούτως ή άλλως;"'
    },
    'es.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="Se detectó dnsmasq. Si lo utiliza como caché de DNS, libvirt puede causar problemas e impedir que su conexión resuelva solicitudes DNS. ¿Continuar de todos modos?"'
    },
    'et.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="Tuvastati dnsmasq. Kui kasutate seda DNS-i vahemäluna, võib libvirt põhjustada probleeme ja takistada teie ühendusel DNS-päringute lahendamist. Kas jätkata ikkagi?"'
    },
    'fa.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="dnsmasq شناسایی شد. اگر از آن به‌عنوان حافظه نهان DNS استفاده می‌کنید، libvirt ممکن است باعث بروز مشکل شود و اتصال شما را از حل درخواست‌های DNS بازدارد. با این حال ادامه داده شود؟"'
    },
    'fi.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="dnsmasq havaittiin. Jos käytät sitä DNS-välimuistina, libvirt voi aiheuttaa ongelmia ja estää yhteyttäsi selvittämästä DNS-pyyntöjä. Jatketaanko silti?"'
    },
    'fr.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="dnsmasq a été détecté. Si vous l’utilisez comme cache DNS, libvirt peut provoquer des problèmes et empêcher votre connexion de résoudre les requêtes DNS. Continuer quand même ?"'
    },
    'ga.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="Braitheadh dnsmasq. Má tá tú á úsáid mar thaisce DNS, d’fhéadfadh libvirt fadhbanna a chruthú agus cosc a chur ar do cheangal iarratais DNS a réiteach. Lean ar aghaidh mar sin féin?"'
    },
    'he.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="זוהה dnsmasq. אם נעשה בו שימוש כמטמון DNS, ‏libvirt עלול לגרום לבעיות ולמנוע מהחיבור שלך לפתור בקשות DNS. להמשיך בכל זאת?"'
    },
    'hi.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="dnsmasq का पता चला है। यदि आप इसे DNS कैश के रूप में उपयोग कर रहे हैं, तो libvirt समस्याएँ पैदा कर सकता है और आपके कनेक्शन को DNS अनुरोध हल करने में असमर्थ बना सकता है। फिर भी आगे बढ़ें?"'
    },
    'hr.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="Otkriven je dnsmasq. Ako ga koristite kao DNS predmemoriju, libvirt može uzrokovati probleme i onemogućiti vašoj vezi razrješavanje DNS zahtjeva. Ipak nastaviti?"'
    },
    'hu.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="A rendszer dnsmasq szolgáltatást észlelt. Ha DNS-gyorsítótárként használja, a libvirt problémákat okozhat, és megakadályozhatja, hogy a kapcsolat DNS-kéréseket oldjon fel. Mindenképpen folytatja?"'
    },
    'hy.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="Հայտնաբերվել է dnsmasq։ Եթե այն օգտագործում եք որպես DNS քեշ, libvirt-ը կարող է խնդիրներ առաջացնել և խանգարել ձեր կապին DNS հարցումները լուծել։ Շարունակե՞լ այնուամենայնիվ։"'
    },
    'id.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="dnsmasq terdeteksi. Jika Anda menggunakannya sebagai cache DNS, libvirt dapat menyebabkan masalah dan membuat koneksi Anda tidak dapat meresolusi permintaan DNS. Tetap lanjutkan?"'
    },
    'is.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="dnsmasq fannst. Ef þú notar það sem DNS-skyndiminni getur libvirt valdið vandamálum og komið í veg fyrir að tengingin þín geti leyst DNS-beiðnir. Halda samt áfram?"'
    },
    'it.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="È stato rilevato dnsmasq. Se lo utilizzi come cache DNS, libvirt potrebbe causare problemi e impedire alla tua connessione di risolvere le richieste DNS. Procedere comunque?"'
    },
    'ja.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="dnsmasq が検出されました。DNS キャッシュとして使用している場合、libvirt が問題を引き起こし、接続で DNS リクエストを解決できなくなる可能性があります。それでも続行しますか？"'
    },
    'ka.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="აღმოჩენილია dnsmasq. თუ მას DNS ქეშად იყენებთ, libvirt-მა შეიძლება პრობლემები გამოიწვიოს და თქვენს კავშირს DNS მოთხოვნების ამოხსნა აღარ შეეძლოს. მაინც გაგრძელდეს?"'
    },
    'km.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="បានរកឃើញ dnsmasq។ ប្រសិនបើអ្នកកំពុងប្រើវាជាឃ្លាំងសម្ងាត់ DNS នោះ libvirt អាចបង្កបញ្ហា និងធ្វើឱ្យការតភ្ជាប់របស់អ្នកមិនអាចដោះស្រាយសំណើ DNS បាន។ តើនៅតែបន្តឬ?"'
    },
    'ko.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="dnsmasq가 감지되었습니다. DNS 캐시로 사용 중인 경우 libvirt로 인해 문제가 발생하여 연결에서 DNS 요청을 확인할 수 없게 될 수 있습니다. 그래도 계속하시겠습니까?"'
    },
    'lo.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="ກວດພົບ dnsmasq. ຖ້າທ່ານໃຊ້ມັນເປັນແຄດ DNS, libvirt ອາດເຮັດໃຫ້ເກີດບັນຫາ ແລະ ເຮັດໃຫ້ການເຊື່ອມຕໍ່ຂອງທ່ານບໍ່ສາມາດແກ້ໄຂຄຳຮ້ອງຂໍ DNS ໄດ້. ຍັງຈະສືບຕໍ່ບໍ?"'
    },
    'lt.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="Aptiktas dnsmasq. Jei naudojate jį kaip DNS podėlį, libvirt gali sukelti problemų ir neleisti jūsų ryšiui išspręsti DNS užklausų. Vis tiek tęsti?"'
    },
    'lv.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="Tika konstatēts dnsmasq. Ja izmantojat to kā DNS kešatmiņu, libvirt var radīt problēmas un neļaut savienojumam atrisināt DNS pieprasījumus. Vai tomēr turpināt?"'
    },
    'mn.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="dnsmasq илэрлээ. Хэрэв та үүнийг DNS кэш болгон ашиглаж байгаа бол libvirt асуудал үүсгэж, таны холболт DNS хүсэлтүүдийг шийдвэрлэх боломжгүй болж магадгүй. Ямартай ч үргэлжлүүлэх үү?"'
    },
    'ms.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="dnsmasq dikesan. Jika anda menggunakannya sebagai cache DNS, libvirt mungkin menyebabkan masalah dan menjadikan sambungan anda tidak dapat menyelesaikan permintaan DNS. Teruskan juga?"'
    },
    'my.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="dnsmasq ကို တွေ့ရှိထားသည်။ ၎င်းကို DNS cache အဖြစ် အသုံးပြုနေပါက libvirt သည် ပြဿနာများ ဖြစ်စေနိုင်ပြီး သင့်ချိတ်ဆက်မှုမှ DNS တောင်းဆိုချက်များကို ဖြေရှင်းနိုင်ခြင်း မရှိစေနိုင်ပါသည်။ ဆက်လက်လုပ်ဆောင်မည်လား?"'
    },
    'nb.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="dnsmasq ble oppdaget. Hvis du bruker den som DNS-hurtigbuffer, kan libvirt forårsake problemer og gjøre at tilkoblingen din ikke kan løse DNS-forespørsler. Fortsette likevel?"'
    },
    'ne.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="dnsmasq पत्ता लागेको छ। यदि तपाईं यसलाई DNS क्यासको रूपमा प्रयोग गर्दै हुनुहुन्छ भने, libvirt ले समस्या निम्त्याउन सक्छ र तपाईंको जडानलाई DNS अनुरोधहरू समाधान गर्न असमर्थ बनाउन सक्छ। तैपनि अगाडि बढ्ने?"'
    },
    'nl.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="dnsmasq is gedetecteerd. Als u het als DNS-cache gebruikt, kan libvirt problemen veroorzaken waardoor uw verbinding geen DNS-verzoeken meer kan oplossen. Toch doorgaan?"'
    },
    'pl.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="Wykryto dnsmasq. Jeśli używasz go jako pamięci podręcznej DNS, libvirt może powodować problemy i uniemożliwić połączeniu rozwiązywanie zapytań DNS. Kontynuować mimo to?"'
    },
    'pt.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="O dnsmasq foi detectado. Se você o utiliza como cache DNS, o libvirt pode causar problemas e fazer com que sua conexão não consiga resolver solicitações DNS. Continuar mesmo assim?"'
    },
    'ro.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="A fost detectat dnsmasq. Dacă îl utilizați drept cache DNS, libvirt poate cauza probleme și poate împiedica conexiunea să rezolve cererile DNS. Continuați oricum?"'
    },
    'ru.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="Обнаружен dnsmasq. Если вы используете его в качестве DNS-кэша, libvirt может вызвать проблемы и лишить ваше соединение возможности разрешать DNS-запросы. Всё равно продолжить?"'
    },
    'sk.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="Bol zistený dnsmasq. Ak ho používate ako vyrovnávaciu pamäť DNS, libvirt môže spôsobiť problémy a zabrániť vášmu pripojeniu v preklade DNS požiadaviek. Napriek tomu pokračovať?"'
    },
    'sl.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="Zaznan je bil dnsmasq. Če ga uporabljate kot predpomnilnik DNS, lahko libvirt povzroči težave in vaši povezavi onemogoči razreševanje zahtev DNS. Vseeno nadaljujem?"'
    },
    'sq.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="U zbulua dnsmasq. Nëse po e përdorni si cache DNS, libvirt mund të shkaktojë probleme dhe ta bëjë lidhjen tuaj të paaftë për të zgjidhur kërkesat DNS. Të vazhdohet gjithsesi?"'
    },
    'sr.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="Откривен је dnsmasq. Ако га користите као DNS кеш, libvirt може изазвати проблеме и онемогућити вашој вези да разрешава DNS захтеве. Ипак наставити?"'
    },
    'sv.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="dnsmasq upptäcktes. Om du använder den som DNS-cache kan libvirt orsaka problem och göra att din anslutning inte kan lösa DNS-förfrågningar. Fortsätt ändå?"'
    },
    'sw.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="dnsmasq imegunduliwa. Ikiwa unaitumia kama akiba ya DNS, libvirt inaweza kusababisha matatizo na kufanya muunganisho wako ushindwe kutatua maombi ya DNS. Uendelee hata hivyo?"'
    },
    'ta.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="dnsmasq கண்டறியப்பட்டது. இதை DNS தற்காலிக சேமிப்பாகப் பயன்படுத்தினால், libvirt சிக்கல்களை ஏற்படுத்தி உங்கள் இணைப்பால் DNS கோரிக்கைகளைத் தீர்க்க முடியாமல் போகலாம். இருப்பினும் தொடரவா?"'
    },
    'tg.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="dnsmasq муайян карда шуд. Агар шумо онро ҳамчун кэши DNS истифода баред, libvirt метавонад мушкилот эҷод кунад ва пайвасти шуморо аз ҳалли дархостҳои DNS боздорад. Ба ҳар ҳол идома дода шавад?"'
    },
    'th.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="ตรวจพบ dnsmasq หากคุณใช้เป็นแคช DNS, libvirt อาจทำให้เกิดปัญหาและทำให้การเชื่อมต่อของคุณไม่สามารถแก้ไขคำขอ DNS ได้ ต้องการดำเนินการต่อหรือไม่?"'
    },
    'tl.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="Natukoy ang dnsmasq. Kung ginagamit mo ito bilang DNS cache, maaaring magdulot ng problema ang libvirt at gawing hindi kayang lutasin ng iyong koneksyon ang mga kahilingan sa DNS. Magpatuloy pa rin?"'
    },
    'tr.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="dnsmasq algılandı. DNS önbelleği olarak kullanıyorsanız libvirt sorunlara yol açabilir ve bağlantınızın DNS isteklerini çözümleyememesine neden olabilir. Yine de devam edilsin mi?"'
    },
    'uk.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="Виявлено dnsmasq. Якщо ви використовуєте його як DNS-кеш, libvirt може спричинити проблеми та позбавити ваше з’єднання можливості розв’язувати DNS-запити. Усе одно продовжити?"'
    },
    'ur.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="dnsmasq کا پتہ چلا ہے۔ اگر آپ اسے DNS کیش کے طور پر استعمال کر رہے ہیں تو libvirt مسائل پیدا کر سکتا ہے اور آپ کے کنکشن کو DNS درخواستیں حل کرنے سے روک سکتا ہے۔ پھر بھی آگے بڑھیں؟"'
    },
    'uz.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="dnsmasq aniqlandi. Agar undan DNS keshi sifatida foydalanayotgan bo‘lsangiz, libvirt muammolarga sabab bo‘lishi va ulanishingiz DNS so‘rovlarini hal qila olmay qolishiga olib kelishi mumkin. Shunga qaramay davom etilsinmi?"'
    },
    'vi.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="Đã phát hiện dnsmasq. Nếu bạn đang sử dụng nó làm bộ nhớ đệm DNS, libvirt có thể gây ra sự cố và khiến kết nối của bạn không thể phân giải các yêu cầu DNS. Vẫn tiếp tục?"'
    },
    'zh.lib': {
        'libvirtdnsmasq': 'libvirtdnsmasq="检测到 dnsmasq。如果您将其用作 DNS 缓存，libvirt 可能会引发问题，导致您的连接无法解析 DNS 请求。仍要继续吗？"'
    }
}

def add_translations_to_file(filepath, translations_dict):
    """Add translations to the specified .lib file"""
    try:
        # Read the current file content
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        added_count = 0
        skipped_count = 0

        # Add each translation
        for msg_id, translation in translations_dict.items():
            if f'{msg_id}=' in content:
                print(f"  {msg_id} already exists, skipping...")
                skipped_count += 1
            else:
                # Add the translation at the end
                if not content.endswith('\n'):
                    content += '\n'
                content += translation + '\n'
                added_count += 1

        # Write back to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return added_count, skipped_count

    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return 0, 0

def main():
    """Main function to add translations to all language files"""
    total_added = 0
    total_skipped = 0
    errors = 0

    print("Adding translations to all language files...")
    print("=" * 70)

    for filename, translations in TRANSLATIONS.items():
        filepath = os.path.join(LANG_DIR, filename)

        if os.path.exists(filepath):
            print(f"Processing {filename}...")
            added, skipped = add_translations_to_file(filepath, translations)
            total_added += added
            total_skipped += skipped

            if added > 0:
                print(f"  Added {added} translations")
            if skipped > 0:
                print(f"  Skipped {skipped} (already exist)")
        else:
            print(f"File not found: {filepath}")
            errors += 1

    print("=" * 70)
    print("Summary:")
    print(f"  Total added: {total_added}")
    print(f"  Total skipped: {total_skipped}")
    print(f"  Files with errors: {errors}")

if __name__ == "__main__":
    main()

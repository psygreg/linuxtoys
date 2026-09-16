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
        'parumsg': 'parumsg="LinuxToys የAUR ጥቅሎችን ለማስተዳደር paru ያስፈልገዋል። አሁን ይጫናል።"',
        'gearlevermsg': 'gearlevermsg="LinuxToys የAppImage ጥቅሎችን ለማስተዳደር Gear Lever ያስፈልገዋል። አሁን ይጫናል።"'
    },
    'ar.lib': {
        'parumsg': 'parumsg="يتطلب LinuxToys برنامج paru للتعامل مع حزم AUR. سيتم تثبيته الآن."',
        'gearlevermsg': 'gearlevermsg="يتطلب LinuxToys برنامج Gear Lever للتعامل مع حزم AppImage. سيتم تثبيته الآن."'
    },
    'az.lib': {
        'parumsg': 'parumsg="LinuxToys-un AUR paketlərini idarə etməsi üçün paru tələb olunur. İndi quraşdırılacaq."',
        'gearlevermsg': 'gearlevermsg="LinuxToys-un AppImage paketlərini idarə etməsi üçün Gear Lever tələb olunur. İndi quraşdırılacaq."'
    },
    'bg.lib': {
        'parumsg': 'parumsg="paru е необходим, за да може LinuxToys да обработва AUR пакети. Той ще бъде инсталиран сега."',
        'gearlevermsg': 'gearlevermsg="Gear Lever е необходим, за да може LinuxToys да обработва AppImage пакети. Той ще бъде инсталиран сега."'
    },
    'bn.lib': {
        'parumsg': 'parumsg="LinuxToys-এর AUR প্যাকেজ পরিচালনার জন্য paru প্রয়োজন। এটি এখন ইনস্টল করা হবে।"',
        'gearlevermsg': 'gearlevermsg="LinuxToys-এর AppImage প্যাকেজ পরিচালনার জন্য Gear Lever প্রয়োজন। এটি এখন ইনস্টল করা হবে।"'
    },
    'bs.lib': {
        'parumsg': 'parumsg="paru je potreban da bi LinuxToys mogao upravljati AUR paketima. Sada će biti instaliran."',
        'gearlevermsg': 'gearlevermsg="Gear Lever je potreban da bi LinuxToys mogao upravljati AppImage paketima. Sada će biti instaliran."'
    },
    'cs.lib': {
        'parumsg': 'parumsg="paru je vyžadován, aby LinuxToys mohl pracovat s balíčky AUR. Nyní bude nainstalován."',
        'gearlevermsg': 'gearlevermsg="Gear Lever je vyžadován, aby LinuxToys mohl pracovat s balíčky AppImage. Nyní bude nainstalován."'
    },
    'da.lib': {
        'parumsg': 'parumsg="paru er påkrævet, for at LinuxToys kan håndtere AUR-pakker. Det installeres nu."',
        'gearlevermsg': 'gearlevermsg="Gear Lever er påkrævet, for at LinuxToys kan håndtere AppImage-pakker. Det installeres nu."'
    },
    'de.lib': {
        'parumsg': 'parumsg="paru wird benötigt, damit LinuxToys AUR-Pakete verwalten kann. Es wird jetzt installiert."',
        'gearlevermsg': 'gearlevermsg="Gear Lever wird benötigt, damit LinuxToys AppImage-Pakete verwalten kann. Es wird jetzt installiert."'
    },
    'el.lib': {
        'parumsg': 'parumsg="Το paru απαιτείται ώστε το LinuxToys να μπορεί να διαχειρίζεται πακέτα AUR. Θα εγκατασταθεί τώρα."',
        'gearlevermsg': 'gearlevermsg="Το Gear Lever απαιτείται ώστε το LinuxToys να μπορεί να διαχειρίζεται πακέτα AppImage. Θα εγκατασταθεί τώρα."'
    },
    'es.lib': {
        'parumsg': 'parumsg="paru es necesario para que LinuxToys pueda gestionar paquetes de AUR. Se instalará ahora."',
        'gearlevermsg': 'gearlevermsg="Gear Lever es necesario para que LinuxToys pueda gestionar paquetes AppImage. Se instalará ahora."'
    },
    'et.lib': {
        'parumsg': 'parumsg="LinuxToys vajab AUR-pakettide haldamiseks paru. See paigaldatakse nüüd."',
        'gearlevermsg': 'gearlevermsg="LinuxToys vajab AppImage-pakettide haldamiseks Gear Leverit. See paigaldatakse nüüd."'
    },
    'fa.lib': {
        'parumsg': 'parumsg="برای مدیریت بسته‌های AUR توسط LinuxToys، paru مورد نیاز است. اکنون نصب خواهد شد."',
        'gearlevermsg': 'gearlevermsg="برای مدیریت بسته‌های AppImage توسط LinuxToys، Gear Lever مورد نیاز است. اکنون نصب خواهد شد."'
    },
    'fi.lib': {
        'parumsg': 'parumsg="LinuxToys tarvitsee paru-ohjelman AUR-pakettien käsittelyyn. Se asennetaan nyt."',
        'gearlevermsg': 'gearlevermsg="LinuxToys tarvitsee Gear Leverin AppImage-pakettien käsittelyyn. Se asennetaan nyt."'
    },
    'fr.lib': {
        'parumsg': 'parumsg="paru est requis pour permettre à LinuxToys de gérer les paquets AUR. Il va maintenant être installé."',
        'gearlevermsg': 'gearlevermsg="Gear Lever est requis pour permettre à LinuxToys de gérer les paquets AppImage. Il va maintenant être installé."'
    },
    'ga.lib': {
        'parumsg': 'parumsg="Tá paru riachtanach chun go mbeidh LinuxToys in ann pacáistí AUR a láimhseáil. Suiteálfar anois é."',
        'gearlevermsg': 'gearlevermsg="Tá Gear Lever riachtanach chun go mbeidh LinuxToys in ann pacáistí AppImage a láimhseáil. Suiteálfar anois é."'
    },
    'he.lib': {
        'parumsg': 'parumsg="paru נדרש כדי ש-LinuxToys יוכל לטפל בחבילות AUR. הוא יותקן כעת."',
        'gearlevermsg': 'gearlevermsg="Gear Lever נדרש כדי ש-LinuxToys יוכל לטפל בחבילות AppImage. הוא יותקן כעת."'
    },
    'hi.lib': {
        'parumsg': 'parumsg="LinuxToys को AUR पैकेज संभालने के लिए paru की आवश्यकता है। इसे अब इंस्टॉल किया जाएगा।"',
        'gearlevermsg': 'gearlevermsg="LinuxToys को AppImage पैकेज संभालने के लिए Gear Lever की आवश्यकता है। इसे अब इंस्टॉल किया जाएगा।"'
    },
    'hr.lib': {
        'parumsg': 'parumsg="paru je potreban kako bi LinuxToys mogao upravljati AUR paketima. Sada će biti instaliran."',
        'gearlevermsg': 'gearlevermsg="Gear Lever je potreban kako bi LinuxToys mogao upravljati AppImage paketima. Sada će biti instaliran."'
    },
    'hu.lib': {
        'parumsg': 'parumsg="A LinuxToys számára a paru szükséges az AUR-csomagok kezeléséhez. Most telepítésre kerül."',
        'gearlevermsg': 'gearlevermsg="A LinuxToys számára a Gear Lever szükséges az AppImage-csomagok kezeléséhez. Most telepítésre kerül."'
    },
    'hy.lib': {
        'parumsg': 'parumsg="LinuxToys-ին AUR փաթեթները կառավարելու համար անհրաժեշտ է paru։ Այն այժմ կտեղադրվի։"',
        'gearlevermsg': 'gearlevermsg="LinuxToys-ին AppImage փաթեթները կառավարելու համար անհրաժեշտ է Gear Lever։ Այն այժմ կտեղադրվի։"'
    },
    'id.lib': {
        'parumsg': 'parumsg="paru diperlukan agar LinuxToys dapat menangani paket AUR. paru akan dipasang sekarang."',
        'gearlevermsg': 'gearlevermsg="Gear Lever diperlukan agar LinuxToys dapat menangani paket AppImage. Gear Lever akan dipasang sekarang."'
    },
    'is.lib': {
        'parumsg': 'parumsg="paru er nauðsynlegt svo LinuxToys geti meðhöndlað AUR-pakka. Það verður sett upp núna."',
        'gearlevermsg': 'gearlevermsg="Gear Lever er nauðsynlegt svo LinuxToys geti meðhöndlað AppImage-pakka. Það verður sett upp núna."'
    },
    'it.lib': {
        'parumsg': 'parumsg="paru è necessario affinché LinuxToys possa gestire i pacchetti AUR. Verrà installato ora."',
        'gearlevermsg': 'gearlevermsg="Gear Lever è necessario affinché LinuxToys possa gestire i pacchetti AppImage. Verrà installato ora."'
    },
    'ja.lib': {
        'parumsg': 'parumsg="LinuxToys で AUR パッケージを処理するには paru が必要です。今すぐインストールされます。"',
        'gearlevermsg': 'gearlevermsg="LinuxToys で AppImage パッケージを処理するには Gear Lever が必要です。今すぐインストールされます。"'
    },
    'ka.lib': {
        'parumsg': 'parumsg="LinuxToys-ს AUR პაკეტების სამართავად paru სჭირდება. ის ახლა დაინსტალირდება."',
        'gearlevermsg': 'gearlevermsg="LinuxToys-ს AppImage პაკეტების სამართავად Gear Lever სჭირდება. ის ახლა დაინსტალირდება."'
    },
    'km.lib': {
        'parumsg': 'parumsg="LinuxToys ត្រូវការ paru ដើម្បីគ្រប់គ្រងកញ្ចប់ AUR។ វានឹងត្រូវបានដំឡើងឥឡូវនេះ។"',
        'gearlevermsg': 'gearlevermsg="LinuxToys ត្រូវការ Gear Lever ដើម្បីគ្រប់គ្រងកញ្ចប់ AppImage។ វានឹងត្រូវបានដំឡើងឥឡូវនេះ។"'
    },
    'ko.lib': {
        'parumsg': 'parumsg="LinuxToys에서 AUR 패키지를 처리하려면 paru가 필요합니다. 지금 설치됩니다."',
        'gearlevermsg': 'gearlevermsg="LinuxToys에서 AppImage 패키지를 처리하려면 Gear Lever가 필요합니다. 지금 설치됩니다."'
    },
    'lo.lib': {
        'parumsg': 'parumsg="LinuxToys ຕ້ອງການ paru ເພື່ອຈັດການແພັກເກດ AUR. ມັນຈະຖືກຕິດຕັ້ງຕອນນີ້."',
        'gearlevermsg': 'gearlevermsg="LinuxToys ຕ້ອງການ Gear Lever ເພື່ອຈັດການແພັກເກດ AppImage. ມັນຈະຖືກຕິດຕັ້ງຕອນນີ້."'
    },
    'lt.lib': {
        'parumsg': 'parumsg="LinuxToys reikalingas paru AUR paketams tvarkyti. Jis bus įdiegtas dabar."',
        'gearlevermsg': 'gearlevermsg="LinuxToys reikalingas Gear Lever AppImage paketams tvarkyti. Jis bus įdiegtas dabar."'
    },
    'lv.lib': {
        'parumsg': 'parumsg="LinuxToys ir nepieciešams paru, lai apstrādātu AUR pakotnes. Tas tagad tiks instalēts."',
        'gearlevermsg': 'gearlevermsg="LinuxToys ir nepieciešams Gear Lever, lai apstrādātu AppImage pakotnes. Tas tagad tiks instalēts."'
    },
    'mn.lib': {
        'parumsg': 'parumsg="LinuxToys-д AUR багцуудыг удирдахын тулд paru шаардлагатай. Одоо суулгана."',
        'gearlevermsg': 'gearlevermsg="LinuxToys-д AppImage багцуудыг удирдахын тулд Gear Lever шаардлагатай. Одоо суулгана."'
    },
    'ms.lib': {
        'parumsg': 'parumsg="paru diperlukan supaya LinuxToys dapat mengendalikan pakej AUR. Ia akan dipasang sekarang."',
        'gearlevermsg': 'gearlevermsg="Gear Lever diperlukan supaya LinuxToys dapat mengendalikan pakej AppImage. Ia akan dipasang sekarang."'
    },
    'my.lib': {
        'parumsg': 'parumsg="LinuxToys မှ AUR ပက်ကေ့ဂျ်များကို ကိုင်တွယ်ရန် paru လိုအပ်ပါသည်။ ယခု ထည့်သွင်းပါမည်။"',
        'gearlevermsg': 'gearlevermsg="LinuxToys မှ AppImage ပက်ကေ့ဂျ်များကို ကိုင်တွယ်ရန် Gear Lever လိုအပ်ပါသည်။ ယခု ထည့်သွင်းပါမည်။"'
    },
    'nb.lib': {
        'parumsg': 'parumsg="paru kreves for at LinuxToys skal kunne håndtere AUR-pakker. Det installeres nå."',
        'gearlevermsg': 'gearlevermsg="Gear Lever kreves for at LinuxToys skal kunne håndtere AppImage-pakker. Det installeres nå."'
    },
    'ne.lib': {
        'parumsg': 'parumsg="LinuxToys लाई AUR प्याकेजहरू व्यवस्थापन गर्न paru आवश्यक छ। यो अब स्थापना गरिनेछ।"',
        'gearlevermsg': 'gearlevermsg="LinuxToys लाई AppImage प्याकेजहरू व्यवस्थापन गर्न Gear Lever आवश्यक छ। यो अब स्थापना गरिनेछ।"'
    },
    'nl.lib': {
        'parumsg': 'parumsg="paru is vereist zodat LinuxToys AUR-pakketten kan verwerken. Het wordt nu geïnstalleerd."',
        'gearlevermsg': 'gearlevermsg="Gear Lever is vereist zodat LinuxToys AppImage-pakketten kan verwerken. Het wordt nu geïnstalleerd."'
    },
    'pl.lib': {
        'parumsg': 'parumsg="paru jest wymagany, aby LinuxToys mógł obsługiwać pakiety AUR. Zostanie teraz zainstalowany."',
        'gearlevermsg': 'gearlevermsg="Gear Lever jest wymagany, aby LinuxToys mógł obsługiwać pakiety AppImage. Zostanie teraz zainstalowany."'
    },
    'pt.lib': {
        'parumsg': 'parumsg="O paru é necessário para que o LinuxToys possa gerenciar pacotes do AUR. Ele será instalado agora."',
        'gearlevermsg': 'gearlevermsg="O Gear Lever é necessário para que o LinuxToys possa gerenciar pacotes AppImage. Ele será instalado agora."'
    },
    'ro.lib': {
        'parumsg': 'parumsg="paru este necesar pentru ca LinuxToys să poată gestiona pachetele AUR. Acesta va fi instalat acum."',
        'gearlevermsg': 'gearlevermsg="Gear Lever este necesar pentru ca LinuxToys să poată gestiona pachetele AppImage. Acesta va fi instalat acum."'
    },
    'ru.lib': {
        'parumsg': 'parumsg="paru необходим LinuxToys для работы с пакетами AUR. Он будет установлен сейчас."',
        'gearlevermsg': 'gearlevermsg="Gear Lever необходим LinuxToys для работы с пакетами AppImage. Он будет установлен сейчас."'
    },
    'sk.lib': {
        'parumsg': 'parumsg="paru je potrebný, aby LinuxToys mohol pracovať s balíkmi AUR. Teraz bude nainštalovaný."',
        'gearlevermsg': 'gearlevermsg="Gear Lever je potrebný, aby LinuxToys mohol pracovať s balíkmi AppImage. Teraz bude nainštalovaný."'
    },
    'sl.lib': {
        'parumsg': 'parumsg="paru je potreben, da lahko LinuxToys upravlja pakete AUR. Zdaj bo nameščen."',
        'gearlevermsg': 'gearlevermsg="Gear Lever je potreben, da lahko LinuxToys upravlja pakete AppImage. Zdaj bo nameščen."'
    },
    'sq.lib': {
        'parumsg': 'parumsg="paru kërkohet që LinuxToys të mund të menaxhojë paketat AUR. Do të instalohet tani."',
        'gearlevermsg': 'gearlevermsg="Gear Lever kërkohet që LinuxToys të mund të menaxhojë paketat AppImage. Do të instalohet tani."'
    },
    'sr.lib': {
        'parumsg': 'parumsg="paru је неопходан да би LinuxToys могао да управља AUR пакетима. Сада ће бити инсталиран."',
        'gearlevermsg': 'gearlevermsg="Gear Lever је неопходан да би LinuxToys могао да управља AppImage пакетима. Сада ће бити инсталиран."'
    },
    'sv.lib': {
        'parumsg': 'parumsg="paru krävs för att LinuxToys ska kunna hantera AUR-paket. Det installeras nu."',
        'gearlevermsg': 'gearlevermsg="Gear Lever krävs för att LinuxToys ska kunna hantera AppImage-paket. Det installeras nu."'
    },
    'sw.lib': {
        'parumsg': 'parumsg="paru inahitajika ili LinuxToys iweze kushughulikia vifurushi vya AUR. Itasakinishwa sasa."',
        'gearlevermsg': 'gearlevermsg="Gear Lever inahitajika ili LinuxToys iweze kushughulikia vifurushi vya AppImage. Itasakinishwa sasa."'
    },
    'ta.lib': {
        'parumsg': 'parumsg="LinuxToys AUR தொகுப்புகளைக் கையாள paru தேவை. அது இப்போது நிறுவப்படும்."',
        'gearlevermsg': 'gearlevermsg="LinuxToys AppImage தொகுப்புகளைக் கையாள Gear Lever தேவை. அது இப்போது நிறுவப்படும்."'
    },
    'tg.lib': {
        'parumsg': 'parumsg="Барои коркарди бастаҳои AUR ба LinuxToys paru лозим аст. Он ҳоло насб карда мешавад."',
        'gearlevermsg': 'gearlevermsg="Барои коркарди бастаҳои AppImage ба LinuxToys Gear Lever лозим аст. Он ҳоло насб карда мешавад."'
    },
    'th.lib': {
        'parumsg': 'parumsg="LinuxToys ต้องใช้ paru เพื่อจัดการแพ็กเกจ AUR โดยจะติดตั้งตอนนี้"',
        'gearlevermsg': 'gearlevermsg="LinuxToys ต้องใช้ Gear Lever เพื่อจัดการแพ็กเกจ AppImage โดยจะติดตั้งตอนนี้"'
    },
    'tl.lib': {
        'parumsg': 'parumsg="Kinakailangan ang paru upang mapangasiwaan ng LinuxToys ang mga AUR package. Ii-install ito ngayon."',
        'gearlevermsg': 'gearlevermsg="Kinakailangan ang Gear Lever upang mapangasiwaan ng LinuxToys ang mga AppImage package. Ii-install ito ngayon."'
    },
    'tr.lib': {
        'parumsg': 'parumsg="LinuxToys\'un AUR paketlerini yönetebilmesi için paru gereklidir. Şimdi yüklenecek."',
        'gearlevermsg': 'gearlevermsg="LinuxToys\'un AppImage paketlerini yönetebilmesi için Gear Lever gereklidir. Şimdi yüklenecek."'
    },
    'uk.lib': {
        'parumsg': 'parumsg="paru потрібен LinuxToys для роботи з пакетами AUR. Його буде встановлено зараз."',
        'gearlevermsg': 'gearlevermsg="Gear Lever потрібен LinuxToys для роботи з пакетами AppImage. Його буде встановлено зараз."'
    },
    'ur.lib': {
        'parumsg': 'parumsg="LinuxToys کو AUR پیکیجز سنبھالنے کے لیے paru درکار ہے۔ اسے اب انسٹال کیا جائے گا۔"',
        'gearlevermsg': 'gearlevermsg="LinuxToys کو AppImage پیکیجز سنبھالنے کے لیے Gear Lever درکار ہے۔ اسے اب انسٹال کیا جائے گا۔"'
    },
    'uz.lib': {
        'parumsg': 'parumsg="LinuxToys AUR paketlarini boshqarishi uchun paru talab qilinadi. U hozir o‘rnatiladi."',
        'gearlevermsg': 'gearlevermsg="LinuxToys AppImage paketlarini boshqarishi uchun Gear Lever talab qilinadi. U hozir o‘rnatiladi."'
    },
    'vi.lib': {
        'parumsg': 'parumsg="LinuxToys cần paru để xử lý các gói AUR. paru sẽ được cài đặt ngay bây giờ."',
        'gearlevermsg': 'gearlevermsg="LinuxToys cần Gear Lever để xử lý các gói AppImage. Gear Lever sẽ được cài đặt ngay bây giờ."'
    },
    'zh.lib': {
        'parumsg': 'parumsg="LinuxToys 需要 paru 来处理 AUR 软件包。现在将安装 paru。"',
        'gearlevermsg': 'gearlevermsg="LinuxToys 需要 Gear Lever 来处理 AppImage 软件包。现在将安装 Gear Lever。"'
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

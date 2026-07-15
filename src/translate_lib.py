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
        'websoftwarewarning': 'websoftwarewarning="ከዚህ ጥገና በኋላ የመሣሪያ ቅንብሮችን ለማስተዳደር Flatpak ያልሆነ Chromium-መሠረት ያለው ድር አሳሽ አሁንም ያስፈልጋል።"'
    },
    'ar.lib': {
        'websoftwarewarning': 'websoftwarewarning="بعد تطبيق هذا التصحيح، سيظل متصفح ويب يعتمد على Chromium وغير مثبت عبر Flatpak مطلوبًا لإدارة إعدادات الجهاز."'
    },
    'az.lib': {
        'websoftwarewarning': 'websoftwarewarning="Bu yamaqdan sonra cihaz parametrlərini idarə etmək üçün hələ də Flatpak olmayan Chromium əsaslı veb brauzer tələb olunur."'
        },
    'bg.lib': {
        'websoftwarewarning': 'websoftwarewarning="След този пач все още е необходим уеб браузър, базиран на Chromium и който не е Flatpak, за да управлявате настройките на устройството."'
    },
    'bn.lib': {
        'websoftwarewarning': 'websoftwarewarning="এই প্যাচের পরেও ডিভাইসের সেটিংস পরিচালনার জন্য একটি নন-ফ্ল্যাটপ্যাক Chromium-ভিত্তিক ওয়েব ব্রাউজার প্রয়োজন হবে।"'
    },
    'bs.lib': {
        'websoftwarewarning': 'websoftwarewarning="Nakon ove zakrpe i dalje je potreban web preglednik zasnovan na Chromiumu koji nije Flatpak za upravljanje postavkama uređaja."'
    },
    'cs.lib': {
        'websoftwarewarning': 'websoftwarewarning="Po této opravě je stále vyžadován webový prohlížeč založený na Chromiu, který není Flatpak, pro správu nastavení zařízení."'
    },
    'da.lib': {
        'websoftwarewarning': 'websoftwarewarning="Efter denne rettelse kræves der stadig en Chromium-baseret webbrowser, som ikke er en Flatpak, for at administrere enhedsindstillinger."'
    },
    'de.lib': {
        'websoftwarewarning': 'websoftwarewarning="Nach diesem Patch wird weiterhin ein Chromium-basierter Webbrowser (nicht als Flatpak) benötigt, um die Geräteeinstellungen zu verwalten."'
    },
    'el.lib': {
        'websoftwarewarning': 'websoftwarewarning="Μετά από αυτήν την ενημέρωση εξακολουθεί να απαιτείται πρόγραμμα περιήγησης βασισμένο στο Chromium που δεν είναι Flatpak για τη διαχείριση των ρυθμίσεων της συσκευής."'
    },
    'es.lib': {
        'websoftwarewarning': 'websoftwarewarning="Después de este parche, aún se requiere un navegador web basado en Chromium que no sea Flatpak para administrar la configuración del dispositivo."'
    },
    'et.lib': {
        'websoftwarewarning': 'websoftwarewarning="Pärast seda parandust on seadme sätete haldamiseks endiselt vaja Chromiumi-põhist veebibrauserit, mis ei ole Flatpak."'
    },
    'fa.lib': {
        'websoftwarewarning': 'websoftwarewarning="پس از اعمال این وصله، همچنان برای مدیریت تنظیمات دستگاه به یک مرورگر وب مبتنی بر Chromium که Flatpak نباشد نیاز است."'
    },
    'fi.lib': {
        'websoftwarewarning': 'websoftwarewarning="Tämän korjauksen jälkeen laitteen asetusten hallintaan tarvitaan edelleen Chromium-pohjainen selain, joka ei ole Flatpak."'
    },
    'fr.lib': {
        'websoftwarewarning': 'websoftwarewarning="Après ce correctif, un navigateur Web basé sur Chromium non installé via Flatpak est toujours nécessaire pour gérer les paramètres de l’appareil."'
    },
    'ga.lib': {
        'websoftwarewarning': 'websoftwarewarning="Tar éis an paiste seo, beidh brabhsálaí gréasáin bunaithe ar Chromium nach Flatpak é fós ag teastáil chun socruithe an ghléis a bhainistiú."'
    },
    'he.lib': {
        'websoftwarewarning': 'websoftwarewarning="לאחר תיקון זה עדיין נדרש דפדפן מבוסס Chromium שאינו Flatpak כדי לנהל את הגדרות ההתקן."'
    },
    'hi.lib': {
        'websoftwarewarning': 'websoftwarewarning="इस पैच के बाद भी डिवाइस सेटिंग्स प्रबंधित करने के लिए एक गैर-Flatpak Chromium-आधारित वेब ब्राउज़र आवश्यक रहेगा।"'
    },
    'hr.lib': {
        'websoftwarewarning': 'websoftwarewarning="Nakon ove zakrpe i dalje je potreban web preglednik temeljen na Chromiumu koji nije Flatpak za upravljanje postavkama uređaja."'
    },
    'hu.lib': {
        'websoftwarewarning': 'websoftwarewarning="A javítás után továbbra is szükség van egy nem Flatpak Chromium-alapú webböngészőre az eszköz beállításainak kezeléséhez."'
    },
    'hy.lib': {
        'websoftwarewarning': 'websoftwarewarning="Այս թարմացումից հետո սարքի կարգավորումները կառավարելու համար դեռևս պահանջվում է Chromium-ի վրա հիմնված, ոչ Flatpak վեբ զննարկիչ։"'
    },
    'id.lib': {
        'websoftwarewarning': 'websoftwarewarning="Setelah patch ini, browser web berbasis Chromium yang bukan Flatpak masih diperlukan untuk mengelola pengaturan perangkat."'
    },
    'is.lib': {
        'websoftwarewarning': 'websoftwarewarning="Eftir þessa lagfæringu er enn þörf á Chromium-vafra sem ekki er Flatpak til að stjórna stillingum tækisins."'
    },
    'it.lib': {
        'websoftwarewarning': 'websoftwarewarning="Dopo questa patch, è ancora necessario un browser Web basato su Chromium non Flatpak per gestire le impostazioni del dispositivo."'
    },
    'ja.lib': {
        'websoftwarewarning': 'websoftwarewarning="このパッチ適用後も、デバイス設定を管理するには、Flatpak版ではないChromiumベースのWebブラウザーが必要です。"'
    },
    'ka.lib': {
        'websoftwarewarning': 'websoftwarewarning="ამ პატჩის შემდეგ მოწყობილობის პარამეტრების სამართავად კვლავ საჭიროა Chromium-ზე დაფუძნებული, არა-Flatpak ვებ-ბრაუზერი."'
    },
    'km.lib': {
        'websoftwarewarning': 'websoftwarewarning="បន្ទាប់ពីការកែប្រែនេះ នៅតែត្រូវការកម្មវិធីរុករកបណ្ដាញផ្អែកលើ Chromium ដែលមិនមែនជា Flatpak ដើម្បីគ្រប់គ្រងការកំណត់ឧបករណ៍។"'
    },
    'ko.lib': {
        'websoftwarewarning': 'websoftwarewarning="이 패치 후에도 장치 설정을 관리하려면 Flatpak이 아닌 Chromium 기반 웹 브라우저가 필요합니다."'
    },
    'lo.lib': {
        'websoftwarewarning': 'websoftwarewarning="ຫຼັງຈາກແພັດນີ້ ຍັງຈຳເປັນຕ້ອງໃຊ້ເວັບບຣາວເຊີທີ່ອີງໃສ່ Chromium ແລະບໍ່ແມ່ນ Flatpak ເພື່ອຈັດການການຕັ້ງຄ່າອຸປະກອນ."'
    },
    'lt.lib': {
        'websoftwarewarning': 'websoftwarewarning="Po šio pataisymo įrenginio nustatymams tvarkyti vis dar reikalinga Chromium pagrindu sukurta naršyklė, kuri nėra Flatpak."'
    },
    'lv.lib': {
        'websoftwarewarning': 'websoftwarewarning="Pēc šī ielāpa ierīces iestatījumu pārvaldībai joprojām ir nepieciešama uz Chromium balstīta tīmekļa pārlūkprogramma, kas nav Flatpak."'
    },
    'ms.lib': {
        'websoftwarewarning': 'websoftwarewarning="Selepas tampalan ini, pelayar web berasaskan Chromium yang bukan Flatpak masih diperlukan untuk mengurus tetapan peranti."'
    },
    'nb.lib': {
        'websoftwarewarning': 'websoftwarewarning="Etter denne oppdateringen kreves det fortsatt en Chromium-basert nettleser som ikke er en Flatpak for å administrere enhetsinnstillinger."'
    },
    'nl.lib': {
        'websoftwarewarning': 'websoftwarewarning="Na deze patch is nog steeds een niet-Flatpak Chromium-gebaseerde webbrowser vereist om de apparaatinstellingen te beheren."'
    },
    'pl.lib': {
        'websoftwarewarning': 'websoftwarewarning="Po zastosowaniu tej poprawki nadal wymagane jest korzystanie z przeglądarki internetowej opartej na Chromium, która nie jest zainstalowana jako Flatpak, aby zarządzać ustawieniami urządzenia."'
    },
    'pt.lib': {
        'websoftwarewarning': 'websoftwarewarning="Após este patch, ainda é necessário um navegador baseado em Chromium que não seja Flatpak para gerenciar as configurações do dispositivo."'
    },
    'ro.lib': {
        'websoftwarewarning': 'websoftwarewarning="După aplicarea acestui patch este în continuare necesar un browser web bazat pe Chromium, care nu este Flatpak, pentru a gestiona setările dispozitivului."'
    },
    'ru.lib': {
        'websoftwarewarning': 'websoftwarewarning="После применения этого патча для управления настройками устройства по-прежнему требуется веб-браузер на базе Chromium, установленный не через Flatpak."'
    },
    'sk.lib': {
        'websoftwarewarning': 'websoftwarewarning="Po tejto oprave je na správu nastavení zariadenia stále potrebný webový prehliadač založený na Chromiu, ktorý nie je Flatpak."'
    },
    'sl.lib': {
        'websoftwarewarning': 'websoftwarewarning="Po tem popravku je za upravljanje nastavitev naprave še vedno potreben spletni brskalnik, ki temelji na Chromiumu in ni Flatpak."'
    },
    'sq.lib': {
        'websoftwarewarning': 'websoftwarewarning="Pas këtij përditësimi kërkohet ende një shfletues uebi i bazuar në Chromium që nuk është Flatpak për të menaxhuar cilësimet e pajisjes."'
    },
    'sr.lib': {
        'websoftwarewarning': 'websoftwarewarning="Након ове исправке и даље је потребан веб-прегледач заснован на Chromium-у који није Flatpak за управљање подешавањима уређаја."'
    },
    'sv.lib': {
        'websoftwarewarning': 'websoftwarewarning="Efter denna uppdatering krävs fortfarande en Chromium-baserad webbläsare som inte är en Flatpak för att hantera enhetsinställningar."'
    },
    'sw.lib': {
        'websoftwarewarning': 'websoftwarewarning="Baada ya kiraka hiki, kivinjari cha wavuti kinachotegemea Chromium ambacho si Flatpak bado kinahitajika ili kudhibiti mipangilio ya kifaa."'
    },
    'ta.lib': {
        'websoftwarewarning': 'websoftwarewarning="இந்த திருத்தத்திற்குப் பிறகும் சாதன அமைப்புகளை நிர்வகிக்க Flatpak அல்லாத Chromium அடிப்படையிலான இணைய உலாவி இன்னும் தேவைப்படுகிறது."'
    },
    'tg.lib': {
        'websoftwarewarning': 'websoftwarewarning="Пас аз ин ислоҳ барои идоракунии танзимоти дастгоҳ ҳанӯз ҳам браузери веби асосёфта ба Chromium, ки Flatpak нест, лозим аст."'
    },
    'th.lib': {
        'websoftwarewarning': 'websoftwarewarning="หลังจากแพตช์นี้ ยังจำเป็นต้องใช้เว็บเบราว์เซอร์ที่ใช้ Chromium และไม่ใช่ Flatpak เพื่อจัดการการตั้งค่าอุปกรณ์"'
    },
    'tl.lib': {
        'websoftwarewarning': 'websoftwarewarning="Pagkatapos ng patch na ito, kailangan pa rin ang isang Chromium-based na web browser na hindi Flatpak upang pamahalaan ang mga setting ng device."'
    },
    'tr.lib': {
        'websoftwarewarning': 'websoftwarewarning="Bu yamadan sonra, cihaz ayarlarını yönetmek için hâlâ Flatpak olmayan Chromium tabanlı bir web tarayıcısı gereklidir."'
    },
    'uk.lib': {
        'websoftwarewarning': 'websoftwarewarning="Після застосування цього патча для керування налаштуваннями пристрою, як і раніше, потрібен веббраузер на базі Chromium, встановлений не через Flatpak."'
    },
    'ur.lib': {
        'websoftwarewarning': 'websoftwarewarning="اس پیچ کے بعد بھی ڈیوائس کی ترتیبات کا انتظام کرنے کے لیے ایک ایسا Chromium پر مبنی ویب براؤزر درکار ہے جو Flatpak نہ ہو۔"'
    },
    'uz.lib': {
        'websoftwarewarning': 'websoftwarewarning="Ushbu yamadan so‘ng ham qurilma sozlamalarini boshqarish uchun Flatpak bo‘lmagan Chromium asosidagi veb-brauzer talab qilinadi."'
    },
    'vi.lib': {
        'websoftwarewarning': 'websoftwarewarning="Sau bản vá này, vẫn cần một trình duyệt web dựa trên Chromium không phải Flatpak để quản lý cài đặt thiết bị."'
    },
    'zh.lib': {
        'websoftwarewarning': 'websoftwarewarning="应用此补丁后，仍然需要一个非 Flatpak 的 Chromium 内核网页浏览器来管理设备设置。"'
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

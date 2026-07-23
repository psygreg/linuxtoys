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
        'itbinput': 'itbinput="ibus-typing-boosterን ለመጠቀም GNOME ውስጥ ባለው የስርዓት ቅንብሮች ውስጥ ወደ የግቤት ዘዴዎችዎ ያክሉት ወይም ibus-setup ይጠቀሙ።"'
    },
    'ar.lib': {
        'itbinput': 'itbinput="لاستخدام ibus-typing-booster، أضفه إلى طرق الإدخال في إعدادات النظام في GNOME أو من خلال ibus-setup."'
    },
    'az.lib': {
        'itbinput': 'itbinput="ibus-typing-booster istifadə etmək üçün onu GNOME sistem ayarlarında giriş metodlarına əlavə edin və ya ibus-setup vasitəsilə əlavə edin."'
    },
    'bg.lib': {
        'itbinput': 'itbinput="За да използвате ibus-typing-booster, добавете го към методите за въвеждане в системните настройки на GNOME или чрез ibus-setup."'
    },
    'bn.lib': {
        'itbinput': 'itbinput="ibus-typing-booster ব্যবহার করতে, GNOME-এর সিস্টেম সেটিংসে ইনপুট পদ্ধতিতে এটি যোগ করুন অথবা ibus-setup ব্যবহার করুন।"'
    },
    'bs.lib': {
        'itbinput': 'itbinput="Da biste koristili ibus-typing-booster, dodajte ga u svoje metode unosa u sistemskim postavkama GNOME-a ili putem ibus-setup."'
    },
    'cs.lib': {
        'itbinput': 'itbinput="Chcete-li používat ibus-typing-booster, přidejte jej do metod zadávání v nastavení systému GNOME nebo pomocí ibus-setup."'
    },
    'da.lib': {
        'itbinput': 'itbinput="For at bruge ibus-typing-booster skal du tilføje det til dine inputmetoder i GNOME\'s systemindstillinger eller via ibus-setup."'
    },
    'de.lib': {
        'itbinput': 'itbinput="Um ibus-typing-booster zu verwenden, fügen Sie ihn in den Systemeinstellungen von GNOME zu Ihren Eingabemethoden hinzu oder verwenden Sie ibus-setup."'
    },
    'el.lib': {
        'itbinput': 'itbinput="Για να χρησιμοποιήσετε το ibus-typing-booster, προσθέστε το στις μεθόδους εισαγωγής στις ρυθμίσεις συστήματος του GNOME ή μέσω του ibus-setup."'
    },
    'es.lib': {
        'itbinput': 'itbinput="Para usar ibus-typing-booster, agréguelo a sus métodos de entrada en la configuración del sistema de GNOME o mediante ibus-setup."'
    },
    'et.lib': {
        'itbinput': 'itbinput="ibus-typing-boosteri kasutamiseks lisage see GNOME süsteemiseadetes sisestusmeetodite hulka või kasutage ibus-setupi."'
    },
    'fa.lib': {
        'itbinput': 'itbinput="برای استفاده از ibus-typing-booster، آن را در تنظیمات سیستم GNOME به روش‌های ورودی خود اضافه کنید یا از ibus-setup استفاده کنید."'
    },
    'fi.lib': {
        'itbinput': 'itbinput="Käyttääksesi ibus-typing-boosteria lisää se syöttötapoihin GNOMEn järjestelmäasetuksissa tai käytä ibus-setupia."'
    },
    'fr.lib': {
        'itbinput': 'itbinput="Pour utiliser ibus-typing-booster, ajoutez-le à vos méthodes de saisie dans les paramètres système de GNOME ou via ibus-setup."'
    },
    'ga.lib': {
        'itbinput': 'itbinput="Chun ibus-typing-booster a úsáid, cuir le do mhodhanna ionchuir é i socruithe córais GNOME nó trí ibus-setup."'
    },
    'he.lib': {
        'itbinput': 'itbinput="כדי להשתמש ב-ibus-typing-booster, הוסף אותו לשיטות הקלט שלך בהגדרות המערכת של GNOME או באמצעות ibus-setup."'
    },
    'hi.lib': {
        'itbinput': 'itbinput="ibus-typing-booster का उपयोग करने के लिए, इसे GNOME की सिस्टम सेटिंग्स में अपनी इनपुट विधियों में जोड़ें या ibus-setup का उपयोग करें।"'
    },
    'hr.lib': {
        'itbinput': 'itbinput="Za korištenje ibus-typing-boostera dodajte ga među metode unosa u postavkama sustava GNOME ili putem ibus-setup."'
    },
    'hu.lib': {
        'itbinput': 'itbinput="Az ibus-typing-booster használatához adja hozzá a beviteli módokhoz a GNOME rendszerbeállításaiban vagy az ibus-setup segítségével."'
    },
    'hy.lib': {
        'itbinput': 'itbinput="ibus-typing-booster-ն օգտագործելու համար այն ավելացրեք մուտքագրման մեթոդներին GNOME-ի համակարգի կարգավորումներում կամ ibus-setup-ի միջոցով։"'
    },
    'id.lib': {
        'itbinput': 'itbinput="Untuk menggunakan ibus-typing-booster, tambahkan ke metode masukan Anda di pengaturan sistem GNOME atau melalui ibus-setup."'
    },
    'is.lib': {
        'itbinput': 'itbinput="Til að nota ibus-typing-booster skaltu bæta því við innsláttaraðferðir í kerfisstillingum GNOME eða með ibus-setup."'
    },
    'it.lib': {
    'itbinput': 'itbinput="Per utilizzare ibus-typing-booster, aggiungilo ai metodi di input nelle impostazioni di sistema di GNOME oppure tramite ibus-setup."'
    },
    'ja.lib': {
        'itbinput': 'itbinput="ibus-typing-booster を使用するには、GNOME のシステム設定の入力方式に追加するか、ibus-setup を使用してください。"' 
    },
    'ka.lib': {
        'itbinput': 'itbinput="ibus-typing-booster-ის გამოსაყენებლად დაამატეთ ის შეყვანის მეთოდებში GNOME-ის სისტემურ პარამეტრებში ან გამოიყენეთ ibus-setup."'
    },
    'km.lib': {
        'itbinput': 'itbinput="ដើម្បីប្រើ ibus-typing-booster សូមបន្ថែមវាទៅវិធីសាស្ត្របញ្ចូលក្នុងការកំណត់ប្រព័ន្ធ GNOME ឬតាមរយៈ ibus-setup។"'
    },
    'ko.lib': {
        'itbinput': 'itbinput="ibus-typing-booster를 사용하려면 GNOME 시스템 설정의 입력 방식에 추가하거나 ibus-setup을 사용하십시오."'
    },
    'lo.lib': {
        'itbinput': 'itbinput="ເພື່ອໃຊ້ ibus-typing-booster ໃຫ້ເພີ່ມມັນເຂົ້າໃນວິທີປ້ອນຂໍ້ມູນໃນການຕັ້ງຄ່າລະບົບຂອງ GNOME ຫຼືຜ່ານ ibus-setup."'
    },
    'lt.lib': {
        'itbinput': 'itbinput="Norėdami naudoti ibus-typing-booster, pridėkite jį prie įvesties metodų GNOME sistemos nustatymuose arba naudokite ibus-setup."'
    },
    'lv.lib': {
        'itbinput': 'itbinput="Lai izmantotu ibus-typing-booster, pievienojiet to ievades metodēm GNOME sistēmas iestatījumos vai izmantojot ibus-setup."'
    },
    'ms.lib': {
        'itbinput': 'itbinput="Untuk menggunakan ibus-typing-booster, tambahkannya pada kaedah input dalam tetapan sistem GNOME atau melalui ibus-setup."'
    },
    'nb.lib': {
        'itbinput': 'itbinput="For å bruke ibus-typing-booster, legg det til i inndatametodene dine i GNOMEs systeminnstillinger eller via ibus-setup."'
    },
    'nl.lib': {
        'itbinput': 'itbinput="Om ibus-typing-booster te gebruiken, voegt u deze toe aan uw invoermethoden in de systeeminstellingen van GNOME of via ibus-setup."'
    },
    'pl.lib': {
        'itbinput': 'itbinput="Aby używać ibus-typing-booster, dodaj go do metod wprowadzania w ustawieniach systemowych GNOME lub za pomocą ibus-setup."'
    },
    'pt.lib': {
        'itbinput': 'itbinput="Para usar o ibus-typing-booster, adicione-o aos seus métodos de entrada nas configurações do sistema do GNOME ou através do ibus-setup."'
    },
    'ro.lib': {
        'itbinput': 'itbinput="Pentru a utiliza ibus-typing-booster, adăugați-l la metodele de introducere din setările de sistem GNOME sau prin ibus-setup."'
    },
    'ru.lib': {
        'itbinput': 'itbinput="Чтобы использовать ibus-typing-booster, добавьте его в методы ввода в настройках системы GNOME или с помощью ibus-setup."'
    },
    'sk.lib': {
        'itbinput': 'itbinput="Ak chcete používať ibus-typing-booster, pridajte ho medzi metódy vstupu v systémových nastaveniach GNOME alebo pomocou ibus-setup."'
    },
    'sl.lib': {
        'itbinput': 'itbinput="Za uporabo ibus-typing-booster ga dodajte med načine vnosa v sistemskih nastavitvah GNOME ali prek ibus-setup."'
    },
    'sq.lib': {
        'itbinput': 'itbinput="Për të përdorur ibus-typing-booster, shtojeni te metodat e hyrjes në cilësimet e sistemit të GNOME ose përmes ibus-setup."'
    },
    'sr.lib': {
        'itbinput': 'itbinput="Да бисте користили ibus-typing-booster, додајте га у методе уноса у системским подешавањима GNOME-а или путем ibus-setup."'
    },
    'sv.lib': {
        'itbinput': 'itbinput="För att använda ibus-typing-booster, lägg till det bland dina inmatningsmetoder i GNOME:s systeminställningar eller via ibus-setup."'
    },
    'sw.lib': {
        'itbinput': 'itbinput="Ili kutumia ibus-typing-booster, iongeze kwenye mbinu zako za kuingiza katika mipangilio ya mfumo ya GNOME au kupitia ibus-setup."'
    },
    'ta.lib': {
        'itbinput': 'itbinput="ibus-typing-booster-ஐ பயன்படுத்த, அதை GNOME அமைப்பின் உள்ளீட்டு முறைகளில் சேர்க்கவும் அல்லது ibus-setup மூலம் சேர்க்கவும்."'
    },
    'tg.lib': {
        'itbinput': 'itbinput="Барои истифодаи ibus-typing-booster онро ба усулҳои воридкунии худ дар танзимоти системаи GNOME ё тавассути ibus-setup илова кунед."'
    },
    'th.lib': {
        'itbinput': 'itbinput="หากต้องการใช้ ibus-typing-booster ให้เพิ่มลงในวิธีป้อนข้อมูลในตั้งค่าระบบของ GNOME หรือผ่าน ibus-setup"'
    },
    'tl.lib': {
        'itbinput': 'itbinput="Upang gamitin ang ibus-typing-booster, idagdag ito sa iyong mga paraan ng pag-input sa mga setting ng system ng GNOME o sa pamamagitan ng ibus-setup."'
    },
    'tr.lib': {
        'itbinput': 'itbinput="ibus-typing-booster kullanmak için GNOME sistem ayarlarında giriş yöntemlerinize ekleyin veya ibus-setup aracılığıyla ekleyin."'
    },
    'uk.lib': {
        'itbinput': 'itbinput="Щоб використовувати ibus-typing-booster, додайте його до методів введення в системних налаштуваннях GNOME або за допомогою ibus-setup."'
    },
    'ur.lib': {
        'itbinput': 'itbinput="ibus-typing-booster استعمال کرنے کے لیے اسے GNOME کی نظامی ترتیبات میں اپنے ان پٹ طریقوں میں شامل کریں یا ibus-setup استعمال کریں۔"'
    },
    'uz.lib': {
        'itbinput': 'itbinput="ibus-typing-booster-dan foydalanish uchun uni GNOME tizim sozlamalaridagi kiritish usullariga qo‘shing yoki ibus-setup orqali qo‘shing."'
    },
    'vi.lib': {
        'itbinput': 'itbinput="Để sử dụng ibus-typing-booster, hãy thêm nó vào các phương thức nhập trong cài đặt hệ thống của GNOME hoặc thông qua ibus-setup."'
    },
    'zh.lib': {
        'itbinput': 'itbinput="要使用 ibus-typing-booster，请在 GNOME 的系统设置中将其添加到输入法，或通过 ibus-setup 进行配置。"' 
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

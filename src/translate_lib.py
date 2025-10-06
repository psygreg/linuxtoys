#!/usr/bin/env python3
"""
Script to add translated messages to all language .lib files

INSTRUCTIONS FOR FUTURE USE:
1. Update ENGLISH_MSG with the new English message
2. Update MSG_ID with the new message ID (e.g., "msg296", "msg297", etc.)
3. Update the TRANSLATIONS dictionary with translations for all languages
4. Run: python add_translations.py
5. Verify the output and check for any errors
"""

import os

# The base directory containing language files
LANG_DIR = "../p3/libs/lang"

# The English message to translate (update this for future messages)
ENGLISH_MSG = 'msg300="Check service status"'

# Message ID to check for existence (update this for future messages)
MSG_ID = "msg300"

# Translations for the message in all supported languages (update these for future messages)
TRANSLATIONS = {
    'am.lib': 'msg300="የአገልግሎት ሁኔታ ፈትሽ"',
    'ar.lib': 'msg300="التحقق من حالة الخدمة"',
    'az.lib': 'msg300="Xidmətin statusunu yoxlayın"',
    'bg.lib': 'msg300="Проверка на състоянието на услугата"',
    'bn.lib': 'msg300="সেবা অবস্থা পরীক্ষা করুন"',
    'bs.lib': 'msg300="Provjeri status usluge"',
    'cs.lib': 'msg300="Zkontrolovat stav služby"',
    'da.lib': 'msg300="Tjek servicestatus"',
    'de.lib': 'msg300="Dienststatus überprüfen"',
    'el.lib': 'msg300="Έλεγχος κατάστασης υπηρεσίας"',
    'es.lib': 'msg300="Verificar estado del servicio"',
    'et.lib': 'msg300="Kontrolli teenuse olekut"',
    'fa.lib': 'msg300="بررسی وضعیت سرویس"',
    'fi.lib': 'msg300="Tarkista palvelun tila"',
    'fr.lib': 'msg300="Vérifier l\'état du service"',
    'ga.lib': 'msg300="Seiceáil stádas seirbhíse"',
    'he.lib': 'msg300="בדוק מצב השירות"',
    'hi.lib': 'msg300="सेवा स्थिति जांचें"',
    'hr.lib': 'msg300="Provjeri status usluge"',
    'hu.lib': 'msg300="Szolgáltatás állapotának ellenőrzése"',
    'hy.lib': 'msg300="Ստուգել ծառայության կարգավիճակը"',
    'id.lib': 'msg300="Periksa status layanan"',
    'is.lib': 'msg300="Athuga stöðu þjónustu"',
    'it.lib': 'msg300="Controlla stato del servizio"',
    'ja.lib': 'msg300="サービスステータスを確認"',
    'ka.lib': 'msg300="შეამოწმეთ სერვისის სტატუსი"',
    'km.lib': 'msg300="ពិនិត្យស្ថានភាពសេវាកម្ម"',
    'ko.lib': 'msg300="서비스 상태 확인"',
    'lo.lib': 'msg300="ກວດສອບສະຖານະການບໍລິການ"',
    'lt.lib': 'msg300="Patikrinti paslaugos būseną"',
    'lv.lib': 'msg300="Pārbaudīt pakalpojuma statusu"',
    'mn.lib': 'msg300="Үйлчилгээний төлөвийг шалгах"',
    'ms.lib': 'msg300="Semak status perkhidmatan"',
    'my.lib': 'msg300="ဝန်ဆောင်မှု အခြေအနေ စစ်ဆေးပါ"',
    'nb.lib': 'msg300="Sjekk tjenestestatus"',
    'ne.lib': 'msg300="सेवा स्थिति जाँच गर्नुहोस्"',
    'nl.lib': 'msg300="Servicestatus controleren"',
    'pl.lib': 'msg300="Sprawdź status usługi"',
    'pt.lib': 'msg300="Verificar status do serviço"',
    'ro.lib': 'msg300="Verifică starea serviciului"',
    'ru.lib': 'msg300="Проверить статус службы"',
    'sk.lib': 'msg300="Skontrolovať stav služby"',
    'sl.lib': 'msg300="Preveri stanje storitve"',
    'sq.lib': 'msg300="Kontrollo statusin e shërbimit"',
    'sr.lib': 'msg300="Провери статус услуге"',
    'sv.lib': 'msg300="Kontrollera tjänststatus"',
    'sw.lib': 'msg300="Angalia hali ya huduma"',
    'ta.lib': 'msg300="சேவை நிலையை சரிபார்க்கவும்"',
    'tg.lib': 'msg300="Холати хидматро тафтиш кунед"',
    'th.lib': 'msg300="ตรวจสอบสถานะบริการ"',
    'tl.lib': 'msg300="Suriin ang katayuan ng serbisyo"',
    'tr.lib': 'msg300="Hizmet durumunu kontrol et"',
    'uk.lib': 'msg300="Перевірити статус служби"',
    'ur.lib': 'msg300="سروس کی حیثیت چیک کریں"',
    'uz.lib': 'msg300="Xizmat holatini tekshirish"',
    'vi.lib': 'msg300="Kiểm tra trạng thái dịch vụ"',
    'zh.lib': 'msg300="检查服务状态"'
}

def add_translation_to_file(filepath, translation):
    """Add the translation to the specified .lib file"""
    try:
        # Read the current file content
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if the message already exists
        if f'{MSG_ID}=' in content:
            print(f"{MSG_ID} already exists in {filepath}, skipping...")
            return False
        
        # Add the translation at the end
        if not content.endswith('\n'):
            content += '\n'
        content += translation + '\n'
        
        # Write back to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Added translation to {filepath}")
        return True
        
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False

def main():
    """Main function to add translations to all language files"""
    processed = 0
    skipped = 0
    errors = 0
    
    print(f"Adding {MSG_ID} translations to all language files...")
    print("=" * 50)
    
    for filename, translation in TRANSLATIONS.items():
        filepath = os.path.join(LANG_DIR, filename)
        
        if os.path.exists(filepath):
            result = add_translation_to_file(filepath, translation)
            if result is True:
                processed += 1
            elif result is False:
                skipped += 1
        else:
            print(f"File not found: {filepath}")
            errors += 1
    
    print("=" * 50)
    print("Summary:")
    print(f"  Processed: {processed}")
    print(f"  Skipped (already exists): {skipped}")
    print(f"  Errors: {errors}")
    print(f"  Total files: {len(TRANSLATIONS)}")

if __name__ == "__main__":
    main()
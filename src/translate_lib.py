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
    'hwincompat': 'hwincompat="የእርስዎ ሃርድዌር ከዚህ ባህሪ ጋር ተኳሃኝ አይደለም። ክዋኔው ተሰርዟል።"'
},
'ar.lib': {
    'hwincompat': 'hwincompat="جهازك غير متوافق مع هذه الميزة. تم إلغاء العملية."'
},
'az.lib': {
    'hwincompat': 'hwincompat="Avadanlığınız bu funksiya ilə uyğun deyil. Əməliyyat ləğv edildi."'
},
'bg.lib': {
    'hwincompat': 'hwincompat="Вашият хардуер не е съвместим с тази функция. Операцията е отменена."'
},
'bn.lib': {
    'hwincompat': 'hwincompat="আপনার হার্ডওয়্যার এই বৈশিষ্ট্যের সঙ্গে সামঞ্জস্যপূর্ণ নয়। কার্যক্রম বাতিল করা হয়েছে।"'
},
'bs.lib': {
    'hwincompat': 'hwincompat="Vaš hardver nije kompatibilan s ovom funkcijom. Operacija je otkazana."'
},
'cs.lib': {
    'hwincompat': 'hwincompat="Váš hardware není s touto funkcí kompatibilní. Operace byla zrušena."'
},
'da.lib': {
    'hwincompat': 'hwincompat="Din hardware er ikke kompatibel med denne funktion. Handlingen blev annulleret."'
},
'de.lib': {
    'hwincompat': 'hwincompat="Ihre Hardware ist mit dieser Funktion nicht kompatibel. Der Vorgang wurde abgebrochen."'
},
'el.lib': {
    'hwincompat': 'hwincompat="Το υλικό σας δεν είναι συμβατό με αυτήν τη λειτουργία. Η διαδικασία ακυρώθηκε."'
},
'es.lib': {
    'hwincompat': 'hwincompat="Su hardware no es compatible con esta función. Operación cancelada."'
},
'et.lib': {
    'hwincompat': 'hwincompat="Teie riistvara ei ühildu selle funktsiooniga. Toiming tühistati."'
},
'fa.lib': {
    'hwincompat': 'hwincompat="سخت‌افزار شما با این قابلیت سازگار نیست. عملیات لغو شد."'
},
'fi.lib': {
    'hwincompat': 'hwincompat="Laitteistosi ei ole yhteensopiva tämän ominaisuuden kanssa. Toiminto peruutettiin."'
},
'fr.lib': {
    'hwincompat': 'hwincompat="Votre matériel n’est pas compatible avec cette fonctionnalité. Opération annulée."'
},
'ga.lib': {
    'hwincompat': 'hwincompat="Níl do chrua-earraí comhoiriúnach leis an ngné seo. Cuireadh an oibríocht ar ceal."'
},
'he.lib': {
    'hwincompat': 'hwincompat="החומרה שלך אינה תואמת לתכונה זו. הפעולה בוטלה."'
},
'hi.lib': {
    'hwincompat': 'hwincompat="आपका हार्डवेयर इस सुविधा के अनुकूल नहीं है। कार्रवाई रद्द कर दी गई।"'
},
'hr.lib': {
    'hwincompat': 'hwincompat="Vaš hardver nije kompatibilan s ovom značajkom. Radnja je otkazana."'
},
'hu.lib': {
    'hwincompat': 'hwincompat="A hardvere nem kompatibilis ezzel a funkcióval. A művelet megszakítva."'
},
'hy.lib': {
    'hwincompat': 'hwincompat="Ձեր սարքավորումը համատեղելի չէ այս գործառույթի հետ։ Գործողությունը չեղարկվեց։"'
},
'id.lib': {
    'hwincompat': 'hwincompat="Perangkat keras Anda tidak kompatibel dengan fitur ini. Operasi dibatalkan."'
},
'is.lib': {
    'hwincompat': 'hwincompat="Vélbúnaðurinn þinn er ekki samhæfur þessum eiginleika. Aðgerð hætt við."'
},
'it.lib': {
    'hwincompat': 'hwincompat="Il tuo hardware non è compatibile con questa funzionalità. Operazione annullata."'
},
'ja.lib': {
    'hwincompat': 'hwincompat="お使いのハードウェアはこの機能に対応していません。操作をキャンセルしました。"'
},
'ka.lib': {
    'hwincompat': 'hwincompat="თქვენი აპარატურა ამ ფუნქციასთან თავსებადი არ არის. ოპერაცია გაუქმდა."'
},
'km.lib': {
    'hwincompat': 'hwincompat="ផ្នែករឹងរបស់អ្នកមិនត្រូវគ្នាជាមួយមុខងារនេះទេ។ ប្រតិបត្តិការត្រូវបានបោះបង់។"'
},
'ko.lib': {
    'hwincompat': 'hwincompat="하드웨어가 이 기능과 호환되지 않습니다. 작업이 취소되었습니다."'
},
'lo.lib': {
    'hwincompat': 'hwincompat="ຮາດແວຂອງທ່ານບໍ່ຮອງຮັບຄຸນສົມບັດນີ້. ການດຳເນີນງານຖືກຍົກເລີກ."'
},
'lt.lib': {
    'hwincompat': 'hwincompat="Jūsų aparatinė įranga nesuderinama su šia funkcija. Veiksmas atšauktas."'
},
'lv.lib': {
    'hwincompat': 'hwincompat="Jūsu aparatūra nav saderīga ar šo funkciju. Darbība atcelta."'
},
'mn.lib': {
    'hwincompat': 'hwincompat="Таны техник хангамж энэ боломжтой нийцэхгүй байна. Үйлдлийг цуцаллаа."'
},
'ms.lib': {
    'hwincompat': 'hwincompat="Perkakasan anda tidak serasi dengan ciri ini. Operasi dibatalkan."'
},
'my.lib': {
    'hwincompat': 'hwincompat="သင့်ဟာ့ဒ်ဝဲသည် ဤအင်္ဂါရပ်နှင့် ကိုက်ညီမှုမရှိပါ။ လုပ်ဆောင်ချက်ကို ပယ်ဖျက်လိုက်သည်။"'
},
'nb.lib': {
    'hwincompat': 'hwincompat="Maskinvaren din er ikke kompatibel med denne funksjonen. Handlingen ble avbrutt."'
},
'ne.lib': {
    'hwincompat': 'hwincompat="तपाईंको हार्डवेयर यो सुविधासँग उपयुक्त छैन। कार्य रद्द गरियो।"'
},
'nl.lib': {
    'hwincompat': 'hwincompat="Uw hardware is niet compatibel met deze functie. De bewerking is geannuleerd."'
},
'pl.lib': {
    'hwincompat': 'hwincompat="Twój sprzęt nie jest zgodny z tą funkcją. Operacja została anulowana."'
},
'pt.lib': {
    'hwincompat': 'hwincompat="Seu hardware não é compatível com este recurso. Operação cancelada."'
},
'ro.lib': {
    'hwincompat': 'hwincompat="Hardware-ul dumneavoastră nu este compatibil cu această funcție. Operațiunea a fost anulată."'
},
'ru.lib': {
    'hwincompat': 'hwincompat="Ваше оборудование несовместимо с этой функцией. Операция отменена."'
},
'sk.lib': {
    'hwincompat': 'hwincompat="Váš hardvér nie je kompatibilný s touto funkciou. Operácia bola zrušená."'
},
'sl.lib': {
    'hwincompat': 'hwincompat="Vaša strojna oprema ni združljiva s to funkcijo. Postopek je bil preklican."'
},
'sq.lib': {
    'hwincompat': 'hwincompat="Pajisja juaj nuk është e përputhshme me këtë veçori. Veprimi u anulua."'
},
'sr.lib': {
    'hwincompat': 'hwincompat="Ваш хардвер није компатибилан са овом функцијом. Операција је отказана."'
},
'sv.lib': {
    'hwincompat': 'hwincompat="Din maskinvara är inte kompatibel med den här funktionen. Åtgärden avbröts."'
},
'sw.lib': {
    'hwincompat': 'hwincompat="Maunzi yako hayaoani na kipengele hiki. Operesheni imeghairiwa."'
},
'ta.lib': {
    'hwincompat': 'hwincompat="உங்கள் வன்பொருள் இந்த அம்சத்துடன் இணக்கமாக இல்லை. செயல்பாடு ரத்துசெய்யப்பட்டது."'
},
'tg.lib': {
    'hwincompat': 'hwincompat="Сахтафзори шумо бо ин хусусият мувофиқ нест. Амалиёт бекор карда шуд."'
},
'th.lib': {
    'hwincompat': 'hwincompat="ฮาร์ดแวร์ของคุณไม่รองรับคุณสมบัตินี้ ยกเลิกการดำเนินการแล้ว"'
},
'tl.lib': {
    'hwincompat': 'hwincompat="Hindi tugma ang iyong hardware sa feature na ito. Kinansela ang operasyon."'
},
'tr.lib': {
    'hwincompat': 'hwincompat="Donanımınız bu özellikle uyumlu değil. İşlem iptal edildi."'
},
'uk.lib': {
    'hwincompat': 'hwincompat="Ваше обладнання несумісне з цією функцією. Операцію скасовано."'
},
'ur.lib': {
    'hwincompat': 'hwincompat="آپ کا ہارڈویئر اس خصوصیت کے ساتھ مطابقت نہیں رکھتا۔ کارروائی منسوخ کر دی گئی۔"'
},
'uz.lib': {
    'hwincompat': 'hwincompat="Qurilmangiz ushbu imkoniyat bilan mos emas. Amal bekor qilindi."'
},
'vi.lib': {
    'hwincompat': 'hwincompat="Phần cứng của bạn không tương thích với tính năng này. Thao tác đã bị hủy."'
},
'zh.lib': {
    'hwincompat': 'hwincompat="您的硬件与此功能不兼容。操作已取消。"'
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

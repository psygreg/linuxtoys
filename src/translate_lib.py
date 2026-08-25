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
    'requirerebar': 'requirerebar="\\"Resize BAR\\" እና \\"Above 4G Decoding\\" የAMD GPU ነጂዎችን ለመጫን ያስፈልጋሉ። እባክዎ እነዚህን በBIOS ውስጥ ያንቁ እና እንደገና ይሞክሩ።"'
},
'ar.lib': {
    'requirerebar': 'requirerebar="\\"Resize BAR\\" و\\"Above 4G Decoding\\" مطلوبان لتثبيت برامج تشغيل AMD GPU. يرجى تمكينهما في BIOS ثم المحاولة مرة أخرى."'
},
'az.lib': {
    'requirerebar': 'requirerebar="\\"Resize BAR\\" və \\"Above 4G Decoding\\" AMD GPU sürücülərini quraşdırmaq üçün tələb olunur. Zəhmət olmasa onları BIOS-da aktivləşdirin və yenidən cəhd edin."'
},
'bg.lib': {
    'requirerebar': 'requirerebar="\\"Resize BAR\\" и \\"Above 4G Decoding\\" са необходими за инсталиране на драйверите за AMD GPU. Моля, активирайте ги в BIOS и опитайте отново."'
},
'bn.lib': {
    'requirerebar': 'requirerebar="AMD GPU ড্রাইভার ইনস্টল করতে \\"Resize BAR\\" এবং \\"Above 4G Decoding\\" প্রয়োজন। অনুগ্রহ করে BIOS-এ এগুলো সক্রিয় করুন এবং আবার চেষ্টা করুন।"'
},
'bs.lib': {
    'requirerebar': 'requirerebar="\\"Resize BAR\\" i \\"Above 4G Decoding\\" su potrebni za instalaciju AMD GPU upravljačkih programa. Omogućite ih u BIOS-u i pokušajte ponovo."'
},
'cs.lib': {
    'requirerebar': 'requirerebar="Pro instalaci ovladačů AMD GPU jsou vyžadovány \\"Resize BAR\\" a \\"Above 4G Decoding\\". Povolte je v BIOSu a zkuste to znovu."'
},
'da.lib': {
    'requirerebar': 'requirerebar="\\"Resize BAR\\" og \\"Above 4G Decoding\\" er påkrævet for at installere AMD GPU-drivere. Aktivér dem i BIOS, og prøv igen."'
},
'de.lib': {
    'requirerebar': 'requirerebar="\\"Resize BAR\\" und \\"Above 4G Decoding\\" sind erforderlich, um AMD-GPU-Treiber zu installieren. Bitte aktivieren Sie beide Optionen im BIOS und versuchen Sie es erneut."'
},
'el.lib': {
    'requirerebar': 'requirerebar="Τα \\"Resize BAR\\" και \\"Above 4G Decoding\\" απαιτούνται για την εγκατάσταση προγραμμάτων οδήγησης AMD GPU. Ενεργοποιήστε τα στο BIOS και δοκιμάστε ξανά."'
},
'es.lib': {
    'requirerebar': 'requirerebar="\\"Resize BAR\\" y \\"Above 4G Decoding\\" son necesarios para instalar los controladores de GPU AMD. Habilítelos en la BIOS e inténtelo de nuevo."'
},
'et.lib': {
    'requirerebar': 'requirerebar="\\"Resize BAR\\" ja \\"Above 4G Decoding\\" on AMD GPU draiverite installimiseks vajalikud. Lubage need BIOS-is ja proovige uuesti."'
},
'fa.lib': {
    'requirerebar': 'requirerebar="برای نصب درایورهای AMD GPU، گزینه‌های \\"Resize BAR\\" و \\"Above 4G Decoding\\" لازم هستند. لطفاً آن‌ها را در BIOS فعال کرده و دوباره تلاش کنید."'
},
'fi.lib': {
    'requirerebar': 'requirerebar="\\"Resize BAR\\" ja \\"Above 4G Decoding\\" vaaditaan AMD GPU -ajureiden asentamiseen. Ota ne käyttöön BIOSissa ja yritä uudelleen."'
},
'fr.lib': {
    'requirerebar': 'requirerebar="\\"Resize BAR\\" et \\"Above 4G Decoding\\" sont requis pour installer les pilotes GPU AMD. Veuillez les activer dans le BIOS et réessayer."'
},
'ga.lib': {
    'requirerebar': 'requirerebar="Tá \\"Resize BAR\\" agus \\"Above 4G Decoding\\" riachtanach chun tiománaithe AMD GPU a shuiteáil. Cumasaigh iad sa BIOS agus bain triail eile as."'
},
'he.lib': {
    'requirerebar': 'requirerebar="יש צורך ב-\\"Resize BAR\\" וב-\\"Above 4G Decoding\\" כדי להתקין מנהלי התקנים של AMD GPU. יש להפעיל אותם ב-BIOS ולנסות שוב."'
},
'hi.lib': {
    'requirerebar': 'requirerebar="AMD GPU ड्राइवर इंस्टॉल करने के लिए \\"Resize BAR\\" और \\"Above 4G Decoding\\" आवश्यक हैं। कृपया इन्हें BIOS में सक्षम करें और फिर से प्रयास करें।"'
},
'hr.lib': {
    'requirerebar': 'requirerebar="\\"Resize BAR\\" i \\"Above 4G Decoding\\" potrebni su za instalaciju AMD GPU upravljačkih programa. Omogućite ih u BIOS-u i pokušajte ponovno."'
},
'hu.lib': {
    'requirerebar': 'requirerebar="Az AMD GPU-illesztőprogramok telepítéséhez szükséges a \\"Resize BAR\\" és az \\"Above 4G Decoding\\". Engedélyezze ezeket a BIOS-ban, majd próbálja újra."'
},
'hy.lib': {
    'requirerebar': 'requirerebar="AMD GPU-ի դրայվերները տեղադրելու համար անհրաժեշտ են \\"Resize BAR\\" և \\"Above 4G Decoding\\" տարբերակները։ Միացրեք դրանք BIOS-ում և կրկին փորձեք։"'
},
'id.lib': {
    'requirerebar': 'requirerebar="\\"Resize BAR\\" dan \\"Above 4G Decoding\\" diperlukan untuk memasang driver GPU AMD. Aktifkan keduanya di BIOS lalu coba lagi."'
},
'is.lib': {
    'requirerebar': 'requirerebar="\\"Resize BAR\\" og \\"Above 4G Decoding\\" eru nauðsynleg til að setja upp AMD GPU-rekla. Virkjaðu þau í BIOS og reyndu aftur."'
},
'it.lib': {
    'requirerebar': 'requirerebar="\\"Resize BAR\\" e \\"Above 4G Decoding\\" sono necessari per installare i driver GPU AMD. Abilitali nel BIOS e riprova."'
},
'ja.lib': {
    'requirerebar': 'requirerebar="AMD GPU ドライバーをインストールするには、\\"Resize BAR\\" と \\"Above 4G Decoding\\" が必要です。BIOS でこれらを有効にして、もう一度お試しください。"'
},
'ka.lib': {
    'requirerebar': 'requirerebar="AMD GPU-ის დრაივერების დასაყენებლად საჭიროა \\"Resize BAR\\" და \\"Above 4G Decoding\\". ჩართეთ ისინი BIOS-ში და სცადეთ ხელახლა."'
},
'km.lib': {
    'requirerebar': 'requirerebar="ត្រូវការ \\"Resize BAR\\" និង \\"Above 4G Decoding\\" ដើម្បីដំឡើងកម្មវិធីបញ្ជា AMD GPU។ សូមបើកពួកវានៅក្នុង BIOS ហើយសាកល្បងម្តងទៀត។"'
},
'ko.lib': {
    'requirerebar': 'requirerebar="AMD GPU 드라이버를 설치하려면 \\"Resize BAR\\" 및 \\"Above 4G Decoding\\"이 필요합니다. BIOS에서 해당 옵션을 활성화한 후 다시 시도하십시오."'
},
'lo.lib': {
    'requirerebar': 'requirerebar="ຈຳເປັນຕ້ອງເປີດ \\"Resize BAR\\" ແລະ \\"Above 4G Decoding\\" ເພື່ອຕິດຕັ້ງໄດຣເວີ AMD GPU. ກະລຸນາເປີດໃຊ້ງານພວກມັນໃນ BIOS ແລ້ວລອງໃໝ່."'
},
'lt.lib': {
    'requirerebar': 'requirerebar="Norint įdiegti AMD GPU tvarkykles, reikalingi \\"Resize BAR\\" ir \\"Above 4G Decoding\\". Įjunkite juos BIOS ir bandykite dar kartą."'
},
'lv.lib': {
    'requirerebar': 'requirerebar="Lai instalētu AMD GPU draiverus, ir nepieciešami \\"Resize BAR\\" un \\"Above 4G Decoding\\". Iespējojiet tos BIOS un mēģiniet vēlreiz."'
},
'mn.lib': {
    'requirerebar': 'requirerebar="AMD GPU драйвер суулгахын тулд \\"Resize BAR\\" болон \\"Above 4G Decoding\\" шаардлагатай. Эдгээрийг BIOS-д идэвхжүүлээд дахин оролдоно уу."'
},
'ms.lib': {
    'requirerebar': 'requirerebar="\\"Resize BAR\\" dan \\"Above 4G Decoding\\" diperlukan untuk memasang pemacu AMD GPU. Sila dayakannya dalam BIOS dan cuba lagi."'
},
'my.lib': {
    'requirerebar': 'requirerebar="AMD GPU ဒရိုင်ဘာများ ထည့်သွင်းရန် \\"Resize BAR\\" နှင့် \\"Above 4G Decoding\\" လိုအပ်ပါသည်။ ၎င်းတို့ကို BIOS တွင် ဖွင့်ပြီး ထပ်မံကြိုးစားပါ။"'
},
'nb.lib': {
    'requirerebar': 'requirerebar="\\"Resize BAR\\" og \\"Above 4G Decoding\\" kreves for å installere AMD GPU-drivere. Aktiver dem i BIOS og prøv igjen."'
},
'ne.lib': {
    'requirerebar': 'requirerebar="AMD GPU ड्राइभर स्थापना गर्न \\"Resize BAR\\" र \\"Above 4G Decoding\\" आवश्यक छन्। कृपया तिनीहरूलाई BIOS मा सक्षम गर्नुहोस् र फेरि प्रयास गर्नुहोस्।"'
},
'nl.lib': {
    'requirerebar': 'requirerebar="\\"Resize BAR\\" en \\"Above 4G Decoding\\" zijn vereist om AMD GPU-stuurprogramma’s te installeren. Schakel deze opties in het BIOS in en probeer het opnieuw."'
},
'pl.lib': {
    'requirerebar': 'requirerebar="\\"Resize BAR\\" i \\"Above 4G Decoding\\" są wymagane do zainstalowania sterowników GPU AMD. Włącz je w BIOS-ie i spróbuj ponownie."'
},
'pt.lib': {
    'requirerebar': 'requirerebar="\\"Resize BAR\\" e \\"Above 4G Decoding\\" são necessários para instalar os drivers de GPU da AMD. Ative essas opções na BIOS e tente novamente."'
},
'ro.lib': {
    'requirerebar': 'requirerebar="\\"Resize BAR\\" și \\"Above 4G Decoding\\" sunt necesare pentru instalarea driverelor GPU AMD. Activați-le în BIOS și încercați din nou."'
},
'ru.lib': {
    'requirerebar': 'requirerebar="\\"Resize BAR\\" и \\"Above 4G Decoding\\" необходимы для установки драйверов AMD GPU. Включите эти параметры в BIOS и повторите попытку."'
},
'sk.lib': {
    'requirerebar': 'requirerebar="Na inštaláciu ovládačov AMD GPU sú potrebné \\"Resize BAR\\" a \\"Above 4G Decoding\\". Povoľte ich v systéme BIOS a skúste to znova."'
},
'sl.lib': {
    'requirerebar': 'requirerebar="Za namestitev gonilnikov AMD GPU sta potrebna \\"Resize BAR\\" in \\"Above 4G Decoding\\". Omogočite ju v BIOS-u in poskusite znova."'
},
'sq.lib': {
    'requirerebar': 'requirerebar="\\"Resize BAR\\" dhe \\"Above 4G Decoding\\" kërkohen për të instaluar drejtuesit e AMD GPU. Aktivizojini në BIOS dhe provoni përsëri."'
},
'sr.lib': {
    'requirerebar': 'requirerebar="\\"Resize BAR\\" и \\"Above 4G Decoding\\" су неопходни за инсталацију AMD GPU драјвера. Омогућите их у BIOS-у и покушајте поново."'
},
'sv.lib': {
    'requirerebar': 'requirerebar="\\"Resize BAR\\" och \\"Above 4G Decoding\\" krävs för att installera AMD GPU-drivrutiner. Aktivera dem i BIOS och försök igen."'
},
'sw.lib': {
    'requirerebar': 'requirerebar="\\"Resize BAR\\" na \\"Above 4G Decoding\\" zinahitajika ili kusakinisha viendeshaji vya AMD GPU. Viwashe kwenye BIOS kisha ujaribu tena."'
},
'ta.lib': {
    'requirerebar': 'requirerebar="AMD GPU இயக்கிகளை நிறுவ \\"Resize BAR\\" மற்றும் \\"Above 4G Decoding\\" தேவை. அவற்றை BIOS-இல் இயக்கி மீண்டும் முயற்சிக்கவும்."'
},
'tg.lib': {
    'requirerebar': 'requirerebar="Барои насб кардани драйверҳои AMD GPU, \\"Resize BAR\\" ва \\"Above 4G Decoding\\" лозиманд. Онҳоро дар BIOS фаъол кунед ва дубора кӯшиш кунед."'
},
'th.lib': {
    'requirerebar': 'requirerebar="จำเป็นต้องเปิดใช้ \\"Resize BAR\\" และ \\"Above 4G Decoding\\" เพื่อติดตั้งไดรเวอร์ AMD GPU โปรดเปิดใช้ตัวเลือกเหล่านี้ใน BIOS แล้วลองอีกครั้ง"'
},
'tl.lib': {
    'requirerebar': 'requirerebar="Kinakailangan ang \\"Resize BAR\\" at \\"Above 4G Decoding\\" upang mai-install ang mga driver ng AMD GPU. Paganahin ang mga ito sa BIOS at subukang muli."'
},
'tr.lib': {
    'requirerebar': 'requirerebar="AMD GPU sürücülerini yüklemek için \\"Resize BAR\\" ve \\"Above 4G Decoding\\" gereklidir. Bunları BIOS üzerinden etkinleştirip tekrar deneyin."'
},
'uk.lib': {
    'requirerebar': 'requirerebar="\\"Resize BAR\\" і \\"Above 4G Decoding\\" необхідні для встановлення драйверів AMD GPU. Увімкніть ці параметри в BIOS і повторіть спробу."'
},
'ur.lib': {
    'requirerebar': 'requirerebar="AMD GPU ڈرائیور انسٹال کرنے کے لیے \\"Resize BAR\\" اور \\"Above 4G Decoding\\" ضروری ہیں۔ براہ کرم انہیں BIOS میں فعال کریں اور دوبارہ کوشش کریں۔"'
},
'uz.lib': {
    'requirerebar': 'requirerebar="AMD GPU drayverlarini o‘rnatish uchun \\"Resize BAR\\" va \\"Above 4G Decoding\\" talab qilinadi. Ularni BIOS’da yoqing va qayta urinib ko‘ring."'
},
'vi.lib': {
    'requirerebar': 'requirerebar="Cần bật \\"Resize BAR\\" và \\"Above 4G Decoding\\" để cài đặt trình điều khiển GPU AMD. Hãy bật các tùy chọn này trong BIOS rồi thử lại."'
},
'zh.lib': {
    'requirerebar': 'requirerebar="安装 AMD GPU 驱动程序需要启用 \\"Resize BAR\\" 和 \\"Above 4G Decoding\\"。请在 BIOS 中启用这些选项，然后重试。"'
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

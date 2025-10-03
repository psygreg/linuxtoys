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
LANG_DIR = "p3/libs/lang"

# The English message to translate (update this for future messages)
ENGLISH_MSG = 'msg295="There are no tangible benefits using gamemode in systems with CPU ondemand scaling already applied. Proceed anyway?"'

# Message ID to check for existence (update this for future messages)
MSG_ID = "msg295"

# Translations for the message in all supported languages (update these for future messages)
TRANSLATIONS = {
    'am.lib': 'msg295="በ CPU ondemand scaling ባሉ ስርዓቶች ላይ gamemode መጠቀም ምንም ተጨባጭ ጥቅሞች የሉም። ወደ ፊት ይቀጥሉ?"',
    'ar.lib': 'msg295="لا توجد فوائد ملموسة من استخدام gamemode في الأنظمة التي تطبق بالفعل CPU ondemand scaling. المتابعة على أي حال؟"',
    'az.lib': 'msg295="CPU ondemand scaling tətbiq edilmiş sistemlərdə gamemode istifadəsinin heç bir əhəmiyyətli faydası yoxdur. Hər halda davam etmək?"',
    'bg.lib': 'msg295="Няма осезаеми ползи от използването на gamemode в системи с вече приложено CPU ondemand scaling. Да продължим ли въпреки това?"',
    'bn.lib': 'msg295="CPU ondemand scaling ইতিমধ্যে প্রয়োগ করা সিস্টেমে gamemode ব্যবহার করার কোন বাস্তব সুবিধা নেই। তারপরও এগিয়ে যাবেন?"',
    'bs.lib': 'msg295="Nema opipljivih koristi korišćenja gamemode na sistemima sa već primenjenim CPU ondemand scaling. Ipak nastaviti?"',
    'cs.lib': 'msg295="Neexistují žádné hmatatelné výhody použití gamemode v systémech s již aplikovaným CPU ondemand scaling. Přesto pokračovat?"',
    'da.lib': 'msg295="Der er ingen mærkbare fordele ved at bruge gamemode i systemer med CPU ondemand scaling allerede anvendt. Fortsæt alligevel?"',
    'de.lib': 'msg295="Es gibt keine greifbaren Vorteile bei der Verwendung von gamemode in Systemen mit bereits angewendetem CPU ondemand scaling. Trotzdem fortfahren?"',
    'el.lib': 'msg295="Δεν υπάρχουν απτά οφέλη από τη χρήση gamemode σε συστήματα με ήδη εφαρμοσμένο CPU ondemand scaling. Να συνεχίσετε ούτως ή άλλως;"',
    'es.lib': 'msg295="No hay beneficios tangibles usando gamemode en sistemas con CPU ondemand scaling ya aplicado. ¿Proceder de todos modos?"',
    'et.lib': 'msg295="Gamemode kasutamisel süsteemides, kus CPU ondemand scaling on juba rakendatud, ei ole käegakatsutavaid eeliseid. Kas jätkata ikkagi?"',
    'fa.lib': 'msg295="هیچ مزیت قابل لمسی در استفاده از gamemode در سیستم‌هایی که از قبل CPU ondemand scaling اعمال شده دارند، وجود ندارد. به هر حال ادامه دهید؟"',
    'fi.lib': 'msg295="Gamemode:n käytöstä ei ole konkreettisia hyötyjä järjestelmissä, joissa CPU ondemand scaling on jo käytössä. Jatketaanko silti?"',
    'fr.lib': 'msg295="Il n\'y a aucun avantage tangible à utiliser gamemode sur les systèmes avec CPU ondemand scaling déjà appliqué. Continuer quand même ?"',
    'ga.lib': 'msg295="Níl aon tairbhí inláimhsithe ag baint úsáide as gamemode i gcórais le CPU ondemand scaling curtha i bhfeidhm cheana. Lean ar aghaidh ar aon nós?"',
    'he.lib': 'msg295="אין יתרונות מוחשיים בשימוש ב-gamemode במערכות עם CPU ondemand scaling שכבר מיושם. להמשיך בכל זאת?"',
    'hi.lib': 'msg295="CPU ondemand scaling पहले से लागू वाले सिस्टम में gamemode का उपयोग करने के कोई ठोस फायदे नहीं हैं। फिर भी आगे बढ़ें?"',
    'hr.lib': 'msg295="Nema opipljivih koristi korišţenja gamemode na sustavima s već primijenjenim CPU ondemand scaling. Ipak nastaviti?"',
    'hu.lib': 'msg295="Nincs kézzelfogható előnye a gamemode használatának olyan rendszereken, ahol már alkalmazva van a CPU ondemand scaling. Mégis folytatja?"',
    'hy.lib': 'msg295="Gamemode-ը օգտագործելու ակնհայտ օգուտներ չկան այն համակարգերում, որտեղ արդեն կիրառված է CPU ondemand scaling: Այնուամենայնիվ շարունակե՞լ:"',
    'id.lib': 'msg295="Tidak ada manfaat nyata menggunakan gamemode pada sistem dengan CPU ondemand scaling yang sudah diterapkan. Tetap lanjutkan?"',
    'is.lib': 'msg295="Það eru engir áþreifanlegir kostir við að nota gamemode í kerfum með CPU ondemand scaling þegar beitt. Halda samt áfram?"',
    'it.lib': 'msg295="Non ci sono vantaggi tangibili nell\'usare gamemode su sistemi con CPU ondemand scaling già applicato. Procedere comunque?"',
    'ja.lib': 'msg295="CPU ondemand scaling が既に適用されているシステムでは、gamemode を使用することに具体的な利点はありません。それでも続行しますか？"',
    'ka.lib': 'msg295="არ არის რეალური სარგებელი gamemode-ის გამოყენებისა სისტემებში, სადაც უკვე გამოყენებულია CPU ondemand scaling. მაინც გაგრძელება?"',
    'km.lib': 'msg295="មិនមានអត្ថប្រយោជន៍ជាក់ស្តែងក្នុងការប្រើ gamemode នៅក្នុងប្រព័ន្ធដែលមាន CPU ondemand scaling ត្រូវបានអនុវត្តរួចហើយ។ បន្តទោះយ៉ាងណា?"',
    'ko.lib': 'msg295="CPU ondemand scaling이 이미 적용된 시스템에서 gamemode를 사용하는 것에는 실질적인 이점이 없습니다. 그래도 계속하시겠습니까?"',
    'lo.lib': 'msg295="ບໍ່ມີຜົນປະໂຫຍດທີ່ແທ້ຈິງໃນການໃຊ້ gamemode ໃນລະບົບທີ່ມີ CPU ondemand scaling ໄດ້ຖືກນຳໃຊ້ແລ້ວ. ດຳເນີນຕໍ່ໄປບໍ?"',
    'lt.lib': 'msg295="Nėra jokių apčiuopiamų naudos gamemode naudojimo sistemose su jau taikoma CPU ondemand scaling. Vis tiek tęsti?"',
    'lv.lib': 'msg295="Nav nekādu taustāmu ieguvumu, lietojot gamemode sistēmās ar jau pielietotu CPU ondemand scaling. Tomēr turpināt?"',
    'mn.lib': 'msg295="CPU ondemand scaling аль хэдийн хэрэгжүүлсэн системд gamemode ашиглахад бодитой ашиг тус байхгүй. Ямар ч байсан үргэлжлүүлэх үү?"',
    'ms.lib': 'msg295="Tiada faedah ketara menggunakan gamemode dalam sistem dengan CPU ondemand scaling sudah digunakan. Teruskan juga?"',
    'my.lib': 'msg295="CPU ondemand scaling ကို ပြီးသားအသုံးပြုထားသော စနစ်များတွင် gamemode ကိုအသုံးပြုခြင်း၏ တိကျသောအကျိုးကျေးဇူးများမရှိပါ။ မည်သို့ပင်ဖြစ်စေ ဆက်လက်လုပ်ဆောင်မလား?"',
    'nb.lib': 'msg295="Det er ingen håndgripelige fordeler ved å bruke gamemode i systemer med CPU ondemand scaling allerede anvendt. Fortsett likevel?"',
    'ne.lib': 'msg295="CPU ondemand scaling पहिले नै लागू भएका प्रणालीहरूमा gamemode प्रयोग गर्दा कुनै ठोस फाइदाहरू छैनन्। जे भए पनि अगाडि बढ्ने?"',
    'nl.lib': 'msg295="Er zijn geen tastbare voordelen bij het gebruik van gamemode op systemen waar CPU ondemand scaling al is toegepast. Toch doorgaan?"',
    'pl.lib': 'msg295="Nie ma żadnych wymiernych korzyści z używania gamemode w systemach z już zastosowanym CPU ondemand scaling. Kontynuować mimo wszystko?"',
    'pt.lib': 'msg295="Não há benefícios tangíveis ao usar gamemode em sistemas com CPU ondemand scaling já aplicado. Prosseguir mesmo assim?"',
    'ro.lib': 'msg295="Nu există beneficii tangibile în utilizarea gamemode pe sisteme cu CPU ondemand scaling deja aplicat. Să continuați oricum?"',
    'ru.lib': 'msg295="Нет ощутимых преимуществ в использовании gamemode в системах с уже применённым CPU ondemand scaling. Всё равно продолжить?"',
    'sk.lib': 'msg295="Neexistujú žiadne hmatateľné výhody používania gamemode v systémech s už aplikovaným CPU ondemand scaling. Napriek tomu pokračovať?"',
    'sl.lib': 'msg295="Ni oprijemljivih koristi pri uporabi gamemode v sistemih z že uporabljenim CPU ondemand scaling. Vseeno nadaljevati?"',
    'sq.lib': 'msg295="Nuk ka përfitime të prekshme duke përdorur gamemode në sistemet me CPU ondemand scaling të aplikuar tashmë. Të vazhdohet gjithsesi?"',
    'sr.lib': 'msg295="Нема опипљивих користи коришћења gamemode на системима са већ примењеним CPU ondemand scaling. Ипак наставити?"',
    'sv.lib': 'msg295="Det finns inga påtagliga fördelar med att använda gamemode i system med CPU ondemand scaling redan tillämpat. Fortsätt ändå?"',
    'sw.lib': 'msg295="Hakuna faida za kushikika za kutumia gamemode katika mifumo yenye CPU ondemand scaling tayari imetumika. Endelea hata hivyo?"',
    'ta.lib': 'msg295="CPU ondemand scaling ஏற்கனவே பயன்படுத்தப்பட்ட அமைப்புகளில் gamemode ஐ பயன்படுத்துவதில் உண்மையான நன்மைகள் எதுவும் இல்லை. எப்படியும் தொடரவா?"',
    'tg.lib': 'msg295="Дар системаҳое, ки CPU ondemand scaling аллакай татбиқ шудааст, ҳеҷ манфиати ламсшаванда аз истифодаи gamemode нест. Бо ҳар ҳол идома диҳед?"',
    'th.lib': 'msg295="ไม่มีประโยชน์ที่จับต้องได้จากการใช้ gamemode ในระบบที่มี CPU ondemand scaling ใช้งานอยู่แล้ว ดำเนินการต่อหรือไม่?"',
    'tl.lib': 'msg295="Walang makikitang benepisyo sa paggamit ng gamemode sa mga sistema na may CPU ondemand scaling na naisakatuparan na. Magpatuloy pa rin?"',
    'tr.lib': 'msg295="CPU ondemand scaling zaten uygulanmış sistemlerde gamemode kullanmanın somut faydaları yoktur. Yine de devam edilsin mi?"',
    'uk.lib': 'msg295="Немає відчутних переваг використання gamemode в системах з уже застосованим CPU ondemand scaling. Все одно продовжити?"',
    'ur.lib': 'msg295="CPU ondemand scaling پہلے سے لاگو شدہ سسٹمز میں gamemode استعمال کرنے کے کوئی ٹھوس فوائد نہیں ہیں۔ پھر بھی آگے بڑھیں؟"',
    'uz.lib': 'msg295="CPU ondemand scaling allaqachon qo\'llanilgan tizimlarda gamemode ishlatishning hech qanday aniq foydasi yo\'q. Baribir davom etasizmi?"',
    'vi.lib': 'msg295="Không có lợi ích hữu hình nào khi sử dụng gamemode trên các hệ thống đã áp dụng CPU ondemand scaling. Vẫn tiếp tục?"',
    'zh.lib': 'msg295="在已应用CPU ondemand scaling的系统中使用gamemode没有实际好处。仍要继续吗？"'
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
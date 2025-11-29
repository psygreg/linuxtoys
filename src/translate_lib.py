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
ENGLISH_MSG = 'msg305="This installation requires having paru, an AUR helper, available. Do you wish to install it now?"'

# Message ID to check for existence (update this for future messages)
MSG_ID = "msg305"

# Translations for the message in all supported languages (update these for future messages)
TRANSLATIONS = {
    'am.lib': 'msg305="ይህ ጭነት paru የሚባል AUR ረዳት መኖሩን ይፈልጋል። አሁን መጫን ይፈልጋሉ?"',
    'ar.lib': 'msg305="يتطلب هذا التثبيت توفر paru، وهو مساعد AUR. هل ترغب في تثبيته الآن؟"',
    'az.lib': 'msg305="Bu quraşdırma üçün paru adlı AUR köməkçisinin mövcud olması tələb olunur. İndi quraşdırmaq istəyirsiniz?"',
    'bg.lib': 'msg305="Тази инсталация изисква наличието на paru, помощник за AUR. Искате ли да го инсталирате сега?"',
    'bn.lib': 'msg305="এই ইনস্টলেশনের জন্য paru, একটি AUR সহায়ক উপলব্ধ থাকা প্রয়োজন। আপনি কি এটি এখন ইনস্টল করতে চান?"',
    'bs.lib': 'msg305="Za ovu instalaciju potrebno je imati paru, AUR pomoćnik. Želite li ga instalirati sada?"',
    'cs.lib': 'msg305="Tato instalace vyžaduje dostupnost paru, AUR pomocníka. Přejete si jej nyní nainstalovat?"',
    'da.lib': 'msg305="Denne installation kræver, at paru, en AUR-hjælper, er tilgængelig. Ønsker du at installere den nu?"',
    'de.lib': 'msg305="Diese Installation erfordert paru, einen AUR-Helfer. Möchten Sie ihn jetzt installieren?"',
    'el.lib': 'msg305="Αυτή η εγκατάσταση απαιτεί τη διαθεσιμότητα του paru, ενός βοηθού AUR. Θέλετε να το εγκαταστήσετε τώρα;"',
    'es.lib': 'msg305="Esta instalación requiere tener paru, un asistente de AUR, disponible. ¿Desea instalarlo ahora?"',
    'et.lib': 'msg305="See installatsioon nõuab paru, AUR-i abistaja olemasolu. Kas soovite selle nüüd installida?"',
    'fa.lib': 'msg305="این نصب نیاز به دسترسی به paru، یک کمک‌کننده AUR دارد. آیا می‌خواهید آن را اکنون نصب کنید؟"',
    'fi.lib': 'msg305="Tämä asennus vaatii paru-nimisen AUR-apuohjelman. Haluatko asentaa sen nyt?"',
    'fr.lib': 'msg305="Cette installation nécessite la disponibilité de paru, un assistant AUR. Souhaitez-vous l\'installer maintenant ?"',
    'ga.lib': 'msg305="Teastaíonn paru, cúntóir AUR, don tsuiteáil seo. Ar mhaith leat é a shuiteáil anois?"',
    'he.lib': 'msg305="התקנה זו דורשת את paru, עוזר AUR, זמין. האם ברצונך להתקין אותו כעת?"',
    'hi.lib': 'msg305="इस इंस्टॉलेशन के लिए paru, एक AUR सहायक उपलब्ध होना आवश्यक है। क्या आप इसे अभी इंस्टॉल करना चाहते हैं?"',
    'hr.lib': 'msg305="Za ovu instalaciju potreban je paru, AUR pomoćnik. Želite li ga instalirati sada?"',
    'hu.lib': 'msg305="Ez a telepítés megköveteli a paru, egy AUR segéd meglétét. Szeretné most telepíteni?"',
    'hy.lib': 'msg305="Այս տեղադրումը պահանջում է paru՝ AUR օգնական: Ցանկանու՞մ եք այն տեղադրել հիմա:"',
    'id.lib': 'msg305="Instalasi ini memerlukan paru, pembantu AUR, tersedia. Apakah Anda ingin menginstalnya sekarang?"',
    'is.lib': 'msg305="Þessi uppsetning krefst þess að paru, AUR hjálpartól, sé tiltækt. Viltu setja það upp núna?"',
    'it.lib': 'msg305="Questa installazione richiede la disponibilità di paru, un helper AUR. Desideri installarlo ora?"',
    'ja.lib': 'msg305="このインストールには、AURヘルパーであるparuが必要です。今すぐインストールしますか？"',
    'ka.lib': 'msg305="ამ ინსტალაციას სჭირდება paru, AUR დამხმარე. გსურთ მისი ახლავე დაინსტალირება?"',
    'km.lib': 'msg305="ការដំឡើងនេះត្រូវការ paru ដែលជាជំនួយការ AUR ដែលមាន។ តើអ្នកចង់ដំឡើងវាឥឡូវនេះទេ?"',
    'ko.lib': 'msg305="이 설치는 AUR 도우미인 paru가 필요합니다. 지금 설치하시겠습니까?"',
    'lo.lib': 'msg305="ການຕິດຕັ້ງນີ້ຕ້ອງການໃຫ້ມີ paru, ຕົວຊ່ວຍ AUR. ທ່ານຕ້ອງການຕິດຕັ້ງມັນດຽວນີ້ບໍ່?"',
    'lt.lib': 'msg305="Šiam diegimui reikia turėti paru, AUR pagalbininką. Ar norite jį įdiegti dabar?"',
    'lv.lib': 'msg305="Šai instalācijai ir nepieciešams paru, AUR palīgs. Vai vēlaties to instalēt tūlīt?"',
    'mn.lib': 'msg305="Энэ суулгац нь paru буюу AUR туслагч байхыг шаарддаг. Та үүнийг одоо суулгахыг хүсч байна уу?"',
    'ms.lib': 'msg305="Pemasangan ini memerlukan paru, pembantu AUR, tersedia. Adakah anda ingin memasangnya sekarang?"',
    'my.lib': 'msg305="ဤထည့်သွင်းမှုသည် paru, AUR အကူအညီ ရရှိနိုင်ရန် လိုအပ်သည်။ ယခု ထည့်သွင်းလိုပါသလား?"',
    'nb.lib': 'msg305="Denne installasjonen krever at paru, en AUR-hjelper, er tilgjengelig. Ønsker du å installere den nå?"',
    'ne.lib': 'msg305="यो स्थापनाको लागि paru, एक AUR सहायक उपलब्ध हुनु आवश्यक छ। के तपाईं यसलाई अहिले स्थापना गर्न चाहनुहुन्छ?"',
    'nl.lib': 'msg305="Deze installatie vereist dat paru, een AUR-helper, beschikbaar is. Wilt u het nu installeren?"',
    'pl.lib': 'msg305="Ta instalacja wymaga dostępności paru, pomocnika AUR. Czy chcesz go teraz zainstalować?"',
    'pt.lib': 'msg305="Esta instalação requer ter o paru, um auxiliar do AUR, disponível. Deseja instalá-lo agora?"',
    'ro.lib': 'msg305="Această instalare necesită disponibilitatea paru, un asistent AUR. Doriți să-l instalați acum?"',
    'ru.lib': 'msg305="Для этой установки требуется наличие paru, помощника AUR. Хотите установить его сейчас?"',
    'sk.lib': 'msg305="Táto inštalácia vyžaduje dostupnosť paru, AUR pomocníka. Prajete si ho teraz nainštalovať?"',
    'sl.lib': 'msg305="Ta namestitev zahteva razpoložljivost paru, pomočnika AUR. Želite ga namestiti zdaj?"',
    'sq.lib': 'msg305="Ky instalim kërkon që paru, një ndihmës AUR, të jetë i disponueshëm. A dëshironi ta instaloni tani?"',
    'sr.lib': 'msg305="Ова инсталација захтева да буде доступан paru, AUR помоћник. Да ли желите да га инсталирате сада?"',
    'sv.lib': 'msg305="Denna installation kräver att paru, en AUR-hjälpare, är tillgänglig. Vill du installera den nu?"',
    'sw.lib': 'msg305="Usakinishaji huu unahitaji kuwa na paru, msaidizi wa AUR, inapatikana. Je, ungependa kuisakinisha sasa?"',
    'ta.lib': 'msg305="இந்த நிறுவல் paru, ஒரு AUR உதவியாளர் இருப்பதை தேவைப்படுத்துகிறது. நீங்கள் அதை இப்போது நிறுவ விரும்புகிறீர்களா?"',
    'tg.lib': 'msg305="Ин насбкунӣ дастрасии paru, ёрдамчии AUR-ро талаб мекунад. Мехоҳед онро ҳозир насб кунед?"',
    'th.lib': 'msg305="การติดตั้งนี้ต้องการให้มี paru ซึ่งเป็นผู้ช่วย AUR คุณต้องการติดตั้งตอนนี้หรือไม่?"',
    'tl.lib': 'msg305="Ang pag-install na ito ay nangangailangan ng paru, isang katulong ng AUR, na available. Nais mo bang i-install ito ngayon?"',
    'tr.lib': 'msg305="Bu kurulum için paru adlı bir AUR yardımcısının mevcut olması gerekiyor. Şimdi yüklemek ister misiniz?"',
    'uk.lib': 'msg305="Для цього встановлення потрібна наявність paru, помічника AUR. Бажаєте встановити його зараз?"',
    'ur.lib': 'msg305="اس تنصیب کے لیے paru، ایک AUR مددگار کی ضرورت ہے۔ کیا آپ اسے ابھی انسٹال کرنا چاہتے ہیں؟"',
    'uz.lib': 'msg305="Bu o\'rnatish uchun paru, AUR yordamchisi mavjud bo\'lishi kerak. Uni hozir o\'rnatmoqchimisiz?"',
    'vi.lib': 'msg305="Cài đặt này yêu cầu có paru, một trình trợ giúp AUR. Bạn có muốn cài đặt nó ngay bây giờ không?"',
    'zh.lib': 'msg305="此安装需要有paru（AUR助手）可用。您想现在安装它吗？"'
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
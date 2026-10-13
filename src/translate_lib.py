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
        'noresolve': 'noresolve="DaVinci Resolve በዚህ ኮምፒውተር ላይ አልተጫነም። ይጫኑትና እንደገና ይሞክሩ።"'
    },
    'ar.lib': {
        'noresolve': 'noresolve="برنامج DaVinci Resolve غير مثبت حاليًا على هذا الكمبيوتر. ثبّته وحاول مرة أخرى."'
    },
    'az.lib': {
        'noresolve': 'noresolve="DaVinci Resolve hazırda bu kompüterdə quraşdırılmayıb. Onu quraşdırın və yenidən cəhd edin."'
    },
    'bg.lib': {
        'noresolve': 'noresolve="DaVinci Resolve в момента не е инсталиран на този компютър. Инсталирайте го и опитайте отново."'
    },
    'bn.lib': {
        'noresolve': 'noresolve="DaVinci Resolve বর্তমানে এই কম্পিউটারে ইনস্টল করা নেই। এটি ইনস্টল করে আবার চেষ্টা করুন।"'
    },
    'bs.lib': {
        'noresolve': 'noresolve="DaVinci Resolve trenutno nije instaliran na ovom računaru. Instalirajte ga i pokušajte ponovo."'
    },
    'cs.lib': {
        'noresolve': 'noresolve="DaVinci Resolve není v tomto počítači aktuálně nainstalován. Nainstalujte jej a zkuste to znovu."'
    },
    'da.lib': {
        'noresolve': 'noresolve="DaVinci Resolve er ikke installeret på denne computer. Installer det, og prøv igen."'
    },
    'de.lib': {
        'noresolve': 'noresolve="DaVinci Resolve ist derzeit nicht auf diesem Computer installiert. Installieren Sie es und versuchen Sie es erneut."'
    },
    'el.lib': {
        'noresolve': 'noresolve="Το DaVinci Resolve δεν είναι εγκατεστημένο αυτή τη στιγμή σε αυτόν τον υπολογιστή. Εγκαταστήστε το και δοκιμάστε ξανά."'
    },
    'es.lib': {
        'noresolve': 'noresolve="DaVinci Resolve no está instalado actualmente en este equipo. Instálalo e inténtalo de nuevo."'
    },
    'et.lib': {
        'noresolve': 'noresolve="DaVinci Resolve pole praegu sellesse arvutisse paigaldatud. Paigaldage see ja proovige uuesti."'
    },
    'fa.lib': {
        'noresolve': 'noresolve="DaVinci Resolve در حال حاضر روی این رایانه نصب نیست. آن را نصب کنید و دوباره تلاش کنید."'
    },
    'fi.lib': {
        'noresolve': 'noresolve="DaVinci Resolvea ei ole tällä hetkellä asennettu tähän tietokoneeseen. Asenna se ja yritä uudelleen."'
    },
    'fr.lib': {
        'noresolve': 'noresolve="DaVinci Resolve n’est actuellement pas installé sur cet ordinateur. Installez-le et réessayez."'
    },
    'ga.lib': {
        'noresolve': 'noresolve="Níl DaVinci Resolve suiteáilte ar an ríomhaire seo faoi láthair. Suiteáil é agus bain triail eile as."'
    },
    'he.lib': {
        'noresolve': 'noresolve="DaVinci Resolve אינו מותקן כרגע במחשב זה. התקינו אותו ונסו שוב."'
    },
    'hi.lib': {
        'noresolve': 'noresolve="DaVinci Resolve वर्तमान में इस कंप्यूटर पर इंस्टॉल नहीं है। इसे इंस्टॉल करें और फिर से प्रयास करें।"'
    },
    'hr.lib': {
        'noresolve': 'noresolve="DaVinci Resolve trenutačno nije instaliran na ovom računalu. Instalirajte ga i pokušajte ponovno."'
    },
    'hu.lib': {
        'noresolve': 'noresolve="A DaVinci Resolve jelenleg nincs telepítve erre a számítógépre. Telepítse, majd próbálja újra."'
    },
    'hy.lib': {
        'noresolve': 'noresolve="DaVinci Resolve-ը ներկայումս տեղադրված չէ այս համակարգչում։ Տեղադրեք այն և կրկին փորձեք։"'
    },
    'id.lib': {
        'noresolve': 'noresolve="DaVinci Resolve saat ini belum terinstal di komputer ini. Instal terlebih dahulu, lalu coba lagi."'
    },
    'is.lib': {
        'noresolve': 'noresolve="DaVinci Resolve er ekki uppsett á þessari tölvu eins og er. Settu það upp og reyndu aftur."'
    },
    'it.lib': {
        'noresolve': 'noresolve="DaVinci Resolve non è attualmente installato su questo computer. Installalo e riprova."'
    },
    'ja.lib': {
        'noresolve': 'noresolve="DaVinci Resolve は現在このコンピューターにインストールされていません。インストールしてから再試行してください。"'
    },
    'ka.lib': {
        'noresolve': 'noresolve="DaVinci Resolve ამჟამად ამ კომპიუტერზე არ არის დაინსტალირებული. დააინსტალირეთ და ხელახლა სცადეთ."'
    },
    'km.lib': {
        'noresolve': 'noresolve="DaVinci Resolve មិនទាន់បានដំឡើងនៅលើកុំព្យូទ័រនេះទេ។ សូមដំឡើងវា ហើយព្យាយាមម្តងទៀត។"'
    },
    'ko.lib': {
        'noresolve': 'noresolve="DaVinci Resolve가 현재 이 컴퓨터에 설치되어 있지 않습니다. 설치한 후 다시 시도하세요."'
    },
    'lo.lib': {
        'noresolve': 'noresolve="DaVinci Resolve ຍັງບໍ່ໄດ້ຕິດຕັ້ງໃນຄອມພິວເຕີນີ້. ກະລຸນາຕິດຕັ້ງແລ້ວລອງໃໝ່."'
    },
    'lt.lib': {
        'noresolve': 'noresolve="DaVinci Resolve šiuo metu neįdiegta šiame kompiuteryje. Įdiekite ją ir bandykite dar kartą."'
    },
    'lv.lib': {
        'noresolve': 'noresolve="DaVinci Resolve pašlaik nav instalēts šajā datorā. Instalējiet to un mēģiniet vēlreiz."'
    },
    'mn.lib': {
        'noresolve': 'noresolve="DaVinci Resolve одоогоор энэ компьютерт суулгагдаагүй байна. Суулгаад дахин оролдоно уу."'
    },
    'ms.lib': {
        'noresolve': 'noresolve="DaVinci Resolve belum dipasang pada komputer ini. Pasangkannya dan cuba lagi."'
    },
    'my.lib': {
        'noresolve': 'noresolve="DaVinci Resolve ကို ဤကွန်ပျူတာတွင် လက်ရှိ ထည့်သွင်းထားခြင်း မရှိပါ။ ထည့်သွင်းပြီး ထပ်မံကြိုးစားပါ။"'
    },
    'nb.lib': {
        'noresolve': 'noresolve="DaVinci Resolve er ikke installert på denne datamaskinen. Installer det og prøv igjen."'
    },
    'ne.lib': {
        'noresolve': 'noresolve="DaVinci Resolve हाल यो कम्प्युटरमा स्थापना गरिएको छैन। यसलाई स्थापना गरेर फेरि प्रयास गर्नुहोस्।"'
    },
    'nl.lib': {
        'noresolve': 'noresolve="DaVinci Resolve is momenteel niet op deze computer geïnstalleerd. Installeer het en probeer het opnieuw."'
    },
    'pl.lib': {
        'noresolve': 'noresolve="DaVinci Resolve nie jest obecnie zainstalowany na tym komputerze. Zainstaluj go i spróbuj ponownie."'
    },
    'pt.lib': {
        'noresolve': 'noresolve="O DaVinci Resolve não está instalado neste computador. Instale-o e tente novamente."'
    },
    'ro.lib': {
        'noresolve': 'noresolve="DaVinci Resolve nu este instalat în prezent pe acest computer. Instalați-l și încercați din nou."'
    },
    'ru.lib': {
        'noresolve': 'noresolve="DaVinci Resolve сейчас не установлен на этом компьютере. Установите его и повторите попытку."'
    },
    'sk.lib': {
        'noresolve': 'noresolve="DaVinci Resolve momentálne nie je nainštalovaný na tomto počítači. Nainštalujte ho a skúste to znova."'
    },
    'sl.lib': {
        'noresolve': 'noresolve="DaVinci Resolve trenutno ni nameščen na tem računalniku. Namestite ga in poskusite znova."'
    },
    'sq.lib': {
        'noresolve': 'noresolve="DaVinci Resolve nuk është aktualisht i instaluar në këtë kompjuter. Instalojeni dhe provoni përsëri."'
    },
    'sr.lib': {
        'noresolve': 'noresolve="DaVinci Resolve тренутно није инсталиран на овом рачунару. Инсталирајте га и покушајте поново."'
    },
    'sv.lib': {
        'noresolve': 'noresolve="DaVinci Resolve är för närvarande inte installerat på den här datorn. Installera det och försök igen."'
    },
    'sw.lib': {
        'noresolve': 'noresolve="DaVinci Resolve haijasakinishwa kwenye kompyuta hii kwa sasa. Isakinishe kisha ujaribu tena."'
    },
    'ta.lib': {
        'noresolve': 'noresolve="DaVinci Resolve தற்போது இந்தக் கணினியில் நிறுவப்படவில்லை. அதை நிறுவி மீண்டும் முயற்சிக்கவும்."'
    },
    'tg.lib': {
        'noresolve': 'noresolve="DaVinci Resolve ҳоло дар ин компютер насб нашудааст. Онро насб кунед ва дубора кӯшиш кунед."'
    },
    'th.lib': {
        'noresolve': 'noresolve="ขณะนี้ยังไม่ได้ติดตั้ง DaVinci Resolve บนคอมพิวเตอร์เครื่องนี้ โปรดติดตั้งแล้วลองอีกครั้ง"'
    },
    'tl.lib': {
        'noresolve': 'noresolve="Hindi kasalukuyang naka-install ang DaVinci Resolve sa computer na ito. I-install ito at subukan ulit."'
    },
    'tr.lib': {
        'noresolve': 'noresolve="DaVinci Resolve şu anda bu bilgisayarda yüklü değil. Yükleyip tekrar deneyin."'
    },
    'uk.lib': {
        'noresolve': 'noresolve="DaVinci Resolve наразі не встановлено на цьому комп’ютері. Встановіть його та спробуйте ще раз."'
    },
    'ur.lib': {
        'noresolve': 'noresolve="DaVinci Resolve فی الحال اس کمپیوٹر پر انسٹال نہیں ہے۔ اسے انسٹال کریں اور دوبارہ کوشش کریں۔"'
    },
    'uz.lib': {
        'noresolve': 'noresolve="DaVinci Resolve hozirda ushbu kompyuterga o‘rnatilmagan. Uni o‘rnating va qayta urinib ko‘ring."'
    },
    'vi.lib': {
        'noresolve': 'noresolve="DaVinci Resolve hiện chưa được cài đặt trên máy tính này. Hãy cài đặt rồi thử lại."'
    },
    'zh.lib': {
        'noresolve': 'noresolve="此计算机目前未安装 DaVinci Resolve。请先安装，然后重试。"'
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

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
ENGLISH_MSG = 'nocl="No OpenCL detected. Please install ROCm, RustiCL, or Intel\'s Compute Runtime from the Drivers menu according to your GPU model."'

# Message ID to check for existence (update this for future messages)
MSG_ID = "nocl"

# Translations for the message in all supported languages (update these for future messages)
TRANSLATIONS = {
    'am.lib': 'nocl="OpenCL አልተገኘም። እባክዎ ROCm፣ RustiCL፣ ወይም Intel\'s Compute Runtime ን በ Drivers ምናሌ ላይ ከመጫን በ GPU ሞዴልዎ መሠረት።"',
    'ar.lib': 'nocl="لم يتم اكتشاف OpenCL. يرجى تثبيت ROCm أو RustiCL أو Intel\'s Compute Runtime من قائمة Drivers وفقًا لنموذج GPU الخاص بك."',
    'az.lib': 'nocl="OpenCL aşkar edilmədi. Lütfən GPU modelinizə uyğun olaraq Drivers menyusundan ROCm, RustiCL və ya Intel\'s Compute Runtime-ı quraşdırın."',
    'bg.lib': 'nocl="OpenCL не е обнаружен. Моля, инсталирайте ROCm, RustiCL или Intel\'s Compute Runtime от менюто Drivers според вашия GPU модел."',
    'bn.lib': 'nocl="OpenCL সনাক্ত করা হয়নি। অনুগ্রহ করে আপনার GPU মডেল অনুযায়ী Drivers মেনু থেকে ROCm, RustiCL বা Intel\'s Compute Runtime ইনস্টল করুন।"',
    'bs.lib': 'nocl="OpenCL nije detektovan. Molimo instalirajte ROCm, RustiCL ili Intel\'s Compute Runtime iz Drivers menija prema vašem GPU modelu."',
    'cs.lib': 'nocl="OpenCL nebyl zjištěn. Prosím, nainstalujte ROCm, RustiCL nebo Intel\'s Compute Runtime z nabídky Drivers podle vašeho modelu GPU."',
    'da.lib': 'nocl="OpenCL blev ikke registreret. Installér venligst ROCm, RustiCL eller Intel\'s Compute Runtime fra Drivers-menuen i henhold til din GPU-model."',
    'de.lib': 'nocl="OpenCL nicht erkannt. Bitte installieren Sie ROCm, RustiCL oder Intel\'s Compute Runtime aus dem Drivers-Menü gemäß Ihrem GPU-Modell."',
    'el.lib': 'nocl="Το OpenCL δεν ανιχνεύθηκε. Εγκαταστήστε το ROCm, RustiCL ή Intel\'s Compute Runtime από το μενού Drivers σύμφωνα με το μοντέλο της GPU σας."',
    'es.lib': 'nocl="OpenCL no detectado. Instale ROCm, RustiCL o Intel\'s Compute Runtime desde el menú Drivers según su modelo de GPU."',
    'et.lib': 'nocl="OpenCL-i ei leitud. Palun installige ROCm, RustiCL või Intel\'s Compute Runtime menüüst Drivers vastavalt oma GPU mudelile."',
    'fa.lib': 'nocl="OpenCL یافت نشد. لطفاً ROCm، RustiCL یا Intel\'s Compute Runtime را از منوی Drivers با توجه به مدل GPU خود نصب کنید."',
    'fi.lib': 'nocl="OpenCL:ää ei havaittu. Asenna ROCm, RustiCL tai Intel\'s Compute Runtime Drivers-valikosta GPU-mallisi mukaan."',
    'fr.lib': 'nocl="OpenCL non détecté. Veuillez installer ROCm, RustiCL ou Intel\'s Compute Runtime à partir du menu Drivers selon votre modèle de GPU."',
    'ga.lib': 'nocl="Níor bhraistí OpenCL. Socrú ROCm, RustiCL nó Intel\'s Compute Runtime ó roghchlár an Drivers de réir do ghréine GPU."',
    'he.lib': 'nocl="OpenCL לא זוהה. אנא התקן את ROCm, RustiCL או Intel\'s Compute Runtime מתפריט Drivers בהתאם לדגם ה-GPU שלך."',
    'hi.lib': 'nocl="OpenCL का पता नहीं चला। कृपया अपने GPU मॉडल के अनुसार Drivers मेनू से ROCm, RustiCL या Intel\'s Compute Runtime स्थापित करें।"',
    'hr.lib': 'nocl="OpenCL nije pronađen. Molimo instalirajte ROCm, RustiCL ili Intel\'s Compute Runtime iz Drivers menija prema vašem GPU modelu."',
    'hu.lib': 'nocl="OpenCL nem talált. Kérem, telepítse a ROCm, RustiCL vagy Intel\'s Compute Runtime a Drivers menüből az Ön GPU modellje szerint."',
    'hy.lib': 'nocl="OpenCL չի հայտնաբերվել: Խնդրում եմ տեղադրել ROCm-ը, RustiCL-ը կամ Intel\'s Compute Runtime-ը Drivers ընտրացանցից ձեր GPU մոդելի համաձայն:"',
    'id.lib': 'nocl="OpenCL tidak terdeteksi. Harap instal ROCm, RustiCL, atau Intel\'s Compute Runtime dari menu Drivers sesuai dengan model GPU Anda."',
    'is.lib': 'nocl="OpenCL fannst ekki. Settu upp ROCm, RustiCL eða Intel\'s Compute Runtime frá Drivers valmyndinni í samræmi við GPU módelinn þinn."',
    'it.lib': 'nocl="OpenCL non rilevato. Installa ROCm, RustiCL o Intel\'s Compute Runtime dal menu Drivers secondo il tuo modello GPU."',
    'ja.lib': 'nocl="OpenCLが検出されません。GPU モデルに応じて、ドライバーメニューから ROCm、RustiCL、または Intel\'s Compute Runtime をインストールしてください。"',
    'ka.lib': 'nocl="OpenCL არ აღმოჩნდა. გთხოვთ დაადგინოთ ROCm, RustiCL ან Intel\'s Compute Runtime Drivers მენიუდან თქვენი GPU მოდელის მიხედვით."',
    'km.lib': 'nocl="មិនបានរកឃើញ OpenCL ទេ។ សូមដំឡើង ROCm, RustiCL ឬ Intel\'s Compute Runtime ពីម៉េនុយ Drivers យោងទៅតាមម៉ូដែល GPU របស់អ្នក។"',
    'ko.lib': 'nocl="OpenCL을 찾을 수 없습니다. GPU 모델에 따라 드라이버 메뉴에서 ROCm, RustiCL 또는 Intel\'s Compute Runtime을 설치하세요."',
    'lo.lib': 'nocl="OpenCL ບໍ່ພົບ. ກະລຸນາຕິດຕັ້ງ ROCm, RustiCL ຫຼື Intel\'s Compute Runtime ຈາກເມນູ Drivers ອີງຕາມແບບ GPU ຂອງທ່ານ."',
    'lt.lib': 'nocl="OpenCL nerastas. Prašome diegti ROCm, RustiCL arba Intel\'s Compute Runtime iš Drivers meniu pagal jūsų GPU modelį."',
    'lv.lib': 'nocl="OpenCL nav atrasts. Lūdzu, instalējiet ROCm, RustiCL vai Intel\'s Compute Runtime no Drivers izvēlnes saskaņā ar jūsu GPU modeli."',
    'mn.lib': 'nocl="OpenCL олдсонгүй. Өөрийн GPU загвараас хамаарч Drivers цэсээс ROCm, RustiCL эсвэл Intel\'s Compute Runtime-ийг суулгаад өгнө үү."',
    'ms.lib': 'nocl="OpenCL tidak dikesan. Sila pasang ROCm, RustiCL, atau Intel\'s Compute Runtime daripada menu Drivers mengikut model GPU anda."',
    'my.lib': 'nocl="OpenCL မတွေ့ရှိ။ သင့်ကြီးအုပ်စုအလိုက်မပုံစံအတိုင်း Drivers မီနူးမှ ROCm၊ RustiCL သို့မဟုတ် Intel\'s Compute Runtime ကို ထည့်သွင်းပါ။"',
    'nb.lib': 'nocl="OpenCL ble ikke funnet. Installer ROCm, RustiCL eller Intel\'s Compute Runtime fra Drivers-menyen i henhold til GPU-modellen din."',
    'ne.lib': 'nocl="OpenCL पत्ता नलागेको छ। कृपया आपको GPU मोडेल अनुसार Drivers मेनुबाट ROCm, RustiCL वा Intel\'s Compute Runtime स्थापना गर्नुहोस्।"',
    'nl.lib': 'nocl="OpenCL niet gedetecteerd. Installeer ROCm, RustiCL of Intel\'s Compute Runtime uit het Drivers-menu naar gelang uw GPU-model."',
    'pl.lib': 'nocl="OpenCL nie znaleziono. Prosimy zainstalować ROCm, RustiCL lub Intel\'s Compute Runtime z menu Drivers zgodnie z Twoim modelem GPU."',
    'pt.lib': 'nocl="OpenCL não detectado. Instale ROCm, RustiCL ou Intel\'s Compute Runtime no menu Drivers de acordo com o modelo da sua GPU."',
    'ro.lib': 'nocl="OpenCL nu a fost detectat. Instalați ROCm, RustiCL sau Intel\'s Compute Runtime din meniul Drivers în funcție de modelul GPU-ului dvs."',
    'ru.lib': 'nocl="OpenCL не обнаружен. Установите ROCm, RustiCL или Intel\'s Compute Runtime из меню Drivers в соответствии с моделью вашего GPU."',
    'sk.lib': 'nocl="OpenCL nenájdený. Prosím, nainštalujte ROCm, RustiCL alebo Intel\'s Compute Runtime z ponuky Drivers podľa vášho modelu GPU."',
    'sl.lib': 'nocl="OpenCL ni bil najden. Prosim, namestite ROCm, RustiCL ali Intel\'s Compute Runtime iz menija Drivers v skladu z vašim modelom GPU."',
    'sq.lib': 'nocl="OpenCL nuk u zbulua. Ju lutemi instaloni ROCm, RustiCL ose Intel\'s Compute Runtime nga menyja e Drivers sipas modelit tuaj të GPU-s."',
    'sr.lib': 'nocl="OpenCL није нађен. Молимо инсталирајте ROCm, RustiCL или Intel\'s Compute Runtime из Drivers менија према вашем GPU моделу."',
    'sv.lib': 'nocl="OpenCL hittades inte. Installera ROCm, RustiCL eller Intel\'s Compute Runtime från Drivers-menyn enligt din GPU-modell."',
    'sw.lib': 'nocl="OpenCL haikuonekani. Tafadhali sanidi ROCm, RustiCL, au Intel\'s Compute Runtime kutoka kwa menyu ya Drivers kulingana na muundo wa GPU yako."',
    'ta.lib': 'nocl="OpenCL கண்டறியப்படவில்லை. உங்கள் GPU மாதிரிக்கு ஏற்ப Drivers மெனுவிலிருந்து ROCm, RustiCL அல்லது Intel\'s Compute Runtime ஐ நிறுவவும்."',
    'tg.lib': 'nocl="OpenCL ёфта нашудааст. Лутфан ROCm, RustiCL ё Intel\'s Compute Runtime-ро аз менюи Drivers мувофиқи модели GPU-и худ насб кунед."',
    'th.lib': 'nocl="ไม่พบ OpenCL โปรดติดตั้ง ROCm, RustiCL หรือ Intel\'s Compute Runtime จากเมนู Drivers ตามรุ่น GPU ของคุณ"',
    'tl.lib': 'nocl="Walang OpenCL na nahanap. Mangyaring i-install ang ROCm, RustiCL o Intel\'s Compute Runtime mula sa Drivers menu ayon sa iyong GPU model."',
    'tr.lib': 'nocl="OpenCL bulunamadı. Lütfen GPU modelinize göre Drivers menüsünden ROCm, RustiCL veya Intel\'s Compute Runtime yükleyin."',
    'uk.lib': 'nocl="OpenCL не знайдено. Встановіть ROCm, RustiCL або Intel\'s Compute Runtime з меню Drivers відповідно до моделі вашої GPU."',
    'ur.lib': 'nocl="OpenCL نہیں ملا۔ براہ مہربانی اپنے GPU ماڈل کے مطابق Drivers مینو سے ROCm، RustiCL یا Intel\'s Compute Runtime انسٹال کریں۔"',
    'uz.lib': 'nocl="OpenCL topilmadi. Iltimos, GPU modelingizga muvofiq Drivers menyusidan ROCm, RustiCL yoki Intel\'s Compute Runtime o\'rnating."',
    'vi.lib': 'nocl="Không tìm thấy OpenCL. Vui lòng cài đặt ROCm, RustiCL hoặc Intel\'s Compute Runtime từ menu Drivers theo mô hình GPU của bạn."',
    'zh.lib': 'nocl="未检测到OpenCL。请根据您的GPU型号从驱动程序菜单安装ROCm、RustiCL或Intel\'s Compute Runtime。"'
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
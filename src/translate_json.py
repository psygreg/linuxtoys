import json
import os

# Directory containing the language files
lang_dir = '../p3/libs/lang/'

# Translations dictionary: key -> {lang_code: translation}
translations = {
    'unsupported_os_title': {
        'am': 'ያልተደገፈ ስርዓት',
        'ar': 'نظام غير مدعوم',
        'az': 'Dəstəklənməyən Sistem',
        'bg': 'Неподдържана система',
        'bn': 'অসমর্থিত সিস্টেম',
        'bs': 'Nepodržani sistem',
        'cs': 'Nepodporovaný systém',
        'da': 'Ikke-understøttet system',
        'de': 'Nicht unterstütztes System',
        'el': 'Μη υποστηριζόμενο σύστημα',
        'es': 'Sistema no compatible',
        'et': 'Toetamata süsteem',
        'fa': 'سیستم پشتیبانی نشده',
        'fi': 'Ei-tuettu järjestelmä',
        'fr': 'Système non pris en charge',
        'ga': 'Córas gan tacaíocht',
        'he': 'מערכת לא נתמכת',
        'hi': 'असमर्थित सिस्टम',
        'hr': 'Nepodržani sustav',
        'hu': 'Nem támogatott rendszer',
        'hy': 'Չապահովված համակարգ',
        'id': 'Sistem tidak didukung',
        'is': 'Óstutt kerfi',
        'it': 'Sistema non supportato',
        'ja': 'サポートされていないシステム',
        'ka': 'მხარდაჭერილი არ არის სისტემა',
        'km': 'ប្រព័ន្ធមិនគាំទ្រ',
        'ko': '지원되지 않는 시스템',
        'lo': 'ລະບົບທີ່ບໍ່ຮອງຮັບ',
        'lt': 'Nepalaikoma sistema',
        'lv': 'Neatbalstīta sistēma',
        'mn': 'Дэмжигдээгүй систем',
        'ms': 'Sistem tidak disokong',
        'my': 'မပံ့ပိုးသော စနစ်',
        'nb': 'Ikke støttet system',
        'ne': 'असमर्थित प्रणाली',
        'nl': 'Niet-ondersteund systeem',
        'pl': 'Nieobsługiwany system',
        'pt': 'Sistema não suportado',
        'ro': 'Sistem neacceptat',
        'ru': 'Неподдерживаемая система',
        'sk': 'Nepodporovaný systém',
        'sl': 'Nepodprt sistem',
        'sq': 'Sistem i pambështetur',
        'sr': 'Неподржани систем',
        'sv': 'Ej stöds system',
        'sw': 'Mfumo usiotumika',
        'ta': 'ஆதரிக்கப்படாத அமைப்பு',
        'tg': 'Системаи дастгирӣнашуда',
        'th': 'ระบบที่ไม่รองรับ',
        'tl': 'Hindi suportadong sistema',
        'tr': 'Desteklenmeyen sistem',
        'uk': 'Непідтримувана система',
        'ur': 'غیر معاون نظام',
        'uz': 'Qo\'llab-quvvatlanmaydigan tizim',
        'vi': 'Hệ thống không được hỗ trợ',
        'zh': '不支持的系统'
    },
    'unsupported_os_message': {
        'am': 'ያልተደገፈ የስርዓት አሰራር።',
        'ar': 'نظام تشغيل غير مدعوم.',
        'az': 'Dəstəklənməyən əməliyyat sistemi.',
        'bg': 'Неподдържана операционна система.',
        'bn': 'অসমর্থিত অপারেটিং সিস্টেম।',
        'bs': 'Nepodržani operativni sistem.',
        'cs': 'Nepodporovaný operační systém.',
        'da': 'Ikke-understøttet operativsystem.',
        'de': 'Nicht unterstütztes Betriebssystem.',
        'el': 'Μη υποστηριζόμενο λειτουργικό σύστημα.',
        'es': 'Sistema operativo no compatible.',
        'et': 'Toetamata operatsioonisüsteem.',
        'fa': 'سیستم عامل پشتیبانی نشده.',
        'fi': 'Ei-tuettu käyttöjärjestelmä.',
        'fr': 'Système d\'exploitation non pris en charge.',
        'ga': 'Córas oibriúcháin gan tacaíocht.',
        'he': 'מערכת הפעלה לא נתמכת.',
        'hi': 'असमर्थित ऑपरेटिंग सिस्टम।',
        'hr': 'Nepodržani operacijski sustav.',
        'hu': 'Nem támogatott operációs rendszer.',
        'hy': 'Չապահովված գործառնական համակարգ։',
        'id': 'Sistem operasi tidak didukung.',
        'is': 'Óstutt stýrikerfi.',
        'it': 'Sistema operativo non supportato.',
        'ja': 'サポートされていないオペレーティングシステム。',
        'ka': 'მხარდაჭერილი არ არის ოპერაციული სისტემა.',
        'km': 'ប្រព័ន្ធប្រតិបត្តិការមិនគាំទ្រ។',
        'ko': '지원되지 않는 운영 체제입니다.',
        'lo': 'ລະບົບປະຕິບັດການທີ່ບໍ່ຮອງຮັບ.',
        'lt': 'Nepalaikoma operacinė sistema.',
        'lv': 'Neatbalstīta operētājsistēma.',
        'mn': 'Дэмжигдээгүй үйлдлийн систем.',
        'ms': 'Sistem pengendalian tidak disokong.',
        'my': 'မပံ့ပိုးသော လည်ပတ်မှုစနစ်။',
        'nb': 'Ikke støttet operativsystem.',
        'ne': 'असमर्थित अपरेटिङ सिस्टम।',
        'nl': 'Niet-ondersteund besturingssysteem.',
        'pl': 'Nieobsługiwany system operacyjny.',
        'pt': 'Sistema operacional não suportado.',
        'ro': 'Sistem de operare neacceptat.',
        'ru': 'Неподдерживаемая операционная система.',
        'sk': 'Nepodporovaný operačný systém.',
        'sl': 'Nepodprt operacijski sistem.',
        'sq': 'Sistem operativ i pambështetur.',
        'sr': 'Неподржани оперативни систем.',
        'sv': 'Ej stöds operativsystem.',
        'sw': 'Mfumo wa uendeshaji usiotumika.',
        'ta': 'ஆதரிக்கப்படாத இயக்க முறைமை.',
        'tg': 'Системаи амалкунандаи дастгирӣнашуда.',
        'th': 'ระบบปฏิบัติการที่ไม่รองรับ',
        'tl': 'Hindi suportadong operating system.',
        'tr': 'Desteklenmeyen işletim sistemi.',
        'uk': 'Непідтримувана операційна система.',
        'ur': 'غیر معاون آپریٹنگ سسٹم۔',
        'uz': 'Qo\'llab-quvvatlanmaydigan operatsion tizim.',
        'vi': 'Hệ điều hành không được hỗ trợ.',
        'zh': '不支持的操作系统。'
    }
}

# Skip 'en' since it's already added
for key, lang_translations in translations.items():
    for lang, translation in lang_translations.items():
        file_path = os.path.join(lang_dir, f'{lang}.json')
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            data[key] = translation
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f'Added {key} to {lang}.json')
        else:
            print(f'File {file_path} does not exist')
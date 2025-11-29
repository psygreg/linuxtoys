import json
import os

# Directory containing the language files
lang_dir = '../p3/libs/lang/'

# Translations dictionary: key -> {lang_code: translation}
translations = {
    'rtl8821ce_desc': {
        'am': 'rtl8821CE ሾፌር ከፍርማዌር ጋር',
        'ar': 'برنامج rtl8821CE مع البرامج الثابتة',
        'az': 'Firmware ilə rtl8821CE sürücüsü',
        'bg': 'rtl8821CE драйвер с фърмуер',
        'bn': 'ফার্মওয়্যার সহ rtl8821CE ড্রাইভার',
        'bs': 'rtl8821CE upravljač sa firmverom',
        'cs': 'rtl8821CE ovladač s firmwarem',
        'da': 'rtl8821CE-driver med firmware',
        'de': 'rtl8821CE-Treiber mit Firmware',
        'el': 'rtl8821CE δρ with firmware',
        'es': 'controlador rtl8821CE con firmware',
        'et': 'rtl8821CE draiver koos püsivara',
        'fa': 'درایور rtl8821CE با فریمور',
        'fi': 'rtl8821CE-ohjain ja ohjelmisto',
        'fr': 'Pilote rtl8821CE avec firmware',
        'ga': 'gealadh rtl8821CE le firmware',
        'he': 'כונן rtl8821CE עם הקנקייה',
        'hi': 'rtl8821CE ड्राइवर फर्मवेयर के साथ',
        'hr': 'rtl8821CE upravljač s firmverom',
        'hu': 'rtl8821CE meghajtó firmware-rel',
        'hy': 'rtl8821CE շարժիչ ամրակցիկով',
        'id': 'Driver rtl8821CE dengan firmware',
        'is': 'rtl8821CE rekill með firmware',
        'it': 'Driver rtl8821CE con firmware',
        'ja': 'ファームウェア付きrtl8821CEドライバー',
        'ka': 'rtl8821CE ფაილი ფიქრით',
        'km': 'កម្មវិធីបញ្ជាលេខ rtl8821CE ដែលមាន',
        'ko': 'ファームウェア포함 rtl8821CE드라이버',
        'lo': 'ຕົວຜະລິດ rtl8821CE ກັບ firmware',
        'lt': 'rtl8821CE tvarkyklė su programine įranga',
        'lv': 'rtl8821CE draiveris ar programmatūru',
        'mn': 'rtl8821CE драйвер суулгацтай',
        'ms': 'Pemacu rtl8821CE dengan firmware',
        'my': 'ფაილোჩერის rtl8821CE চালক',
        'nb': 'rtl8821CE-driver med firmware',
        'ne': 'rtl8821CE चालक फर्मवेयर सहित',
        'nl': 'rtl8821CE-stuurprogramma met firmware',
        'pl': 'Sterownik rtl8821CE z oprogramowaniem',
        'pt': 'Driver rtl8821CE com firmware',
        'ro': 'Driver rtl8821CE cu firmware',
        'ru': 'Драйвер rtl8821CE с прошивкой',
        'sk': 'Ovládač rtl8821CE s firmvérom',
        'sl': 'Gonilnik rtl8821CE s programsko opremo',
        'sq': 'Drajveri rtl8821CE me firmware',
        'sr': 'rtl8821CE управљач са фирмвером',
        'sv': 'rtl8821CE-drivrutin med firmware',
        'sw': 'Mwendesha rtl8821CE na firmware',
        'ta': 'rtl8821CE இயக்கி மென்பொருளுடன்',
        'tg': 'Драйвер rtl8821CE бо мафҳуми барқӣ',
        'th': 'ไดรเวอร์ rtl8821CE พร้อมเฟิร์มแวร์',
        'tl': 'Drayber rtl8821CE na may firmware',
        'tr': 'Donanım Yazılımı ile rtl8821CE sürücüsü',
        'uk': 'Драйвер rtl8821CE з прошивкою',
        'ur': 'rtl8821CE ڈرائیور فرم ویئر کے ساتھ',
        'uz': 'Rtl8821ce drayveri firmware bilan',
        'vi': 'Trình điều khiển rtl8821CE với chương trình',
        'zh': 'rtl8821CE驱动程序带固件'
    },
    'rcloneui_desc': {
        'am': 'rclone ስምምነት ለ GUI',
        'ar': 'واجهة رسومية لمزامنة rclone',
        'az': 'rclone sinkronizasiyası üçün GUI',
        'bg': 'Графичен интерфейс за синхронизиране на rclone',
        'bn': 'rclone সিঙ্ক্রোনাইজেশনের জন্য GUI',
        'bs': 'GUI za sinkronizaciju rclone',
        'cs': 'Grafické rozhraní pro synchronizaci rclone',
        'da': 'GUI til rclone-synkronisering',
        'de': 'GUI für rclone-Synchronisierung',
        'el': 'GUI για συγχρονισμό rclone',
        'es': 'GUI para sincronización de rclone',
        'et': 'GUI rclone sünkroniseerimiseks',
        'fa': 'رابط کاربری برای همگام سازی rclone',
        'fi': 'GUI rclone-synkronointiin',
        'fr': 'Interface graphique pour la synchronisation rclone',
        'ga': 'GUI do dhoimirt rclone',
        'he': 'ממשק המשתמש הגרפי לסנכרון rclone',
        'hi': 'rclone सिंक के लिए GUI',
        'hr': 'GUI za sinkronizaciju rclone',
        'hu': 'GUI az rclone szinkronizáláshoz',
        'hy': 'GUI rclone համաժամանակեցման համար',
        'id': 'GUI untuk sinkronisasi rclone',
        'is': 'GUI fyrir rclone samstillingu',
        'it': 'GUI per la sincronizzazione rclone',
        'ja': 'rclone同期用GUI',
        'ka': 'GUI rclone სინქროულობისთვის',
        'km': 'GUI សម្រាប់ការធ្វើឱ្យក្រុម rclone',
        'ko': 'rclone 동기화를 위한 GUI',
        'lo': 'GUI ສໍາລັບ rclone synchronization',
        'lt': 'GUI rclone sinchronizavimui',
        'lv': 'GUI rclone sinhronizācijai',
        'mn': 'rclone синхронизацийн GUI',
        'ms': 'GUI untuk sinkronisasi rclone',
        'my': 'rclone ကြေးများ အတွက် GUI',
        'nb': 'GUI for rclone-synkronisering',
        'ne': 'rclone सिंक्रोनाइजेशनका लागि GUI',
        'nl': 'GUI voor rclone-synchronisatie',
        'pl': 'GUI dla synchronizacji rclone',
        'pt': 'GUI para sincronização rclone',
        'ro': 'GUI pentru sincronizarea rclone',
        'ru': 'Графический интерфейс для синхронизации rclone',
        'sk': 'GUI pre synchronizáciu rclone',
        'sl': 'Grafični vmesnik za sinhronizacijo rclone',
        'sq': 'GUI për sinkronizimin rclone',
        'sr': 'Графички интерфејс за синхронизацију rclone',
        'sv': 'GUI för rclone-synkronisering',
        'sw': 'GUI kwa ulandanishi wa rclone',
        'ta': 'rclone ஒத்திசைப்புக்கான GUI',
        'tg': 'Интерфейси графикӣ барои sinkronizatsiya rclone',
        'th': 'GUI สำหรับการซิงค์ rclone',
        'tl': 'GUI para sa rclone na pag-sync',
        'tr': 'Rclone senkronizasyonu için GUI',
        'uk': 'Графічний інтерфейс для синхронізації rclone',
        'ur': 'rclone ہم وقتی کے لیے GUI',
        'uz': 'Rclone sinhronizasiyasi uchun GUI',
        'vi': 'GUI để đồng bộ hóa rclone',
        'zh': 'rclone同步的GUI'
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
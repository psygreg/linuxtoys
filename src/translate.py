import json
import os

# Directory containing the language files
lang_dir = 'libs/lang/'

# Translations for "omb_desc": "A delightful community-driven framework for managing your bash configuration."
translations = {
    'am': "የባሽ ውቅርን ለማስተያየት የሚሆን እንግዳ የማህበረሰብ ምርጫ ፍሬምወርክ።",
    'ar': 'إطار عمل ممتع مدفوع بالمجتمع لإدارة تكوين bash الخاص بك.',
    'az': 'Bash konfiqurasiyanızı idarə etmək üçün xoşbəxt bir icma tərəfindən idarə olunan çərçivə.',
    'bg': 'Приятно рамка, управлявана от общността, за управление на вашата bash конфигурация.',
    'bn': 'আপনার ব্যাশ কনফিগারেশন পরিচালনা করার জন্য একটি আনন্দদায়ক সম্প্রদায়-চালিত ফ্রেমওয়ার্ক।',
    'bs': 'Zadovoljavajući okvir vođen zajednicom za upravljanje vašom bash konfiguracijom.',
    'cs': 'Rozkošný rámec řízený komunitou pro správu vaší konfigurace bash.',
    'da': 'En dejlig fællesskabsdrevet ramme til at administrere din bash-konfiguration.',
    'de': 'Ein entzückendes, gemeinschaftlich betriebenes Framework zur Verwaltung Ihrer Bash-Konfiguration.',
    'el': 'Ένα ευχάριστο πλαίσιο οδηγούμενο από την κοινότητα για τη διαχείριση της διαμόρφωσης bash σας.',
    'es': 'Un marco encantador impulsado por la comunidad para gestionar tu configuración de bash.',
    'et': 'Lõbus kogukonna juhitud raamistik teie bash-konfiguratsiooni haldamiseks.',
    'fa': 'یک چارچوب دلپذیر جامعه محور برای مدیریت پیکربندی bash شما.',
    'fi': 'Iloinen yhteisöohjattu kehys bash-konfiguraatiosi hallintaan.',
    'fr': 'Un cadre délicieux piloté par la communauté pour gérer votre configuration bash.',
    'ga': 'Creatlach aoibhinn tiomáinte ag an bpobal chun do chumraíocht bash a bhainistiú.',
    'he': 'מסגרת מהנה מונעת קהילה לניהול תצורת ה-bash שלך.',
    'hi': 'आपकी बैश कॉन्फ़िगरेशन को प्रबंधित करने के लिए एक आनंददायक समुदाय-संचालित ढांचा।',
    'hr': 'Zadovoljavajući okvir vođen zajednicom za upravljanje vašom bash konfiguracijom.',
    'hu': 'Egy elbűvölő, közösség által vezetett keretrendszer a bash konfigurációjának kezelésére.',
    'hy': 'Ձեր bash կոնֆիգուրացիան կառավարելու համար հաճելի համայնքով վարվող շրջանակ:',
    'id': 'Kerangka kerja yang menyenangkan yang didorong oleh komunitas untuk mengelola konfigurasi bash Anda.',
    'is': 'Gleðileg samfélagsstýrð rammi til að stjórna bash stillingum þínum.',
    'it': 'Un framework delizioso guidato dalla comunità per gestire la tua configurazione bash.',
    'ja': 'あなたの bash 設定を管理するための楽しいコミュニティ駆動型フレームワーク。',
    'ka': 'თქვენი bash კონფიგურაციის მართვისთვის სასიამოვნო საზოგადოებრივი ჩარჩო.',
    'km': 'ក្របខ័ណ្ឌដ៏រីករាយដែលគ្រប់គ្រងដោយសហគមន៍សម្រាប់គ្រប់គ្រងការកំណត់របស់ bash របស់អ្នក។',
    'ko': '귀하의 bash 구성을 관리하기 위한 유쾌한 커뮤니티 기반 프레임워크.',
    'lo': 'ເຟມເວີກທີ່ມ່ວນຊື່ນທີ່ຂັບເຄື່ອນໂດຍຊຸມຊົນເພື່ອຈັດການການຕັ້ງຄ່າ bash ຂອງທ່ານ.',
    'lt': 'Malonus bendruomenės valdomas karkasas jūsų bash konfigūracijai valdyti.',
    'lv': 'Jauks kopienas vadīts ietvars jūsu bash konfigurācijas pārvaldībai.',
    'mn': 'Таны bash тохиргоог удирдахад зориулсан сайхан нийгэмд тулгуурласан фрэймворк.',
    'ms': 'Rangka kerja yang menyenangkan yang dipacu oleh komuniti untuk menguruskan konfigurasi bash anda.',
    'my': 'သင့် bash ပြင်ဆင်မှုကို စီမံခန့်ခွဲရန် ပျော်ရွှင်ဖွယ်ရာ အသိုင်းအဝိုင်းက ဦးဆောင်သော မူဘောင်။',
    'nb': 'En herlig fellesskapsdrevet rammeverk for å administrere din bash-konfigurasjon.',
    'ne': 'तपाईको ब्यास कन्फिगरेसन व्यवस्थापन गर्नका लागि एक आनन्ददायक समुदाय-चालित फ्रेमवर्क।',
    'nl': 'Een heerlijk gemeenschapsgedreven raamwerk voor het beheren van uw bash-configuratie.',
    'pl': 'Zachwycająca struktura oparta na społeczności do zarządzania konfiguracją bash.',
    'pt': 'Uma estrutura encantadora orientada pela comunidade para gerenciar sua configuração bash.',
    'ro': 'Un cadru încântător condus de comunitate pentru gestionarea configurației bash.',
    'ru': 'Восхитительный фреймворк, управляемый сообществом, для управления вашей конфигурацией bash.',
    'sk': 'Rozkošný rámec riadený komunitou na správu vašej konfigurácie bash.',
    'sl': 'Prijeten okvir, ki ga vodi skupnost, za upravljanje vaše konfiguracije bash.',
    'sq': 'Një kornizë e këndshme e drejtuar nga komuniteti për të menaxhuar konfigurimin tuaj bash.',
    'sr': 'Zadovoljavajući okvir vođen zajednicom za upravljanje vašom bash konfiguracijom.',
    'sv': 'En underbar gemenskapsdriven ram för att hantera din bash-konfiguration.',
    'sw': 'Mfumo wa kufurahisha unaoendeshwa na jamii kwa kusimamia usanidi wako wa bash.',
    'ta': 'உங்கள் பாஷ் கட்டமைப்பை நிர்வகிப்பதற்கான ஒரு மகிழ்ச்சியான சமூகம்-இயக்கப்படும் கட்டமைப்பு.',
    'tg': 'Чорчубаи ҷолиб барои идоракунии танзимоти bash-и шумо.',
    'th': 'เฟรมเวิร์กที่ยอดเยี่ยมที่ขับเคลื่อนโดยชุมชนเพื่อจัดการการกำหนดค่า bash ของคุณ.',
    'tl': 'Isang kasiya-siyang balangkas na hinihimok ng komunidad para sa pamamahala ng iyong bash configuration.',
    'tr': 'Bash yapılandırmanızı yönetmek için hoş bir topluluk odaklı çerçeve.',
    'uk': 'Чудовий фреймворк, керований спільнотою, для управління вашою конфігурацією bash.',
    'ur': 'آپ کی باش کنفیگریشن کو منظم کرنے کے لیے ایک خوشگوار کمیونٹی ڈرائیون فریم ورک۔',
    'uz': 'Sizning bash konfiguratsiyangizni boshqarish uchun yoqimli jamoa tomonidan boshqariladigan ramka.',
    'vi': 'Một khung làm việc thú vị do cộng đồng điều khiển để quản lý cấu hình bash của bạn.',
    'zh': '一个令人愉快的社区驱动框架，用于管理您的 bash 配置。'
}

# Skip 'en' since it's already added
for lang, translation in translations.items():
    file_path = os.path.join(lang_dir, f'{lang}.json')
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        data['omb_desc'] = translation
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f'Added omb_desc to {lang}.json')
    else:
        print(f'File {file_path} does not exist')
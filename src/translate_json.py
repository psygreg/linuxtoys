import json
import os

# Directory containing the language files
lang_dir = '../p3/libs/lang/'

# Translations dictionary: key -> {lang_code: translation}
translations = {
    'resolvehw': {
        'am': 'DaVinci Resolve FFmpeg ፕላግኢን',
        'ar': 'DaVinci Resolve مكون FFmpeg إضافي',
        'az': 'DaVinci Resolve FFmpeg plaginin',
        'bg': 'DaVinci Resolve FFmpeg плъгин',
        'bn': 'DaVinci Resolve FFmpeg প্লাগইন',
        'bs': 'DaVinci Resolve FFmpeg plugin',
        'cs': 'DaVinci Resolve FFmpeg plugin',
        'da': 'DaVinci Resolve FFmpeg plugin',
        'de': 'DaVinci Resolve FFmpeg Plugin',
        'el': 'DaVinci Resolve FFmpeg plugin',
        'es': 'DaVinci Resolve complemento FFmpeg',
        'et': 'DaVinci Resolve FFmpeg plugin',
        'fa': 'DaVinci Resolve افزونه FFmpeg',
        'fi': 'DaVinci Resolve FFmpeg -liitännäinen',
        'fr': 'DaVinci Resolve plug-in FFmpeg',
        'ga': 'DaVinci Resolve breiseán FFmpeg',
        'he': 'DaVinci Resolve תוסף FFmpeg',
        'hi': 'DaVinci Resolve FFmpeg प्लगइन',
        'hr': 'DaVinci Resolve FFmpeg plugin',
        'hu': 'DaVinci Resolve FFmpeg plugin',
        'hy': 'DaVinci Resolve FFmpeg փլագին',
        'id': 'DaVinci Resolve plugin FFmpeg',
        'is': 'DaVinci Resolve FFmpeg viðbót',
        'it': 'DaVinci Resolve plugin FFmpeg',
        'ja': 'DaVinci Resolve FFmpeg プラグイン',
        'ka': 'DaVinci Resolve FFmpeg დანამატი',
        'km': 'DaVinci Resolve កម្មវិធីជំនួយ FFmpeg',
        'ko': 'DaVinci Resolve FFmpeg 플러그인',
        'lo': 'DaVinci Resolve ປລັກອິນ FFmpeg',
        'lt': 'DaVinci Resolve FFmpeg įskiepis',
        'lv': 'DaVinci Resolve FFmpeg spraudnis',
        'mn': 'DaVinci Resolve FFmpeg залгаас',
        'ms': 'DaVinci Resolve pemalam FFmpeg',
        'my': 'DaVinci Resolve FFmpeg ပလပ်အင်',
        'nb': 'DaVinci Resolve FFmpeg plugin',
        'ne': 'DaVinci Resolve FFmpeg प्लगइन',
        'nl': 'DaVinci Resolve FFmpeg plugin',
        'pl': 'DaVinci Resolve wtyczka FFmpeg',
        'pt': 'DaVinci Resolve plugin FFmpeg',
        'ro': 'DaVinci Resolve plugin FFmpeg',
        'ru': 'DaVinci Resolve плагин FFmpeg',
        'sk': 'DaVinci Resolve plugin FFmpeg',
        'sl': 'DaVinci Resolve vtičnik FFmpeg',
        'sq': 'DaVinci Resolve shtojcë FFmpeg',
        'sr': 'DaVinci Resolve FFmpeg додатак',
        'sv': 'DaVinci Resolve FFmpeg plugin',
        'sw': 'DaVinci Resolve programu-jalizi ya FFmpeg',
        'ta': 'DaVinci Resolve FFmpeg சொருகி',
        'tg': 'DaVinci Resolve плагини FFmpeg',
        'th': 'DaVinci Resolve โมดูลเสริม FFmpeg',
        'tl': 'DaVinci Resolve plugin ng FFmpeg',
        'tr': 'DaVinci Resolve FFmpeg eklentisi',
        'uk': 'DaVinci Resolve плагін FFmpeg',
        'ur': 'DaVinci Resolve FFmpeg پلگ ان',
        'uz': 'DaVinci Resolve FFmpeg plagini',
        'vi': 'DaVinci Resolve plugin FFmpeg',
        'zh': 'DaVinci Resolve FFmpeg 插件'
    },

    'resolvehw_desc': {
        'am': 'DaVinci Resolve ላይ Linux ላይ በ ffmpeg በኩል ለማስተላለፍ የሃርድዌር ተሽጋገር ቪዲዮ ኢንኮዲንግ ያስችላል፣ GPU ሰሪው ከሆነ ቢሆንም።',
        'ar': 'يُمكّن ترميز الفيديو المعجل بالأجهزة للتسليم في DaVinci Resolve على Linux من خلال ffmpeg، بغض النظر عن مصنع GPU.',
        'az': 'DaVinci Resolve-da Linux üzərində ffmpeg vasitəsilə çatdırılma üçün aparat sürətləndirilmiş video kodlaşdırmasını aktivləşdirir, GPU istehsalçısından asılı olmayaraq.',
        'bg': 'Активира хардуерно ускорено видео кодиране за доставка в DaVinci Resolve на Linux чрез ffmpeg, независимо от производителя на GPU.',
        'bn': 'DaVinci Resolve-এ Linux-এ ffmpeg-এর মাধ্যমে ডেলিভারির জন্য হার্ডওয়্যার-অ্যাক্সেলারেটেড ভিডিও এনকোডিং সক্ষম করে, GPU প্রস্তুতকারক নির্বিশেষে।',
        'bs': 'Omogućava hardverski ubrzano video kodiranje za isporuku u DaVinci Resolve na Linuxu putem ffmpeg-a, bez obzira na proizvođača GPU-a.',
        'cs': 'Povoluje hardwarově zrýchlené kódování videa pro doručení v DaVinci Resolve na Linuxu prostřednictvím ffmpeg, bez ohledu na výrobce GPU.',
        'da': 'Aktiverer hardware-accelereret video-kodning til levering i DaVinci Resolve på Linux gennem ffmpeg, uanset GPU-producent.',
        'de': 'Aktiviert hardwarebeschleunigte Video-Kodierung für die Auslieferung in DaVinci Resolve auf Linux durch ffmpeg, unabhängig vom GPU-Hersteller.',
        'el': 'Επιτρέπει την κωδικοποίηση βίντεο με επιτάχυνση υλικού για παράδοση στο DaVinci Resolve στο Linux μέσω ffmpeg, ανεξάρτητα από τον κατασκευαστή GPU.',
        'es': 'Habilita la codificación de video acelerada por hardware para la entrega en DaVinci Resolve en Linux a través de ffmpeg, independientemente del fabricante de GPU.',
        'et': 'Võimaldab riistvaraliselt kiirendatud video kodeerimise DaVinci Resolve\'is Linuxis ffmpeg\'i kaudu, sõltumata GPU tootjast.',
        'fa': 'رمزگذاری ویدیوی شتاب‌دهنده سخت‌افزاری را برای تحویل در DaVinci Resolve در Linux از طریق ffmpeg فعال می‌کند، صرف نظر از تولیدکننده GPU.',
        'fi': 'Ottaa käyttöön laitteistokiihdytetyn videokoodauksen toimitukseen DaVinci Resolve -ohjelmassa Linuxissa ffmpeg:n kautta, riippumatta GPU-valmistajasta.',
        'fr': 'test',
        'ga': 'Cumasaíonn \'sé ionchódú físeán luathaithe crua-earraí le \'haghaidh seachadta i DaVinci Resolve ar Linux trí ffmpeg, beag beann ar \'an monaróir GPU.',
        'he': 'מאפשר קידוד וידאו מואץ בחומרה למסירה ב\'-DaVinci Resolve ב\'-Linux דרך ffmpeg, ללא קשר ליצרן ה\'-GPU.',
        'hi': 'DaVinci Resolve में Linux पर ffmpeg के माध्यम से डिलीवरी के लिए हार्डवेयर-त्वरित वीडियो एन्कोडिंग सक्षम करता है, GPU निर्माता की परवाह किए बिना।',
        'hr': 'Omogućuje hardverski ubrzano video kodiranje za isporuku u DaVinci Resolve na Linuxu putem ffmpeg-a, bez obzira na proizvođača GPU-a.',
        'hu': 'Hardvérovo gyorsított videó kódolást tesz lehetővé a DaVinci Resolve-ban Linuxon keresztül ffmpeg-en, a GPU gyártójától függetlenül.',
        'hy': 'Միացնում է սարքավարության արագացված տեսախցիկի կոդավորումը DaVinci Resolve-ում Linux-ում ffmpeg-ի միջոցով, անկախ GPU արտադրողից:',
        'id': 'Mengaktifkan pengkodean video yang dipercepat perangkat keras untuk pengiriman di DaVinci Resolve di Linux melalui ffmpeg, terlepas dari produsen GPU.',
        'is': 'Virkjar vélbúnaðarhröðun myndskeiðakóðun fyrir afhendingu í DaVinci Resolve á Linux í gegnum ffmpeg, óháð GPU framleiðanda.',
        'it': 'Abilita la codifica video accelerata hardware per la consegna in DaVinci Resolve su Linux tramite ffmpeg, indipendentemente dal produttore GPU.',
        'ja': 'DaVinci Resolve で Linux 上の ffmpeg を通じて配信するためのハードウェアアクセラレーションされたビデオエンコーディングを有効にします。GPU メーカーを問わず。',
        'ka': 'აქტიურებს აპარატურულად აჩქარებულ ვიდეო კოდირებას DaVinci Resolve-ში Linux-ზე ffmpeg-ის საშუალებით, GPU მწარმოებელის მიუხედავად.',
        'km': 'បើកដំណើរការការអ៊ិនកូដវីដេអូដែលត្រូវបានបង្កើនល្បឿនដោយផ្នែករឹងសម្រាប់ការចែកចាយនៅក្នុង DaVinci Resolve នៅលើ Linux តាមរយៈ ffmpeg ដោយមិនគិតពីអ្នកផលិត GPU។',
        'ko': 'DaVinci Resolve에서 Linux의 ffmpeg를 통해 배달을 위한 하드웨어 가속 비디오 인코딩을 활성화합니다. GPU 제조업체에 관계없이.',
        'lo': 'ເປີດໃຊ້ການເຂົ້າລະຫັດວິດີໂອທີ່ໄດ້ຮັບການເລັ່ງຕໍ່ວັດຖຸຮາດແວສໍາລັບການຈັດສົ່ງໃນ DaVinci Resolve ເທິງ Linux ຜ່ານ ffmpeg, ໂດຍບໍ່ຄໍານึงເຖິງຜູ້ຜະລິດ GPU.',
        'lt': 'Įjungia aparatinę įrangą pagreitintą vaizdo kodavimą pristatymui DaVinci Resolve programoje Linux per ffmpeg, nepriklausomai nuo GPU gamintojo.',
        'lv': 'Iespējo aparatūrā paātrinātu video kodēšanu piegādei DaVinci Resolve programmā Linux, izmantojot ffmpeg, neatkarīgi no GPU ražotāja.',
        'mn': 'DaVinci Resolve-д Linux дээр ffmpeg-ээр дамжуулан хүргэхийн тулд тоног төхөөрөмжийн түргэвчилсэн видео кодчилолыг идэвхжүүлнэ, GPU үйлдвэрлэгчээс үл хамааран.',
        'ms': 'Membolehkan pengekodan video dipercepat perkakasan untuk penghantaran dalam DaVinci Resolve di Linux melalui ffmpeg, tanpa mengira pengeluar GPU.',
        'my': 'DaVinci Resolve တွင် Linux ပေါ်တွင် ffmpeg မှတစ်ဆင့် ပို့ဆောင်ရန်အတွက် ဟာ့ဒ်ဝဲလ်အရှိန်မြှင့် ဗီဒီယိုအင်ကုဒ်လုပ်ခြင်းကို ဖွင့်ပေးသည်၊ GPU ထုတ်လုပ်သူမည်သူဖြစ်စေ။',
        'nb': 'Aktiverer maskinvareakselerert videokoding for levering i DaVinci Resolve på Linux gjennom ffmpeg, uavhengig av GPU-produsent.',
        'ne': 'DaVinci Resolve मा Linux मा ffmpeg मार्फत डेलिभरीका लागि हार्डवेयर-एक्सेलेरेटेड भिडियो इनकोडिङ सक्षम गर्दछ, GPU निर्माताको परवाह नगरी।',
        'nl': 'Schakelt hardwareversnelde video-encoding in voor levering in DaVinci Resolve op Linux via ffmpeg, ongeacht de GPU-fabrikant.',
        'pl': 'Włącza sprzętowo przyspieszone kodowanie wideo do dostarczania w DaVinci Resolve na Linuxie przez ffmpeg, niezależnie od producenta GPU.',
        'pt': 'Habilita a codificação de vídeo acelerada por hardware para entrega no DaVinci Resolve no Linux através do ffmpeg, independentemente do fabricante da GPU.',
        'ro': 'Activează codificarea video accelerată hardware pentru livrare în DaVinci Resolve pe Linux prin ffmpeg, indiferent de producătorul GPU.',
        'ru': 'Включает аппаратно-ускоренное кодирование видео для доставки в DaVinci Resolve на Linux через ffmpeg, независимо от производителя GPU.',
        'sk': 'Povoľuje hardvérovo zrýchlené kódovanie videa na doručenie v DaVinci Resolve na Linuxe prostredníctvom ffmpeg, bez ohľadu na výrobcu GPU.',
        'sl': 'Omogoča strojno pospešeno kodiranje videa za dostavo v DaVinci Resolve na Linuxu prek ffmpeg, ne glede na proizvajalca GPU.',
        'sq': 'Aktivizon kodimin e videos së përshpejtuar nga hardueri për shpërndarje në DaVinci Resolve në Linux përmes ffmpeg, pavarësisht nga prodhuesi i GPU-së.',
        'sr': 'Омогућава хардверски убрзано видео кодирање за испоруку у DaVinci Resolve на Linux-у путем ffmpeg-а, без обзира на произвођача GPU-а.',
        'sv': 'Aktiverar hårdvaruaccelererad videokodning för leverans i DaVinci Resolve på Linux genom ffmpeg, oavsett GPU-tillverkare.',
        'sw': 'Huwezesha usimbaji fiche wa video uliohimiliwa na maunzi kwa utoaji katika DaVinci Resolve kwenye Linux kupitia ffmpeg, bila kujali mtengenezaji wa GPU.',
        'ta': 'DaVinci Resolve இல் Linux இல் ffmpeg மூலம் வழங்கலுக்கு வன்பொருள்-முடுக்கப்பட்ட வீடியோ குறியாக்கத்தை இயக்குகிறது, GPU உற்பத்தியாளரைப் பொருட்படுத்தாமல்.',
        'tg': 'Кодкунии видеоии суръатбахшидашудаи сахтафзорро барои интиқол дар DaVinci Resolve дар Linux тавассути ffmpeg фаъол мекунад, новобаста аз истеҳсолкунандаи GPU.',
        'th': 'เปิดใช้งานการเข้ารหัสวิดีโอที่เร่งด้วยฮาร์ดแวร์สำหรับการส่งมอบใน DaVinci Resolve บน Linux ผ่าน ffmpeg โดยไม่คำนึงถึงผู้ผลิต GPU',
        'tl': 'Nagbibigay-daan sa hardware-accelerated na video encoding para sa paghahatid sa DaVinci Resolve sa Linux sa pamamagitan ng ffmpeg, anuman ang tagagawa ng GPU.',
        'tr': 'DaVinci Resolve\'da Linux\'ta ffmpeg aracılığıyla teslimat için donanım hızlandırmalı video kodlamayı etkinleştirir, GPU üreticisinden bağımsız olarak.',
        'uk': 'Вмикає апаратно-прискорене кодування відео для доставки в DaVinci Resolve на Linux через ffmpeg, незалежно від виробника GPU.',
        'ur': 'DaVinci Resolve میں Linux پر ffmpeg کے ذریعے ڈیلیوری کے لیے ہارڈ ویئر ایکسلریٹڈ ویڈیو انکوڈنگ کو فعال کرتا ہے، GPU مینوفیکچرر سے قطع نظر۔',
        'uz': 'DaVinci Resolve-da Linux-da ffmpeg orqali yetkazish uchun apparat tezlatilgan video kodlashni yoqadi, GPU ishlab chiqaruvchisidan qat\'i nazar.',
        'vi': 'Kích hoạt mã hóa video được tăng tốc phần cứng để phân phối trong DaVinci Resolve trên Linux thông qua ffmpeg, bất kể nhà sản xuất GPU.',
        'zh': '在 Linux 上通过 ffmpeg 为 DaVinci Resolve 中的交付启用硬件加速视频编码，无论 GPU 制造商如何。'
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
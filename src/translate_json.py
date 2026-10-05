import json
import os

# Directory containing the language files
lang_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "p3/libs/lang/")

# Translations dictionary: key -> {lang_code: translation}
translations = {
"mtuprobe": {
    "am": "MTU Probingን አንቃ",
    "ar": "تمكين استكشاف MTU",
    "az": "MTU Probing-i aktiv et",
    "bg": "Активиране на MTU Probing",
    "bn": "MTU Probing সক্রিয় করুন",
    "bs": "Omogući MTU Probing",
    "cs": "Povolit MTU Probing",
    "da": "Aktivér MTU Probing",
    "de": "MTU Probing aktivieren",
    "el": "Ενεργοποίηση MTU Probing",
    "es": "Activar MTU Probing",
    "et": "Luba MTU Probing",
    "fa": "فعال‌سازی MTU Probing",
    "fi": "Ota MTU Probing käyttöön",
    "fr": "Activer MTU Probing",
    "ga": "Cumasaigh MTU Probing",
    "he": "הפעלת MTU Probing",
    "hi": "MTU Probing सक्षम करें",
    "hr": "Omogući MTU Probing",
    "hu": "MTU Probing engedélyezése",
    "hy": "Միացնել MTU Probing-ը",
    "id": "Aktifkan MTU Probing",
    "is": "Virkja MTU Probing",
    "it": "Abilita MTU Probing",
    "ja": "MTU Probing を有効にする",
    "ka": "MTU Probing-ის ჩართვა",
    "km": "បើក MTU Probing",
    "ko": "MTU Probing 활성화",
    "lo": "ເປີດໃຊ້ MTU Probing",
    "lt": "Įjungti MTU Probing",
    "lv": "Iespējot MTU Probing",
    "mn": "MTU Probing-г идэвхжүүлэх",
    "ms": "Dayakan MTU Probing",
    "my": "MTU Probing ကို ဖွင့်ရန်",
    "nb": "Aktiver MTU Probing",
    "ne": "MTU Probing सक्षम गर्नुहोस्",
    "nl": "MTU Probing inschakelen",
    "pl": "Włącz MTU Probing",
    "pt": "Ativar MTU Probing",
    "ro": "Activează MTU Probing",
    "ru": "Включить MTU Probing",
    "sk": "Povoliť MTU Probing",
    "sl": "Omogoči MTU Probing",
    "sq": "Aktivizo MTU Probing",
    "sr": "Омогући MTU Probing",
    "sv": "Aktivera MTU Probing",
    "sw": "Washa MTU Probing",
    "ta": "MTU Probing-ஐ இயக்கு",
    "tg": "MTU Probing-ро фаъол кардан",
    "th": "เปิดใช้งาน MTU Probing",
    "tl": "I-enable ang MTU Probing",
    "tr": "MTU Probing'i etkinleştir",
    "uk": "Увімкнути MTU Probing",
    "ur": "MTU Probing فعال کریں",
    "uz": "MTU Probing-ni yoqish",
    "vi": "Bật MTU Probing",
    "zh": "启用 MTU Probing"
},
"mtuprobe_desc": {
    "am": "MTU probing (Packetization Layer Path MTU Discovery) በኔትወርክ መንገድ ላይ ሳይከፋፈል ወይም ሳይጣል ሊጓዝ የሚችለውን ትልቁን የፓኬት መጠን ለማግኘት የሚያገለግል ራስ-ሰር የኔትወርክ ቴክኒክ ነው። ማንቃቱ በተለይ ከUbisoft ጨዋታዎች ጋር የሚከሰቱ አንዳንድ ችግሮችን ያስተካክላል።",
    "ar": "MTU probing ‏(Packetization Layer Path MTU Discovery) هي تقنية شبكات آلية تُستخدم للعثور على أكبر حجم للحزمة يمكنه الانتقال عبر مسار الشبكة دون تجزئة أو إسقاط. يؤدي تمكينها إلى إصلاح بعض المشكلات في الألعاب، خاصة ألعاب Ubisoft.",
    "az": "MTU probing (Packetization Layer Path MTU Discovery) şəbəkə yolu boyunca parçalanmadan və ya itirilmədən ötürülə bilən ən böyük paket ölçüsünü tapmaq üçün istifadə olunan avtomatlaşdırılmış şəbəkə texnikasıdır. Onun aktivləşdirilməsi oyunlarda, xüsusilə Ubisoft oyunlarında bəzi problemləri həll edir.",
    "bg": "MTU probing (Packetization Layer Path MTU Discovery) е автоматизирана мрежова техника за намиране на най-големия размер на пакет, който може да премине по мрежов път, без да бъде фрагментиран или отхвърлен. Активирането ѝ отстранява някои проблеми с игри, особено такива от Ubisoft.",
    "bn": "MTU probing (Packetization Layer Path MTU Discovery) হলো একটি স্বয়ংক্রিয় নেটওয়ার্কিং কৌশল, যা কোনো নেটওয়ার্ক পথে বিভক্ত বা বাদ না পড়ে যেতে পারে এমন সর্বোচ্চ প্যাকেটের আকার নির্ধারণ করে। এটি সক্রিয় করলে গেমের কিছু সমস্যা, বিশেষ করে Ubisoft-এর গেমগুলোর সমস্যা সমাধান হয়।",
    "bs": "MTU probing (Packetization Layer Path MTU Discovery) je automatizovana mrežna tehnika koja pronalazi najveću veličinu paketa koja može proći mrežnom putanjom bez fragmentiranja ili odbacivanja. Omogućavanje ove opcije rješava neke probleme s igrama, posebno Ubisoft igrama.",
    "cs": "MTU probing (Packetization Layer Path MTU Discovery) je automatizovaná síťová technika používaná ke zjištění největší velikosti paketu, který může projít síťovou cestou bez fragmentace nebo zahození. Její povolení řeší některé problémy s hrami, zejména od Ubisoftu.",
    "da": "MTU probing (Packetization Layer Path MTU Discovery) er en automatiseret netværksteknik, der bruges til at finde den største pakkestørrelse, som kan sendes gennem en netværkssti uden at blive fragmenteret eller droppet. Aktivering løser visse problemer med spil, især spil fra Ubisoft.",
    "de": "MTU Probing (Packetization Layer Path MTU Discovery) ist eine automatisierte Netzwerktechnik, mit der die größte Paketgröße ermittelt wird, die einen Netzwerkpfad passieren kann, ohne fragmentiert oder verworfen zu werden. Die Aktivierung behebt einige Probleme mit Spielen, insbesondere von Ubisoft.",
    "el": "Το MTU probing (Packetization Layer Path MTU Discovery) είναι μια αυτοματοποιημένη τεχνική δικτύωσης που χρησιμοποιείται για την εύρεση του μεγαλύτερου μεγέθους πακέτου που μπορεί να διασχίσει μια διαδρομή δικτύου χωρίς να κατακερματιστεί ή να απορριφθεί. Η ενεργοποίησή του διορθώνει ορισμένα προβλήματα με παιχνίδια, ιδιαίτερα της Ubisoft.",
    "es": "MTU probing (Packetization Layer Path MTU Discovery) es una técnica de red automatizada que se utiliza para encontrar el mayor tamaño de paquete que puede recorrer una ruta de red sin fragmentarse ni descartarse. Activarla soluciona algunos problemas con juegos, especialmente de Ubisoft.",
    "et": "MTU probing (Packetization Layer Path MTU Discovery) on automatiseeritud võrgutehnika, mida kasutatakse suurima paketisuuruse leidmiseks, mis saab läbida võrgutee ilma killustumise või kadumiseta. Selle lubamine lahendab mõningaid mängudega seotud probleeme, eriti Ubisofti mängudes.",
    "fa": "MTU probing ‏(Packetization Layer Path MTU Discovery) یک روش خودکار شبکه است که برای یافتن بزرگ‌ترین اندازه بسته‌ای استفاده می‌شود که می‌تواند بدون تکه‌تکه شدن یا حذف شدن از یک مسیر شبکه عبور کند. فعال کردن آن برخی مشکلات بازی‌ها، به‌ویژه بازی‌های Ubisoft، را برطرف می‌کند.",
    "fi": "MTU probing (Packetization Layer Path MTU Discovery) on automaattinen verkkotekniikka, jolla selvitetään suurin pakettikoko, joka voi kulkea verkkoreitin läpi pirstoutumatta tai putoamatta. Sen käyttöönotto korjaa joitakin pelien ongelmia, erityisesti Ubisoftin peleissä.",
    "fr": "MTU probing (Packetization Layer Path MTU Discovery) est une technique réseau automatisée permettant de déterminer la plus grande taille de paquet pouvant parcourir un chemin réseau sans être fragmenté ni abandonné. Son activation corrige certains problèmes avec les jeux, notamment ceux d’Ubisoft.",
    "ga": "Is teicníc líonraithe uathoibrithe é MTU probing (Packetization Layer Path MTU Discovery) a úsáidtear chun an méid paicéid is mó atá in ann taisteal thar chonair líonra gan a bheith ilroinnte ná caillte a aimsiú. Réitíonn a chumasú roinnt fadhbanna le cluichí, go háirithe cluichí ó Ubisoft.",
    "he": "MTU probing ‏(Packetization Layer Path MTU Discovery) היא טכניקת רשת אוטומטית המשמשת למציאת גודל החבילה המרבי שיכול לעבור בנתיב רשת מבלי להתפצל או להיזרק. הפעלתה פותרת בעיות מסוימות במשחקים, במיוחד במשחקים של Ubisoft.",
    "hi": "MTU probing (Packetization Layer Path MTU Discovery) एक स्वचालित नेटवर्किंग तकनीक है, जिसका उपयोग उस सबसे बड़े पैकेट आकार को खोजने के लिए किया जाता है जो बिना खंडित हुए या छोड़े गए नेटवर्क पथ से गुजर सकता है। इसे सक्षम करने से गेम से जुड़ी कुछ समस्याएँ, विशेष रूप से Ubisoft के गेम में, ठीक हो जाती हैं।",
    "hr": "MTU probing (Packetization Layer Path MTU Discovery) automatizirana je mrežna tehnika koja pronalazi najveću veličinu paketa koja može proći mrežnom putanjom bez fragmentiranja ili odbacivanja. Omogućavanje ove opcije rješava neke probleme s igrama, posebno Ubisoftovim igrama.",
    "hu": "Az MTU probing (Packetization Layer Path MTU Discovery) egy automatizált hálózati technika, amely meghatározza azt a legnagyobb csomagméretet, amely töredezés vagy eldobás nélkül képes végighaladni egy hálózati útvonalon. Engedélyezése megold bizonyos játékokkal kapcsolatos problémákat, különösen a Ubisoft játékainál.",
    "hy": "MTU probing-ը (Packetization Layer Path MTU Discovery) ավտոմատացված ցանցային տեխնիկա է, որն օգտագործվում է ցանցային ուղով առանց մասնատման կամ կորստի անցնող փաթեթի առավելագույն չափը գտնելու համար։ Այն միացնելը լուծում է խաղերի, հատկապես Ubisoft-ի խաղերի հետ կապված որոշ խնդիրներ։",
    "id": "MTU probing (Packetization Layer Path MTU Discovery) adalah teknik jaringan otomatis yang digunakan untuk menemukan ukuran paket terbesar yang dapat melewati jalur jaringan tanpa terfragmentasi atau dibuang. Mengaktifkannya memperbaiki beberapa masalah pada game, terutama game dari Ubisoft.",
    "is": "MTU probing (Packetization Layer Path MTU Discovery) er sjálfvirk nettækni sem er notuð til að finna stærstu pakkastærð sem getur farið um netslóð án þess að brotna upp eða falla niður. Virkjun þess lagar sum vandamál með leiki, sérstaklega leiki frá Ubisoft.",
    "it": "MTU probing (Packetization Layer Path MTU Discovery) è una tecnica di rete automatizzata utilizzata per individuare la dimensione massima dei pacchetti che può attraversare un percorso di rete senza essere frammentata o scartata. Abilitarla risolve alcuni problemi con i giochi, in particolare quelli di Ubisoft.",
    "ja": "MTU probing（Packetization Layer Path MTU Discovery）は、断片化や破棄を発生させずにネットワーク経路を通過できる最大のパケットサイズを検出する自動ネットワーク技術です。有効にすると、特に Ubisoft のゲームで発生する一部の問題を解決できます。",
    "ka": "MTU probing (Packetization Layer Path MTU Discovery) არის ავტომატიზებული ქსელური ტექნიკა, რომელიც გამოიყენება პაკეტის უდიდესი ზომის დასადგენად, რომელსაც შეუძლია ქსელურ მარშრუტზე გავლა ფრაგმენტაციის ან დაკარგვის გარეშე. მისი ჩართვა აგვარებს თამაშებთან დაკავშირებულ ზოგიერთ პრობლემას, განსაკუთრებით Ubisoft-ის თამაშებში.",
    "km": "MTU probing (Packetization Layer Path MTU Discovery) គឺជាបច្ចេកទេសបណ្តាញស្វ័យប្រវត្តិដែលប្រើដើម្បីស្វែងរកទំហំកញ្ចប់ធំបំផុតដែលអាចឆ្លងកាត់ផ្លូវបណ្តាញដោយមិនត្រូវបានបំបែក ឬបោះចោល។ ការបើកវាអាចដោះស្រាយបញ្ហាមួយចំនួនជាមួយហ្គេម ជាពិសេសហ្គេមពី Ubisoft។",
    "ko": "MTU probing(Packetization Layer Path MTU Discovery)은 네트워크 경로에서 조각화되거나 손실되지 않고 전송될 수 있는 가장 큰 패킷 크기를 찾는 자동화된 네트워크 기술입니다. 이를 활성화하면 특히 Ubisoft 게임에서 발생하는 일부 문제를 해결할 수 있습니다.",
    "lo": "MTU probing (Packetization Layer Path MTU Discovery) ແມ່ນເຕັກນິກເຄືອຂ່າຍອັດຕະໂນມັດທີ່ໃຊ້ຊອກຫາຂະໜາດແພັກເກດທີ່ໃຫຍ່ທີ່ສຸດທີ່ສາມາດເດີນທາງຜ່ານເສັ້ນທາງເຄືອຂ່າຍໂດຍບໍ່ຖືກແບ່ງ ຫຼື ຖືກຖິ້ມ. ການເປີດໃຊ້ຊ່ວຍແກ້ໄຂບາງບັນຫາກັບເກມ, ໂດຍສະເພາະເກມຈາກ Ubisoft.",
    "lt": "MTU probing (Packetization Layer Path MTU Discovery) yra automatizuotas tinklo metodas, naudojamas didžiausiam paketo dydžiui, galinčiam keliauti tinklo keliu be fragmentavimo ar atmetimo, nustatyti. Jo įjungimas išsprendžia kai kurias žaidimų problemas, ypač Ubisoft žaidimuose.",
    "lv": "MTU probing (Packetization Layer Path MTU Discovery) ir automatizēta tīkla metode, ko izmanto, lai noteiktu lielāko pakotnes izmēru, kas var šķērsot tīkla ceļu bez fragmentēšanas vai nomešanas. Tās iespējošana novērš dažas problēmas ar spēlēm, īpaši Ubisoft spēlēm.",
    "mn": "MTU probing (Packetization Layer Path MTU Discovery) нь сүлжээний замаар хуваагдах эсвэл хаягдахгүйгээр дамжих боломжтой хамгийн том пакетын хэмжээг олох автомат сүлжээний арга юм. Үүнийг идэвхжүүлснээр тоглоом, ялангуяа Ubisoft-ын тоглоомуудтай холбоотой зарим асуудлыг засдаг.",
    "ms": "MTU probing (Packetization Layer Path MTU Discovery) ialah teknik rangkaian automatik yang digunakan untuk mencari saiz paket terbesar yang boleh melalui laluan rangkaian tanpa dipecahkan atau digugurkan. Mendayakannya membaiki beberapa masalah dengan permainan, terutamanya permainan daripada Ubisoft.",
    "my": "MTU probing (Packetization Layer Path MTU Discovery) သည် network လမ်းကြောင်းတစ်လျှောက် fragment ဖြစ်ခြင်း သို့မဟုတ် drop ဖြစ်ခြင်းမရှိဘဲ ဖြတ်သန်းနိုင်သည့် အကြီးဆုံး packet size ကို ရှာဖွေရန် အသုံးပြုသော အလိုအလျောက် networking နည်းပညာဖြစ်သည်။ ၎င်းကို ဖွင့်ခြင်းဖြင့် အထူးသဖြင့် Ubisoft ဂိမ်းများတွင် ဖြစ်ပေါ်သော ပြဿနာအချို့ကို ဖြေရှင်းပေးနိုင်သည်။",
    "nb": "MTU probing (Packetization Layer Path MTU Discovery) er en automatisert nettverksteknikk som brukes til å finne den største pakkestørrelsen som kan sendes gjennom en nettverksbane uten å bli fragmentert eller droppet. Aktivering løser enkelte problemer med spill, spesielt spill fra Ubisoft.",
    "ne": "MTU probing (Packetization Layer Path MTU Discovery) एउटा स्वचालित नेटवर्किङ प्रविधि हो, जसले नेटवर्क मार्गमा खण्डित वा ड्रप नभई यात्रा गर्न सक्ने सबैभन्दा ठूलो प्याकेट आकार पत्ता लगाउँछ। यसलाई सक्षम गर्दा खेलहरूमा, विशेष गरी Ubisoft का खेलहरूमा, देखिने केही समस्याहरू समाधान हुन्छन्।",
    "nl": "MTU probing (Packetization Layer Path MTU Discovery) is een geautomatiseerde netwerktechniek waarmee de grootste pakketgrootte wordt bepaald die een netwerkpad kan doorlopen zonder te worden gefragmenteerd of gedropt. Het inschakelen hiervan verhelpt sommige problemen met games, met name die van Ubisoft.",
    "pl": "MTU probing (Packetization Layer Path MTU Discovery) to automatyczna technika sieciowa służąca do określania największego rozmiaru pakietu, który może przejść przez ścieżkę sieciową bez fragmentacji lub odrzucenia. Włączenie jej rozwiązuje niektóre problemy z grami, szczególnie firmy Ubisoft.",
    "pt": "MTU probing (Packetization Layer Path MTU Discovery) é uma técnica automatizada de rede usada para encontrar o maior tamanho de pacote que pode trafegar por uma rota de rede sem ser fragmentado ou descartado. Ativá-la corrige alguns problemas com jogos, especialmente os da Ubisoft.",
    "ro": "MTU probing (Packetization Layer Path MTU Discovery) este o tehnică automată de rețea utilizată pentru a găsi cea mai mare dimensiune a pachetului care poate traversa o rută de rețea fără a fi fragmentat sau eliminat. Activarea sa rezolvă unele probleme cu jocurile, în special cele de la Ubisoft.",
    "ru": "MTU probing (Packetization Layer Path MTU Discovery) — это автоматизированная сетевая технология для определения максимального размера пакета, который может пройти по сетевому маршруту без фрагментации или потери. Её включение устраняет некоторые проблемы с играми, особенно от Ubisoft.",
    "sk": "MTU probing (Packetization Layer Path MTU Discovery) je automatizovaná sieťová technika používaná na zistenie najväčšej veľkosti paketu, ktorý môže prejsť sieťovou cestou bez fragmentácie alebo zahodenia. Jej povolenie rieši niektoré problémy s hrami, najmä od Ubisoftu.",
    "sl": "MTU probing (Packetization Layer Path MTU Discovery) je samodejna omrežna tehnika za ugotavljanje največje velikosti paketa, ki lahko potuje po omrežni poti brez fragmentacije ali zavrženja. Omogočanje odpravi nekatere težave z igrami, zlasti Ubisoftovimi.",
    "sq": "MTU probing (Packetization Layer Path MTU Discovery) është një teknikë e automatizuar rrjeti që përdoret për të gjetur madhësinë më të madhe të paketës që mund të kalojë nëpër një rrugë rrjeti pa u fragmentuar ose hedhur. Aktivizimi i saj zgjidh disa probleme me lojërat, veçanërisht ato nga Ubisoft.",
    "sr": "MTU probing (Packetization Layer Path MTU Discovery) је аутоматизована мрежна техника која проналази највећу величину пакета која може проћи мрежном путањом без фрагментације или одбацивања. Омогућавање ове опције решава неке проблеме са играма, посебно Ubisoft играма.",
    "sv": "MTU probing (Packetization Layer Path MTU Discovery) är en automatiserad nätverksteknik som används för att hitta den största paketstorleken som kan färdas genom en nätverkssökväg utan att fragmenteras eller tappas. Aktivering åtgärdar vissa problem med spel, särskilt spel från Ubisoft.",
    "sw": "MTU probing (Packetization Layer Path MTU Discovery) ni mbinu ya mtandao ya kiotomatiki inayotumika kupata ukubwa mkubwa zaidi wa pakiti unaoweza kupita kwenye njia ya mtandao bila kugawanywa au kupotezwa. Kuiwasha hurekebisha baadhi ya matatizo ya michezo, hasa michezo kutoka Ubisoft.",
    "ta": "MTU probing (Packetization Layer Path MTU Discovery) என்பது ஒரு பிணையப் பாதையில் துண்டாக்கப்படாமலும் கைவிடப்படாமலும் செல்லக்கூடிய மிகப்பெரிய packet அளவைக் கண்டறியப் பயன்படும் தானியங்கி networking நுட்பமாகும். இதை இயக்குவது விளையாட்டுகளில், குறிப்பாக Ubisoft விளையாட்டுகளில் ஏற்படும் சில சிக்கல்களைச் சரிசெய்கிறது.",
    "tg": "MTU probing (Packetization Layer Path MTU Discovery) усули худкори шабакавӣ барои муайян кардани андозаи калонтарини бастаест, ки метавонад аз масири шабака бе тақсимшавӣ ё партофта шудан гузарад. Фаъол кардани он баъзе мушкилоти бозиҳо, махсусан бозиҳои Ubisoft-ро ҳал мекунад.",
    "th": "MTU probing (Packetization Layer Path MTU Discovery) เป็นเทคนิคเครือข่ายอัตโนมัติที่ใช้ค้นหาขนาดแพ็กเกจที่ใหญ่ที่สุดซึ่งสามารถเดินทางผ่านเส้นทางเครือข่ายได้โดยไม่ถูกแบ่งส่วนหรือทิ้ง การเปิดใช้งานช่วยแก้ปัญหาบางอย่างกับเกม โดยเฉพาะเกมจาก Ubisoft",
    "tl": "Ang MTU probing (Packetization Layer Path MTU Discovery) ay isang awtomatikong networking technique na ginagamit upang mahanap ang pinakamalaking packet size na maaaring dumaan sa isang network path nang hindi naha-fragment o nada-drop. Ang pag-enable nito ay nag-aayos ng ilang problema sa mga laro, lalo na sa mga laro mula sa Ubisoft.",
    "tr": "MTU probing (Packetization Layer Path MTU Discovery), bir ağ yolu boyunca parçalanmadan veya düşürülmeden iletilebilecek en büyük paket boyutunu bulmak için kullanılan otomatik bir ağ tekniğidir. Etkinleştirilmesi, özellikle Ubisoft oyunlarında görülen bazı sorunları giderir.",
    "uk": "MTU probing (Packetization Layer Path MTU Discovery) — це автоматизована мережева технологія для визначення найбільшого розміру пакета, який може пройти мережевим маршрутом без фрагментації або втрати. Її ввімкнення усуває деякі проблеми з іграми, особливо від Ubisoft.",
    "ur": "MTU probing ‏(Packetization Layer Path MTU Discovery) ایک خودکار نیٹ ورکنگ تکنیک ہے جو اس سب سے بڑے پیکیٹ سائز کا تعین کرتی ہے جو کسی نیٹ ورک راستے سے بغیر تقسیم یا ضائع ہوئے گزر سکتا ہے۔ اسے فعال کرنے سے گیمز، خاص طور پر Ubisoft کی گیمز، کے کچھ مسائل حل ہوتے ہیں۔",
    "uz": "MTU probing (Packetization Layer Path MTU Discovery) tarmoq yo'li bo'ylab qismlarga ajratilmasdan yoki tashlab yuborilmasdan o'tishi mumkin bo'lgan eng katta paket hajmini aniqlash uchun ishlatiladigan avtomatlashtirilgan tarmoq usulidir. Uni yoqish o'yinlar, ayniqsa Ubisoft o'yinlari bilan bog'liq ayrim muammolarni hal qiladi.",
    "vi": "MTU probing (Packetization Layer Path MTU Discovery) là kỹ thuật mạng tự động dùng để tìm kích thước gói lớn nhất có thể đi qua một đường mạng mà không bị phân mảnh hoặc loại bỏ. Việc bật tính năng này khắc phục một số sự cố với trò chơi, đặc biệt là các trò chơi của Ubisoft.",
    "zh": "MTU probing（Packetization Layer Path MTU Discovery）是一种自动化网络技术，用于查找能够通过网络路径而不被分片或丢弃的最大数据包大小。启用它可以解决一些游戏问题，尤其是 Ubisoft 游戏的问题。"
}
}

# Skip 'en' since it's already added
for key, lang_translations in translations.items():
    for lang, translation in lang_translations.items():
        file_path = os.path.join(lang_dir, f"{lang}.json")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data[key] = translation
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Added {key} to {lang}.json")
        else:
            print(f"File {file_path} does not exist")

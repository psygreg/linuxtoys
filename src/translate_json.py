import json
import os

# Directory containing the language files
lang_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "p3/libs/lang/")

# Translations dictionary: key -> {lang_code: translation}
translations = {
    "app_page_screenshot_zoom_hint": {
        "am": "ለመመለስ ጠቅ ያድርጉ ወይም Escን ይጫኑ",
        "ar": "انقر أو اضغط على Esc للعودة",
        "az": "Geri qayıtmaq üçün klikləyin və ya Esc düyməsini basın",
        "bg": "Щракнете или натиснете Esc, за да се върнете",
        "bn": "ফিরে যেতে ক্লিক করুন বা Esc চাপুন",
        "bs": "Kliknite ili pritisnite Esc za povratak",
        "cs": "Kliknutím nebo stisknutím Esc se vrátíte",
        "da": "Klik eller tryk på Esc for at gå tilbage",
        "de": "Klicken oder Esc drücken, um zurückzukehren",
        "el": "Κάντε κλικ ή πατήστε Esc για επιστροφή",
        "es": "Haz clic o pulsa Esc para volver",
        "et": "Tagasipöördumiseks klõpsake või vajutage Esc",
        "fa": "برای بازگشت کلیک کنید یا Esc را فشار دهید",
        "fi": "Palaa napsauttamalla tai painamalla Esc",
        "fr": "Cliquez ou appuyez sur Échap pour revenir",
        "ga": "Cliceáil nó brúigh Esc chun filleadh",
        "he": "לחצו או הקישו על Esc כדי לחזור",
        "hi": "वापस जाने के लिए क्लिक करें या Esc दबाएँ",
        "hr": "Kliknite ili pritisnite Esc za povratak",
        "hu": "Kattintson vagy nyomja meg az Esc billentyűt a visszatéréshez",
        "hy": "Վերադառնալու համար սեղմեք կամ սեղմեք Esc",
        "id": "Klik atau tekan Esc untuk kembali",
        "is": "Smelltu eða ýttu á Esc til að fara til baka",
        "it": "Fai clic o premi Esc per tornare indietro",
        "ja": "クリックするか Esc キーを押して戻ります",
        "ka": "დასაბრუნებლად დააწკაპუნეთ ან დააჭირეთ Esc-ს",
        "km": "ចុច ឬចុចគ្រាប់ចុច Esc ដើម្បីត្រឡប់",
        "ko": "돌아가려면 클릭하거나 Esc 키를 누르세요",
        "lo": "ຄລິກ ຫຼື ກົດ Esc ເພື່ອກັບຄືນ",
        "lt": "Spustelėkite arba paspauskite Esc, kad grįžtumėte",
        "lv": "Noklikšķiniet vai nospiediet Esc, lai atgrieztos",
        "mn": "Буцахын тулд товших эсвэл Esc дарна уу",
        "ms": "Klik atau tekan Esc untuk kembali",
        "my": "ပြန်သွားရန် နှိပ်ပါ သို့မဟုတ် Esc ကို နှိပ်ပါ",
        "nb": "Klikk eller trykk Esc for å gå tilbake",
        "ne": "फर्कन क्लिक गर्नुहोस् वा Esc थिच्नुहोस्",
        "nl": "Klik of druk op Esc om terug te gaan",
        "pl": "Kliknij lub naciśnij Esc, aby wrócić",
        "pt": "Clique ou pressione Esc para voltar",
        "ro": "Faceți clic sau apăsați Esc pentru a reveni",
        "ru": "Нажмите мышью или клавишу Esc, чтобы вернуться",
        "sk": "Kliknutím alebo stlačením Esc sa vrátite",
        "sl": "Kliknite ali pritisnite Esc za vrnitev",
        "sq": "Klikoni ose shtypni Esc për t'u kthyer",
        "sr": "Кликните или притисните Esc за повратак",
        "sv": "Klicka eller tryck på Esc för att gå tillbaka",
        "sw": "Bofya au bonyeza Esc ili kurudi",
        "ta": "திரும்புவதற்கு கிளிக் செய்யவும் அல்லது Esc-ஐ அழுத்தவும்",
        "tg": "Барои бозгашт клик кунед ё Esc-ро пахш кунед",
        "th": "คลิกหรือกด Esc เพื่อกลับ",
        "tl": "Mag-click o pindutin ang Esc para bumalik",
        "tr": "Geri dönmek için tıklayın veya Esc tuşuna basın",
        "uk": "Клацніть або натисніть Esc, щоб повернутися",
        "ur": "واپس جانے کے لیے کلک کریں یا Esc دبائیں",
        "uz": "Qaytish uchun bosing yoki Esc tugmasini bosing",
        "vi": "Nhấp hoặc nhấn Esc để quay lại",
        "zh": "点击或按 Esc 返回"
    },
    "app_page_screenshot_zoom": {
        "am": "ለማጉላት ጠቅ ያድርጉ",
        "ar": "انقر للتكبير",
        "az": "Böyütmək üçün klikləyin",
        "bg": "Щракнете за увеличаване",
        "bn": "জুম করতে ক্লিক করুন",
        "bs": "Kliknite za uvećanje",
        "cs": "Kliknutím zvětšíte",
        "da": "Klik for at zoome",
        "de": "Zum Vergrößern klicken",
        "el": "Κάντε κλικ για μεγέθυνση",
        "es": "Haz clic para ampliar",
        "et": "Suurendamiseks klõpsake",
        "fa": "برای بزرگ‌نمایی کلیک کنید",
        "fi": "Napsauta suurentaaksesi",
        "fr": "Cliquez pour agrandir",
        "ga": "Cliceáil chun zúmáil",
        "he": "לחצו להגדלה",
        "hi": "ज़ूम करने के लिए क्लिक करें",
        "hr": "Kliknite za uvećanje",
        "hu": "Kattintson a nagyításhoz",
        "hy": "Սեղմեք՝ մեծացնելու համար",
        "id": "Klik untuk memperbesar",
        "is": "Smelltu til að stækka",
        "it": "Fai clic per ingrandire",
        "ja": "クリックして拡大",
        "ka": "გასადიდებლად დააწკაპუნეთ",
        "km": "ចុចដើម្បីពង្រីក",
        "ko": "클릭하여 확대",
        "lo": "ຄລິກເພື່ອຂະຫຍາຍ",
        "lt": "Spustelėkite, kad padidintumėte",
        "lv": "Noklikšķiniet, lai palielinātu",
        "mn": "Томруулахын тулд товшино уу",
        "ms": "Klik untuk zum",
        "my": "ချဲ့ကြည့်ရန် နှိပ်ပါ",
        "nb": "Klikk for å zoome",
        "ne": "जुम गर्न क्लिक गर्नुहोस्",
        "nl": "Klik om te vergroten",
        "pl": "Kliknij, aby powiększyć",
        "pt": "Clique para ampliar",
        "ro": "Faceți clic pentru mărire",
        "ru": "Нажмите для увеличения",
        "sk": "Kliknutím zväčšíte",
        "sl": "Kliknite za povečavo",
        "sq": "Klikoni për të zmadhuar",
        "sr": "Кликните за увећање",
        "sv": "Klicka för att zooma",
        "sw": "Bofya ili kukuza",
        "ta": "பெரிதாக்க கிளிக் செய்யவும்",
        "tg": "Барои калон кардан клик кунед",
        "th": "คลิกเพื่อขยาย",
        "tl": "Mag-click para mag-zoom",
        "tr": "Yakınlaştırmak için tıklayın",
        "uk": "Клацніть, щоб збільшити",
        "ur": "زوم کرنے کے لیے کلک کریں",
        "uz": "Kattalashtirish uchun bosing",
        "vi": "Nhấp để phóng to",
        "zh": "点击放大"
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

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
        'sysup_starting': 'sysup_starting="-------- ሙሉ ሲስተም ማዘመን ጀምሮ --------"',
        'sysup_completed': 'sysup_completed="ማስተካከል እና ማዘመን ተጠናቋል።"',
        'sysup_rebootreq': 'sysup_rebootreq="ማስተካከል እና ማዘመን ተጠናቋል። ማዘመኖቱ ንጽህና ውስጥ ለመግባት እንደገና ተጀምሮ ሊሆን ይችላል።"',
        'zswapmsg': 'zswapmsg="ZSWAP ሁን ነው ነው ታቅዷል።"',
        'msgostreepending': 'msgostreepending="የስርዓት ማስተካከል በመጠባበቅ ላይ ነው። እባክዎ ስርዓትዎን እንደገና ያስጀምሩ እና ተከታታይ ስክሪፕትን ለማጠናቀቅ ይህን ስክሪፕት ወደገና ያስሮታል።"'
    },
    'ar.lib': {
        'sysup_starting': 'sysup_starting="-------- تحديث النظام الكامل بدء --------"',
        'sysup_completed': 'sysup_completed="التنظيف والتحديث مكتملان."',
        'sysup_rebootreq': 'sysup_rebootreq="التنظيف والتحديث مكتملان. إعادة تشغيل مطلوبة لتفعيل التحديث."',
        'zswapmsg': 'zswapmsg="تم تمكين ZSWAP الآن. لاستخدامه، يجب عليك إنشاء ملف مبادلة أو قسم."',
        'msgostreepending': 'msgostreepending="تحديث نظام معلق. يرجى إعادة تشغيل نظامك وتشغيل هذا السكريبت مرة أخرى لإكمال التثبيت."'
    },
    'az.lib': {
        'sysup_starting': 'sysup_starting="-------- TAM SİSTEM YENİLƏMƏSİ BAŞLADIQLARI --------"',
        'sysup_completed': 'sysup_completed="Təmizlənmə və güncəllənmə tamamlandı."',
        'sysup_rebootreq': 'sysup_rebootreq="Təmizlənmə və güncəllənmə tamamlandı. Güncəllənmənin səmərəli olması üçün yenidən başladılması tələb olunur."',
        'zswapmsg': 'zswapmsg="ZSWAP indi aktivdir. Bunu istifadə etmək üçün swap faylı yaratmalısınız."',
        'msgostreepending': 'msgostreepending="Sistem yeniləməsi gözləyişdədir. Sistemin yenidən başladılması istəyindən sonra yükləməni tamamlamaq üçün bu skripti yenidən çalıştırın."'
    },
    'bg.lib': {
        'sysup_starting': 'sysup_starting="-------- ПЪЛНО СИСТЕМНО ОБНОВЯВАНЕ СТАРТИРАНО --------"',
        'sysup_completed': 'sysup_completed="Почистване и актуализация завършени."',
        'sysup_rebootreq': 'sysup_rebootreq="Почистване и актуализация завършени. Необходимо е рестартиране, за да влезе обновката в сила."',
        'zswapmsg': 'zswapmsg="ZSWAP е сега активиран. Трябва да създадете swap файл или дял."',
        'msgostreepending': 'msgostreepending="Системното актуализиране чака. Моля, рестартирайте системата си и стартирайте този скрипт отново, за да завършите инсталацията."'
    },
    'bn.lib': {
        'sysup_starting': 'sysup_starting="-------- সম্পূর্ণ সিস্টেম আপডেট শুরু হয়েছে --------"',
        'sysup_completed': 'sysup_completed="পরিষ্কার এবং আপডেট সম্পূর্ণ।"',
        'sysup_rebootreq': 'sysup_rebootreq="পরিষ্কার এবং আপডেট সম্পূর্ণ। আপডেটটি কার্যকর হতে একটি পুনর্বুট প্রয়োজন।"',
        'zswapmsg': 'zswapmsg="ZSWAP এখন সক্ষম করা হয়েছে। আপনার একটি স্বাপ ফাইল বা বিভাজন তৈরি করতে হবে।"',
        'msgostreepending': 'msgostreepending="একটি সিস্টেম আপডেট অপেক্ষা করছে। অনুগ্রহ করে আপনার সিস্টেম পুনরায় চালু করুন এবং ইনস্টলেশন সম্পূর্ণ করতে এই স্ক্রিপটি আবার চালান।"'
    },
    'bs.lib': {
        'sysup_starting': 'sysup_starting="-------- PUNO AŽURIRANJE SISTEMA ZAPOČETO --------"',
        'sysup_completed': 'sysup_completed="Čišćenje i ažuriranje dovršeni."',
        'sysup_rebootreq': 'sysup_rebootreq="Čišćenje i ažuriranje dovršeni. Potreban je restart kako bi ažuriranje stupio na snagu."',
        'zswapmsg': 'zswapmsg="ZSWAP je sada omogućen. Morate kreirati datoteku razmjene ili particiju."',
        'msgostreepending': 'msgostreepending="Ažuriranje sistema je u čekanju. Molimo, ponovno pokrenite sistem i ponovo pokrenite ovaj skript da biste dovršili instalaciju."'
    },
    'cs.lib': {
        'sysup_starting': 'sysup_starting="-------- SPUŠTĚNA ÚPLNÁ AKTUALIZACE SYSTÉMU --------"',
        'sysup_completed': 'sysup_completed="Vyčištění a aktualizace dokončeny."',
        'sysup_rebootreq': 'sysup_rebootreq="Vyčištění a aktualizace dokončeny. Pro použití aktualizace je vyžadován restart."',
        'zswapmsg': 'zswapmsg="ZSWAP je nyní povolen. Musíte vytvořit soubor podkačky nebo oddíl."',
        'msgostreepending': 'msgostreepending="Čeká se na aktualizaci systému. Restartujte prosím svůj systém a spusťte znovu tento skript, abyste dokončili instalaci."'
    },
    'da.lib': {
        'sysup_starting': 'sysup_starting="-------- FULD SYSTEMOPDATERING STARTER --------"',
        'sysup_completed': 'sysup_completed="Rengøring og opdatering afsluttet."',
        'sysup_rebootreq': 'sysup_rebootreq="Rengøring og opdatering afsluttet. En genstart er påkrævet for, at opdateringen træder i kraft."',
        'zswapmsg': 'zswapmsg="ZSWAP er nu aktiveret. Du skal oprette en swap-fil eller partition."',
        'msgostreepending': 'msgostreepending="En systemopdatering afventer. Genstart venligst dit system og kør dette script igen for at fuldføre installationen."'
    },
    'de.lib': {
        'sysup_starting': 'sysup_starting="-------- VOLLSTÄNDIGE SYSTEMAKTUALISIERUNG GESTARTET --------"',
        'sysup_completed': 'sysup_completed="Bereinigung und Aktualisierung abgeschlossen."',
        'sysup_rebootreq': 'sysup_rebootreq="Bereinigung und Aktualisierung abgeschlossen. Ein Neustart ist erforderlich, damit die Aktualisierung in Kraft tritt."',
        'zswapmsg': 'zswapmsg="ZSWAP ist nun aktiviert. Sie müssen eine Auslagerungsdatei oder Partition erstellen."',
        'msgostreepending': 'msgostreepending="Eine Systemaktualisierung ist ausstehend. Bitte starten Sie Ihr System neu und führen Sie dieses Skript erneut aus, um die Installation abzuschließen."'
    },
    'el.lib': {
        'sysup_starting': 'sysup_starting="-------- ΠΛΉΡΗΣ ΕΝΗΜΈΡΩΣΗ ΣΥΣΤΉΜΑΤΟΣ ΞΕΚΙΝΆ --------"',
        'sysup_completed': 'sysup_completed="Ο καθαρισμός και η ενημέρωση ολοκληρώθηκαν."',
        'sysup_rebootreq': 'sysup_rebootreq="Ο καθαρισμός και η ενημέρωση ολοκληρώθηκαν. Απαιτείται επανεκκίνηση για να ισχύσει η ενημέρωση."',
        'zswapmsg': 'zswapmsg="Το ZSWAP είναι τώρα ενεργοποιημένο. Πρέπει να δημιουργήσετε ένα αρχείο ή διαμέρισμα ανταλλαγής."',
        'msgostreepending': 'msgostreepending="Μια ενημέρωση συστήματος εκκρεμεί. Παρακαλώ επανεκκινήστε το σύστημά σας και εκτελέστε ξανά αυτό το σενάριο για να ολοκληρώσετε την εγκατάσταση."'
    },
    'es.lib': {
        'sysup_starting': 'sysup_starting="-------- ACTUALIZACIÓN COMPLETA DEL SISTEMA INICIADA --------"',
        'sysup_completed': 'sysup_completed="Limpieza y actualización completadas."',
        'sysup_rebootreq': 'sysup_rebootreq="Limpieza y actualización completadas. Se requiere un reinicio para que la actualización surta efecto."',
        'zswapmsg': 'zswapmsg="ZSWAP está ahora habilitado. Debes crear un archivo o partición de intercambio."',
        'msgostreepending': 'msgostreepending="Una actualización del sistema está pendiente. Por favor, reinicia tu sistema y ejecuta este script nuevamente para completar la instalación."'
    },
    'et.lib': {
        'sysup_starting': 'sysup_starting="-------- TÄIELIK SÜSTEEMI VÄRSKENDUS ALUSTATUD --------"',
        'sysup_completed': 'sysup_completed="Puhastamine ja värskendamine lõpule viidud."',
        'sysup_rebootreq': 'sysup_rebootreq="Puhastamine ja värskendamine lõpule viidud. Värskenduse rakendamiseks on vajalik taaskäivitamine."',
        'zswapmsg': 'zswapmsg="ZSWAP on nüüd lubatud. Peate looma swap-faili või jaotuse."',
        'msgostreepending': 'msgostreepending="Süsteemi uuendamine ootel. Palun taaskäivitage oma süsteem ja käivitage see skript uuesti, et paigaldamine lõpule viia."'
    },
    'fa.lib': {
        'sysup_starting': 'sysup_starting="-------- بروزرسانی کامل سیستم آغاز شد --------"',
        'sysup_completed': 'sysup_completed="تمیز کردن و بروزرسانی کامل شد."',
        'sysup_rebootreq': 'sysup_rebootreq="تمیز کردن و بروزرسانی کامل شد. برای اعمال بروزرسانی نیاز به راه اندازی مجدد است."',
        'zswapmsg': 'zswapmsg="ZSWAP اکنون فعال شده است. شما باید یک فایل یا پارتیشن سوئپ ایجاد کنید."',
        'msgostreepending': 'msgostreepending="یک بروزرسانی سیستم در انتظار است. لطفاً سیستم خود را مجدداً راه اندازی کنید و این اسکریپت را دوباره اجرا کنید تا نصب کامل شود."'
    },
    'fi.lib': {
        'sysup_starting': 'sysup_starting="-------- TÄYSI JÄRJESTELMÄN PÄIVITYS KÄYNNISTETTY --------"',
        'sysup_completed': 'sysup_completed="Siivous ja päivitys valmis."',
        'sysup_rebootreq': 'sysup_rebootreq="Siivous ja päivitys valmis. Päivityksen voimaantuloa varten vaaditaan uudelleenkäynnistys."',
        'zswapmsg': 'zswapmsg="ZSWAP on nyt otettu käyttöön. Sinun on luotava swap-tiedosto tai osio."',
        'msgostreepending': 'msgostreepending="Järjestelmäpäivitys on vireillä. Käynnistä järjestelmä uudelleen ja suorita tämä skripti uudelleen asennuksen loppuunsaattamiseksi."'
    },
    'fr.lib': {
        'sysup_starting': 'sysup_starting="-------- MISE À JOUR COMPLÈTE DU SYSTÈME DÉMARRÉE --------"',
        'sysup_completed': 'sysup_completed="Nettoyage et mise à jour terminés."',
        'sysup_rebootreq': 'sysup_rebootreq="Nettoyage et mise à jour terminés. Un redémarrage est requis pour que la mise à jour prenne effet."',
        'zswapmsg': 'zswapmsg="ZSWAP est maintenant activé. Vous devez créer un fichier ou une partition d\'échange."',
        'msgostreepending': 'msgostreepending="Une mise à jour système est en attente. Veuillez redémarrer votre système et relancer ce script pour terminer l\'installation."'
    },
    'ga.lib': {
        'sysup_starting': 'sysup_starting="-------- NUASHONRÚ IOMLÁN CÓRAS TOSAITHE --------"',
        'sysup_completed': 'sysup_completed="Glanúchán agus nuashonrú críochnaithe."',
        'sysup_rebootreq': 'sysup_rebootreq="Glanúchán agus nuashonrú críochnaithe. Tá atosú ag teastáil chun an nuashonrú a chur i bhfeidhm."',
        'zswapmsg': 'zswapmsg="Tá ZSWAP gníomhachtaithe anois. Ní mór duit comhad babhtála a chruthú."',
        'msgostreepending': 'msgostreepending="Tá nuashonrú córais i bhfeidhm. Atosaigh do chóras le do thoil agus rith an script seo arís chun an fhéadachas a bhaint amach."'
    },
    'he.lib': {
        'sysup_starting': 'sysup_starting="-------- עדכון מערכת מלא החל --------"',
        'sysup_completed': 'sysup_completed="ניקוי ועדכון הושלמו."',
        'sysup_rebootreq': 'sysup_rebootreq="ניקוי ועדכון הושלמו. נדרש אתחול מחדש כדי שהעדכון יכנס לתוקף."',
        'zswapmsg': 'zswapmsg="ZSWAP מופעל כעת. עליך ליצור קובץ החלפה או מחיצה."',
        'msgostreepending': 'msgostreepending="עדכון מערכת ממתין. אנא הפעל מחדש את המערכת שלך והפעל את הסקריפט הזה שוב כדי להשלים את ההתקנה."'
    },
    'hi.lib': {
        'sysup_starting': 'sysup_starting="-------- संपूर्ण सिस्टम अपडेट शुरू --------"',
        'sysup_completed': 'sysup_completed="सफाई और अपडेट पूर्ण।"',
        'sysup_rebootreq': 'sysup_rebootreq="सफाई और अपडेट पूर्ण। अपडेट लागू होने के लिए पुनः बूट की आवश्यकता है।"',
        'zswapmsg': 'zswapmsg="ZSWAP अब सक्षम है। आपको एक स्वैप फाइल या विभाजन बनाना होगा।"',
        'msgostreepending': 'msgostreepending="एक सिस्टम अपडेट लंबित है। कृपया अपनी प्रणाली को पुनः आरंभ करें और स्थापन पूर्ण करने के लिए इस स्क्रिप्ट को फिर से चलाएं।"'
    },
    'hr.lib': {
        'sysup_starting': 'sysup_starting="-------- PUNE AŽURIRANJE SISTEMA POČETO --------"',
        'sysup_completed': 'sysup_completed="Čišćenje i ažuriranje dovršeni."',
        'sysup_rebootreq': 'sysup_rebootreq="Čišćenje i ažuriranje dovršeni. Potreban je restart kako bi ažuriranje stupio na snagu."',
        'zswapmsg': 'zswapmsg="ZSWAP je sada omogućen. Morate kreirati datoteku ili particiju razmjene."',
        'msgostreepending': 'msgostreepending="Ažuriranje sistema čeka. Molim vas, ponovno pokrenite sustav i ponovno pokrenite ovaj skript kako biste dovršili instalaciju."'
    },
    'hu.lib': {
        'sysup_starting': 'sysup_starting="-------- TELJES RENDSZERFRISSÍTÉS ELINDÍTVA --------"',
        'sysup_completed': 'sysup_completed="Megtisztítás és frissítés befejezve."',
        'sysup_rebootreq': 'sysup_rebootreq="Megtisztítás és frissítés befejezve. A frissítés érvénybe lépéséhez újraindítás szükséges."',
        'zswapmsg': 'zswapmsg="A ZSWAP most engedélyezett. Létre kell hoznia egy swap-fájlt vagy partíciót."',
        'msgostreepending': 'msgostreepending="A rendszerfrissítés függőben van. Indítsa újra a rendszert, és futtassa újra ezt a parancsfájlt a telepítés befejezéséhez."'
    },
    'hy.lib': {
        'sysup_starting': 'sysup_starting="-------- ԱՄԲՈՂՋԱԿԱՆ ՀԱՄԱԿԱՐԳԻ ԹԱՐՄԱՑՈՒՄ ՍԿՍՎԵԼ --------"',
        'sysup_completed': 'sysup_completed="Մաքրում և թարմացում ավարտված։"',
        'sysup_rebootreq': 'sysup_rebootreq="Մաքրում և թարմացում ավարտված։ Թարմացումը ուժի մեջ մտնելու համար անհրաժեշտ է վերաբեռնում։"',
        'zswapmsg': 'zswapmsg="ZSWAP-ը այժմ միացված է։ Դուք պետք է ստեղծեք փոխանակման ֆայլ կամ բաժին։"',
        'msgostreepending': 'msgostreepending="Համակարգի թարմացումը սպասում է։ Խնդրում ենք վերսկսել ձեր համակարգը և հետևել այս սկրիպտը վերսկսել՝ տեղակայումը ավարտելու համար։"'
    },
    'id.lib': {
        'sysup_starting': 'sysup_starting="-------- PEMBARUAN SISTEM LENGKAP DIMULAI --------"',
        'sysup_completed': 'sysup_completed="Pembersihan dan pembaruan selesai."',
        'sysup_rebootreq': 'sysup_rebootreq="Pembersihan dan pembaruan selesai. Diperlukan boot ulang agar pembaruan berlaku."',
        'zswapmsg': 'zswapmsg="ZSWAP sekarang diaktifkan. Anda harus membuat file swap atau partisi."',
        'msgostreepending': 'msgostreepending="Pembaruan sistem sedang menunggu. Silakan boot ulang sistem Anda dan jalankan skrip ini lagi untuk menyelesaikan instalasi."'
    },
    'is.lib': {
        'sysup_starting': 'sysup_starting="-------- VOLLUM KERFI UPPFÆRSLA HEFUR HAFIST --------"',
        'sysup_completed': 'sysup_completed="Hreinsun og uppfærsla lokið."',
        'sysup_rebootreq': 'sysup_rebootreq="Hreinsun og uppfærsla lokið. Endurræsing er nauðsynleg til að uppfærslan taki gildi."',
        'zswapmsg': 'zswapmsg="ZSWAP er nú virkt. Ýe verður að búa til skiptiskrá eða sundurskipti."',
        'msgostreepending': 'msgostreepending="Kerfiuppfærsla á bjóð. Endurkkæstir útómátinn þían og kéyrstir þssa skripta aftur til að löka uppsetningunni."'
    },
    'it.lib': {
        'sysup_starting': 'sysup_starting="-------- AGGIORNAMENTO COMPLETO DEL SISTEMA AVVIATO --------"',
        'sysup_completed': 'sysup_completed="Pulizia e aggiornamento completati."',
        'sysup_rebootreq': 'sysup_rebootreq="Pulizia e aggiornamento completati. È necessario un riavvio affinché l\'aggiornamento abbia effetto."',
        'zswapmsg': 'zswapmsg="ZSWAP è ora abilitato. Devi creare un file o una partizione di scambio."',
        'msgostreepending': 'msgostreepending="Un aggiornamento di sistema è in sospeso. Si prega di riavviare il sistema e eseguire di nuovo questo script per completare l\'installazione."'
    },
    'ja.lib': {
        'sysup_starting': 'sysup_starting="-------- システムの完全なアップデートを開始しています --------"',
        'sysup_completed': 'sysup_completed="クリーンアップとアップデートが完了しました。"',
        'sysup_rebootreq': 'sysup_rebootreq="クリーンアップとアップデートが完了しました。アップデートを有効にするには再起動が必要です。"',
        'zswapmsg': 'zswapmsg="ZSWAPが有効になりました。スワップファイルまたはパーティションを作成する必要があります。"',
        'msgostreepending': 'msgostreepending="システムアップデートが保留中です。システムを再起動して、このスクリプトを再度実行して、インストールを完了してください。"'
    },
    'ka.lib': {
        'sysup_starting': 'sysup_starting="-------- ᲡᲘᲡᲢᲔᲛᲘᲡ სრული განახლება დაწყეს --------"',
        'sysup_completed': 'sysup_completed="გაწმენდა და განახლება დასრულებულია."',
        'sysup_rebootreq': 'sysup_rebootreq="გაწმენდა და განახლება დასრულებულია. განახლების ძალაში შესასვლელად საჭიროა თავიდან ჩატვირთვა."',
        'zswapmsg': 'zswapmsg="ZSWAP ახლა ჩართულია. თქვენ უნდა შექმნათ swap ფაილი ან განყოფილება."'
    },
    'km.lib': {
        'sysup_starting': 'sysup_starting="-------- ការអាប់ដេតប្រព័ន្ធពេញលេញបានចាប់ផ្តើម --------"',
        'sysup_completed': 'sysup_completed="ការសម្អាត និងអាប់ដេតបានបញ្ចប់។"',
        'sysup_rebootreq': 'sysup_rebootreq="ការសម្អាត និងអាប់ដេតបានបញ្ចប់។ ការផ្តើមឡើងវិញគឺត្រូវការដើម្បីឱ្យការអាប់ដេតមានប្រសិទ្ធភាព។"',
        'zswapmsg': 'zswapmsg="ZSWAP ត្រូវបានបើក។ អ្នកត្រូវតែបង្កើតឯកសារប្តូរ ឬផ្នែក។"'
    },
    'ko.lib': {
        'sysup_starting': 'sysup_starting="-------- 전체 시스템 업데이트 시작 --------"',
        'sysup_completed': 'sysup_completed="정리 및 업데이트 완료."',
        'sysup_rebootreq': 'sysup_rebootreq="정리 및 업데이트가 완료되었습니다. 업데이트를 적용하려면 재부팅이 필요합니다."',
        'zswapmsg': 'zswapmsg="ZSWAP이 이제 활성화되었스늵니다. 스익 파일 또는 파티션을 만들어야 합니다."',
        'msgostreepending': 'msgostreepending="시스템 업데이트가 대기 중입니다. 시스템을 다시 부팅하고 설치를 완료하려면 이 스크립트를 다시 실행하세요."'
    },
    'lo.lib': {
        'sysup_starting': 'sysup_starting="-------- ອັບເດດລະບົບເຕັມ ເລີ່ມຕົ້ນ --------"',
        'sysup_completed': 'sysup_completed="ການກາຈະ ແລະ ອັບເດດສໍາເລັດ."',
        'sysup_rebootreq': 'sysup_rebootreq="ການກາຈະ ແລະ ອັບເດດສໍາເລັດ. ຕ້ອງການເริ່ມຕົ້ນໃໝ່ເພື່ອໃຫ້ອັບເດດມີຜົນ."',
        'zswapmsg': 'zswapmsg="ZSWAP ແມ່ນформы ເປີດໃຊ້ງານ. ທ່ານຕ້ອງສ້າງໄຟລ໌ lub partition."'
    },
    'lt.lib': {
        'sysup_starting': 'sysup_starting="-------- PILNA SISTEMOS ATNAUJINIMAS PRADĖTAS --------"',
        'sysup_completed': 'sysup_completed="Valymas ir atnaujinimas baigti."',
        'sysup_rebootreq': 'sysup_rebootreq="Valymas ir atnaujinimas baigti. Atnaujinimui įsigalioti reikalingas iš naujo paleistas kompiuteris."',
        'zswapmsg': 'zswapmsg="ZSWAP dabar yra įjungtas. Turite sukurti keičiamojo failo ar skandinio."',
        'msgostreepending': 'msgostreepending="Sistemos atnaujinimas laukia. Prašome perkrāskite savo sistemą ir iš naujo ėkite šį skriptą, kad užbaigčiumėte diegimą."'
    },
    'lv.lib': {
        'sysup_starting': 'sysup_starting="-------- PILNĪGS SISTĒMAS ATJAUNINĀJUMS SĀCIES --------"',
        'sysup_completed': 'sysup_completed="Tīrīšana un atjauninājums pabeigts."',
        'sysup_rebootreq': 'sysup_rebootreq="Tīrīšana un atjauninājums pabeigts. Lai atjauninājums stātos spēkā, nepieciešama pārstartēšana."',
        'zswapmsg': 'zswapmsg="ZSWAP ir tagad iespējots. Jums jārada swap fails vai nodaļījums."',
        'msgostreepending': 'msgostreepending="Sistēmas atjauninājums gaida. Lūdzu pārstartējiet savu sistēmu un pārstartējiet šo skriptu, lai pabeigtuo instalāciju."'
    },
    'mn.lib': {
        'sysup_starting': 'sysup_starting="-------- СИСТЕМ НООГДСОН ШИНЭЧЛЭЛ ЭХЭЛСЭН --------"',
        'sysup_completed': 'sysup_completed="Цэвэрлэгээ ба шинэчлэл дуусав."',
        'sysup_rebootreq': 'sysup_rebootreq="Цэвэрлэгээ ба шинэчлэл дуусав. Шинэчлэл хэрэгжүүлэхийн тулд системийг дахин эхлүүлэх шаардлагатай."',
        'zswapmsg': 'zswapmsg="ZSWAP одоо идэвхжүүлэгдсэн. Swap файл эсвэл хэсэг үүсгэх шаардлагатай."',
        'msgostreepending': 'msgostreepending="Систем сэргээлт хүлээлтэд байна. Систем дахин эхлүүлээд энэ скриптийг дахин ажиллуулан суулгацыг дуусгануу."'
    },
    'ms.lib': {
        'sysup_starting': 'sysup_starting="-------- KEMASKINI SISTEM PENUH DIMULA --------"',
        'sysup_completed': 'sysup_completed="Pembersihan dan kemaskini selesai."',
        'sysup_rebootreq': 'sysup_rebootreq="Pembersihan dan kemaskini selesai. Permulaan semula diperlukan untuk kemaskini berkuat kuasa."',
        'zswapmsg': 'zswapmsg="ZSWAP kini dibenarkan. Anda mesti membuat fail pertukaran atau bahagian."',
        'msgostreepending': 'msgostreepending="Kemaskini sistem sedang menunggu. Sila mulakan semula sistem anda dan jalankan skrip ini lagi untuk melengkapkan pemasangan."'
    },
    'my.lib': {
        'sysup_starting': 'sysup_starting="-------- အပြည့်အစုံ စနစ်အဆင့်မြှင့်တင်မှု စတင်ခြင်း --------"',
        'sysup_completed': 'sysup_completed="တစ်ခြင်းကျခြင်းနှင့် အဆင့်မြှင့်တင်မှုပြီးစုံ။"',
        'sysup_rebootreq': 'sysup_rebootreq="တစ်ခြင်းကျခြင်းနှင့် အဆင့်မြှင့်တင်မှုပြီးစုံ။ အဆင့်မြှင့်တင်မှုထိရောက်စေရန် ပြန်လည်စတင်ရန် လိုအပ်။"',
        'zswapmsg': 'zswapmsg="ZSWAP အခုဖွင့်လှစ်ထားသည်။ Swap ဖိုင်သို့မဟုတ် အပိုင်းအခြ ဖန်တီးရမည်။"',
        'msgostreepending': 'msgostreepending="စနစ်အဆင့်မြှင့်တင်မှုလုပ်ဆောင်ချက်ခံရန် ကျန်ရှိသည်။ သင့်စနစ်ကို ပြန်လည်စတင်ပြီး ထိုအစီအစဉ်ကို ထပ်မံ ဆောင်ရွက်၍ တင်ဆက်ခြင်းပြီးမြောက်အောင် ကျေးဇူးပြု၍ လုပ်ဆောင်ပါ။"'
    },
    'nb.lib': {
        'sysup_starting': 'sysup_starting="-------- FULL SYSTEMOPPDATERING STARTET --------"',
        'sysup_completed': 'sysup_completed="Opprydding og oppdatering fullført."',
        'sysup_rebootreq': 'sysup_rebootreq="Opprydding og oppdatering fullført. En omstart kreves for at oppdateringen skal tre i kraft."',
        'zswapmsg': 'zswapmsg="ZSWAP er nå aktivert. Du må opprette en swap-fil eller partisjon."',
        'msgostreepending': 'msgostreepending="En systemoppdatering venter. Vennligst start systemet på nytt og kjør dette skriptet igjen for å fullføre installasjonen."'
    },
    'ne.lib': {
        'sysup_starting': 'sysup_starting="-------- संपूर्ण प्रणाली अद्यावधिक सुरु भएको --------"',
        'sysup_completed': 'sysup_completed="सफाई र अद्यावधिक पूर्ण।"',
        'sysup_rebootreq': 'sysup_rebootreq="सफाई र अद्यावधिक पूर्ण। अद्यावधिक प्रभावमा आनको लागि रिबुट आवश्यक छ।"',
        'zswapmsg': 'zswapmsg="ZSWAP अब सक्षम छ। तपाईंले swap फाइल वा विभाजन बनाउनु पर्छ।"',
        'msgostreepending': 'msgostreepending="सिस्टम अपडेट प्रतीक्षामा छ। कृपया आफ्नो सिस्टम पुनः विन्यास गरी स्थापन पूरा गरन यो स्क्रिप्ट फिर्ता चलाउनुहोस्।"'
    },
    'nl.lib': {
        'sysup_starting': 'sysup_starting="-------- VOLLEDIGE SYSTEEMUPDATE GESTART --------"',
        'sysup_completed': 'sysup_completed="Opschoning en update voltooid."',
        'sysup_rebootreq': 'sysup_rebootreq="Opschoning en update voltooid. Een herstart is vereist om de update van kracht te laten worden."',
        'zswapmsg': 'zswapmsg="ZSWAP is nu ingeschakeld. U moet een swap-bestand of partitie aanmaken."',
        'msgostreepending': 'msgostreepending="Een systeemupdate wacht. Start alstublieft uw systeem opnieuw op en voer dit script opnieuw uit om de installatie te voltooien."'
    },
    'pl.lib': {
        'sysup_starting': 'sysup_starting="-------- PEŁNA AKTUALIZACJA SYSTEMU ROZPOCZĘTA --------"',
        'sysup_completed': 'sysup_completed="Czyszczenie i aktualizacja ukończone."',
        'sysup_rebootreq': 'sysup_rebootreq="Czyszczenie i aktualizacja ukończone. Wymagany jest restart, aby aktualizacja weszła w życie."',
        'zswapmsg': 'zswapmsg="ZSWAP jest teraz włączony. Musisz utworzyć plik wymiany lub partycję."',
        'msgostreepending': 'msgostreepending="Aktualizacja systemu oczekuje. Proszę ponownie uruchomić system i uruchomić ten skrypt ponownie, aby ukończyć instalację."'
    },
    'pt.lib': {
        'sysup_starting': 'sysup_starting="-------- ATUALIZAÇÃO COMPLETA DO SISTEMA INICIADA --------"',
        'sysup_completed': 'sysup_completed="Limpeza e atualização concluídas."',
        'sysup_rebootreq': 'sysup_rebootreq="Limpeza e atualização concluídas. Um reinício é necessário para que a atualização entre em vigor."',
        'zswapmsg': 'zswapmsg="ZSWAP está agora habilitado. Você deve criar um arquivo ou partição de troca."',
        'msgostreepending': 'msgostreepending="Uma atualização de sistema está pendente. Reinicie seu sistema e execute este script novamente para concluir a instalação."'
    },
    'ro.lib': {
        'sysup_starting': 'sysup_starting="-------- ACTUALIZARE COMPLETĂ A SISTEMULUI PORNITĂ --------"',
        'sysup_completed': 'sysup_completed="Curățare și actualizare finalizate."',
        'sysup_rebootreq': 'sysup_rebootreq="Curățare și actualizare finalizate. Este necesară o repornire pentru ca actualizarea să intre în vigoare."',
        'zswapmsg': 'zswapmsg="ZSWAP este acum activat. Trebuie să creați un fișier sau o partiție de schimb."',
        'msgostreepending': 'msgostreepending="O actualizare de sistem este în așteptare. Vă rugăm să reporniți sistemul și să executați din nou acest script pentru a finaliza instalarea."'
    },
    'ru.lib': {
        'sysup_starting': 'sysup_starting="-------- ПОЛНОЕ ОБНОВЛЕНИЕ СИСТЕМЫ ЗАПУЩЕНО --------"',
        'sysup_completed': 'sysup_completed="Очистка и обновление завершены."',
        'sysup_rebootreq': 'sysup_rebootreq="Очистка и обновление завершены. Требуется перезагрузка для вступления обновления в силу."',
        'zswapmsg': 'zswapmsg="ZSWAP теперь включен. Вы должны создать файл подкачки или раздел."',
        'msgostreepending': 'msgostreepending="Обновление системы ожидает. Пожалуйста, перезагрузите систему и запустите этот скрипт снова, чтобы завершить установку."'
    },
    'sk.lib': {
        'sysup_starting': 'sysup_starting="-------- ÚPLNÁ AKTUALIZÁCIA SYSTÉMU SPUSTENÁ --------"',
        'sysup_completed': 'sysup_completed="Čistenie a aktualizácia boli dokončené."',
        'sysup_rebootreq': 'sysup_rebootreq="Čistenie a aktualizácia boli dokončené. Pre vplyv aktualizácie je potrebný reštart."',
        'zswapmsg': 'zswapmsg="ZSWAP je teraz povolený. Musíte vytvoriť swap súbor alebo oddiel."',
        'msgostreepending': 'msgostreepending="Aktualizácia systému čaká. Prosím reštartujte váš systém a spustite tento skript znova, aby ste dokončili inštaláciu."'
    },
    'sl.lib': {
        'sysup_starting': 'sysup_starting="-------- POLNA POSODOBITEV SISTEMA ZAČETA --------"',
        'sysup_completed': 'sysup_completed="Čiščenje in posodobitev sta dokončana."',
        'sysup_rebootreq': 'sysup_rebootreq="Čiščenje in posodobitev sta dokončana. Ponovno zagon je potreben, da se posodobitev uveljavи."',
        'zswapmsg': 'zswapmsg="ZSWAP je sedaj omogočen. Ustvariti morate datoteko ali particijo za zamenjavo."',
        'msgostreepending': 'msgostreepending="Posodobitev sistema je v teku. Prosim ponovno zaženite sistem in znova zaženite ta skript, da dokončate namestitev."'
    },
    'sq.lib': {
        'sysup_starting': 'sysup_starting="-------- PËRDITËSIM I PLOTË I SISTEMIT FILLUAR --------"',
        'sysup_completed': 'sysup_completed="Pastrimi dhe përditësimi u përfunduan."',
        'sysup_rebootreq': 'sysup_rebootreq="Pastrimi dhe përditësimi u përfunduan. Kërkohet rilindja për të zënë fuqi përditësimi."',
        'zswapmsg': 'zswapmsg="ZSWAP është tani i aktivizuar. Duhet të krijoni një skedar ose ndarje shkëmbimi."',
        'msgostreepending': 'msgostreepending="Përditësimi i sistemit është në pritje. Ju lutemi ristartuani sistemin tuaj dhe ekzekutoni këtë skript përsëri për të përfunduar instalimin."'
    },
    'sr.lib': {
        'sysup_starting': 'sysup_starting="-------- ПОТПУНА АЖУРИРАЊА СИСТЕМА ПОЧЕТА --------"',
        'sysup_completed': 'sysup_completed="Чишћење и ажурирање су завршени."',
        'sysup_rebootreq': 'sysup_rebootreq="Чишћење и ажурирање су завршени. Потребан је поновни покрет да ажурирање стане на снагу."',
        'zswapmsg': 'zswapmsg="ZSWAP је сада активиран. Морате креирати датотеку или партицију за размену."',
        'msgostreepending': 'msgostreepending="Ажурирање система је у очекивању. Молимо поново покрените систем и поново покрените овај скрипт да бисте завршили инсталацију."'
    },
    'sv.lib': {
        'sysup_starting': 'sysup_starting="-------- FULLSTÄNDIG SYSTEMUPPDATERING STARTAD --------"',
        'sysup_completed': 'sysup_completed="Rensning och uppdatering slutförda."',
        'sysup_rebootreq': 'sysup_rebootreq="Rensning och uppdatering slutförda. En omstart krävs för att uppdateringen ska träda i kraft."',
        'zswapmsg': 'zswapmsg="ZSWAP är nu aktiverat. Du måste skapa en swap-fil eller partition."',
        'msgostreepending': 'msgostreepending="En systemuppdatering väntar. Starta om systemet och kör detta skript igen för att slutföra installationen."'
    },
    'sw.lib': {
        'sysup_starting': 'sysup_starting="-------- KUSASISHA KWA KAMILI KWA MFUMO KUANZISHWA --------"',
        'sysup_completed': 'sysup_completed="Kusafisha na kusasisha kumalizwa."',
        'sysup_rebootreq': 'sysup_rebootreq="Kusafisha na kusasisha kumalizwa. Uanzishaji upya unahitajika ili kusasisha kuwe na matokeo."',
        'zswapmsg': 'zswapmsg="ZSWAP sasa imefungwa. Lazima uunde faili au kizigeu cha kubadilishana."',
        'msgostreepending': 'msgostreepending="Kusasisha kwa mfumo kunakaa. Tafadhali anzisha tena mfumo wako na utekeleze hati hii upya kumalizia uongozaji."'
    },
    'ta.lib': {
        'sysup_starting': 'sysup_starting="-------- FULL SYSTEM UPDATE STARTING --------"',
        'sysup_completed': 'sysup_completed="Cleanup and update complete."',
        'sysup_rebootreq': 'sysup_rebootreq="Cleanup and update done. A reboot is required for the update to take effect."',
        'zswapmsg': 'zswapmsg="ZSWAP is now enabled. Create a swap file or partition."',
        'msgostreepending': 'msgostreepending="A system update is pending. Please reboot your system and run this script again to complete the installation."'
    },
    'tg.lib': {
        'sysup_starting': 'sysup_starting="-------- FULL SYSTEM UPDATE STARTING --------"',
        'sysup_completed': 'sysup_completed="Cleanup and update complete."',
        'sysup_rebootreq': 'sysup_rebootreq="Cleanup and update done. A reboot is required for the update to take effect."',
        'zswapmsg': 'zswapmsg="ZSWAP is now enabled. Create a swap file or partition."',
        'msgostreepending': 'msgostreepending="A system update is pending. Please reboot your system and run this script again to complete the installation."'
    },
    'th.lib': {
        'sysup_starting': 'sysup_starting="-------- FULL SYSTEM UPDATE STARTING --------"',
        'sysup_completed': 'sysup_completed="Cleanup and update complete."',
        'sysup_rebootreq': 'sysup_rebootreq="Cleanup and update done. A reboot is required for the update to take effect."',
        'zswapmsg': 'zswapmsg="ZSWAP is now enabled. Create a swap file or partition."',
        'msgostreepending': 'msgostreepending="A system update is pending. Please reboot your system and run this script again to complete the installation."'
    },
    'tl.lib': {
        'sysup_starting': 'sysup_starting="-------- FULL SYSTEM UPDATE STARTING --------"',
        'sysup_completed': 'sysup_completed="Cleanup and update complete."',
        'sysup_rebootreq': 'sysup_rebootreq="Cleanup and update done. A reboot is required for the update to take effect."',
        'zswapmsg': 'zswapmsg="ZSWAP is now enabled. Create a swap file or partition."',
        'msgostreepending': 'msgostreepending="A system update is pending. Please reboot your system and run this script again to complete the installation."'
    },
    'tr.lib': {
        'sysup_starting': 'sysup_starting="-------- TAM SİSTEM GÜNCELLEMESI BAŞLATILDI --------"',
        'sysup_completed': 'sysup_completed="Temizlik ve güncelleme tamamlandı."',
        'sysup_rebootreq': 'sysup_rebootreq="Temizlik ve güncelleme tamamlandı. Güncellemenin etkili olması için yeniden başlatma gereklidir."',
        'zswapmsg': 'zswapmsg="ZSWAP artık etkinleştirildi. Bir swap dosyası veya bölümü oluşturmalısınız."',
        'msgostreepending': 'msgostreepending="Bir sistem güncellemesi bekleniyor. Sisteminizi yeniden başlatın ve yüklemeyi tamamlamak için bu betiği tekrar çalıştırın."'
    },
    'uk.lib': {
        'sysup_starting': 'sysup_starting="-------- ПОВНЕ ОНОВЛЕННЯ СИСТЕМИ РОЗПОЧАТО --------"',
        'sysup_completed': 'sysup_completed="Очищення та оновлення завершені."',
        'sysup_rebootreq': 'sysup_rebootreq="Очищення та оновлення завершені. Для вступлення оновлення в силу вимагається перезавантаження."',
        'zswapmsg': 'zswapmsg="ZSWAP тепер увімкнено. Ви повинні створити файл або розділ обміну."',
        'msgostreepending': 'msgostreepending="Оновлення системи очікує. Будь ласка, перезавантажте систему та запустіть цей скрипт знову, щоб завершити встановлення."'
    },
    'ur.lib': {
        'sysup_starting': 'sysup_starting="-------- مکمل نظام کی تازہ کاری شروع ہو گئی --------"',
        'sysup_completed': 'sysup_completed="صفائی اور تازہ کاری مکمل ہو گئی۔"',
        'sysup_rebootreq': 'sysup_rebootreq="صفائی اور تازہ کاری مکمل ہو گئی۔ تازہ کاری کو نافذ کرنے کے لیے ری بوٹ ضروری ہے۔"',
        'zswapmsg': 'zswapmsg="ZSWAP اب فعال ہے۔ آپ کو ایک سوئپ فائل یا تقسیم بنانا ہوگی۔"',
        'msgostreepending': 'msgostreepending="سسٹم اپ ڈیٹ زیر التوا ہے۔ براہ کرم اپنے سسٹم کو دوبارہ بوٹ کریں اور انسٹالیشن مکمل کرنے کے لیے اس اسکرپٹ کو دوبارہ چلائیں۔"'
    },
    'uz.lib': {
        'sysup_starting': 'sysup_starting="-------- TOLIQ TIZIM YANGILANISHI BOSHLAB BERILDI --------"',
        'sysup_completed': 'sysup_completed="Tozalash va yangilash yakunlandi."',
        'sysup_rebootreq': 'sysup_rebootreq="Tozalash va yangilash yakunlandi. Yangilashning amal qilishi uchun qayta yuklanish kerak."',
        'zswapmsg': 'zswapmsg="ZSWAP endi faollashtirildi. Swap faylini yoki boʻlimni yaratishingiz kerak."',
        'msgostreepending': 'msgostreepending="Tizim yangilanishi kutmoqda. Iltimos tizimni qayta yoqing va o\'rnatishni tugatish uchun ushbu skriptni yana ishga tushiring."'
    },
    'vi.lib': {
        'sysup_starting': 'sysup_starting="-------- CẬP NHẬT TOÀN BỘ HỆ THỐNG ĐƯỢC BẮT ĐẦU --------"',
        'sysup_completed': 'sysup_completed="Dọn dẹp và cập nhật hoàn tất."',
        'sysup_rebootreq': 'sysup_rebootreq="Dọn dẹp và cập nhật hoàn tất. Cần khởi động lại để cập nhật có hiệu lực."',
        'zswapmsg': 'zswapmsg="ZSWAP hiện được bật. Bạn phải tạo tệp hoán đổi hoặc phân vùng."',
        'msgostreepending': 'msgostreepending="Một bản cập nhật hệ thống đang chờ. Vui lòng khởi động lại hệ thống của bạn và chạy lại tập lệnh này để hoàn tất cài đặt."'
    },
    'zh.lib': {
        'sysup_starting': 'sysup_starting="-------- 完整系统更新开始 --------"',
        'sysup_completed': 'sysup_completed="清理和更新完成。"',
        'sysup_rebootreq': 'sysup_rebootreq="清理和更新完成。需要重新启动才能使更新生效。"',
        'zswapmsg': 'zswapmsg="ZSWAP现在已启用。 您必须创建交换文件或分区。"',
        'msgostreepending': 'msgostreepending="系统更新待处理。请重新启动您的系统并再次运行此脚本以完成安装。"'
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

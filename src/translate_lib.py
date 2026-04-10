#!/usr/bin/env python3
"""
Script to add system update related translations to all language .lib files

These messages are for the new system update feature:
- sysup_starting: Message shown at the start of system update
- sysup_completed: Message shown when update completes
- sysup_rebootreq: Message shown when reboot is required
"""

import os

# The base directory containing language files
LANG_DIR = "../p3/libs/lang"

# Translations for all three messages across all supported languages
TRANSLATIONS = {
    'am.lib': {
        'sysup_starting': 'sysup_starting="-------- ሙሉ ሲስተም ማዘመን ጀምሮ --------"',
        'sysup_completed': 'sysup_completed="ማስተካከል እና ማዘመን ተጠናቋል።"',
        'sysup_rebootreq': 'sysup_rebootreq="ማስተካከል እና ማዘመን ተጠናቋል። ማዘመኖቱ ንጽህና ውስጥ ለመግባት እንደገና ተጀምሮ ሊሆን ይችላል።"'
    },
    'ar.lib': {
        'sysup_starting': 'sysup_starting="-------- تحديث النظام الكامل بدء --------"',
        'sysup_completed': 'sysup_completed="التنظيف والتحديث مكتملان."',
        'sysup_rebootreq': 'sysup_rebootreq="التنظيف والتحديث مكتملان. إعادة تشغيل مطلوبة لتفعيل التحديث."'
    },
    'az.lib': {
        'sysup_starting': 'sysup_starting="-------- TAM SİSTEM YENİLƏMƏSİ BAŞLADIQLARI --------"',
        'sysup_completed': 'sysup_completed="Təmizlənmə və güncəllənmə tamamlandı."',
        'sysup_rebootreq': 'sysup_rebootreq="Təmizlənmə və güncəllənmə tamamlandı. Güncəllənmənin səmərəli olması üçün yenidən başladılması tələb olunur."'
    },
    'bg.lib': {
        'sysup_starting': 'sysup_starting="-------- ПЪЛНО СИСТЕМНО ОБНОВЯВАНЕ СТАРТИРАНО --------"',
        'sysup_completed': 'sysup_completed="Почистване и актуализация завършени."',
        'sysup_rebootreq': 'sysup_rebootreq="Почистване и актуализация завършени. Необходимо е рестартиране, за да влезе обновката в сила."'
    },
    'bn.lib': {
        'sysup_starting': 'sysup_starting="-------- সম্পূর্ণ সিস্টেম আপডেট শুরু হয়েছে --------"',
        'sysup_completed': 'sysup_completed="পরিষ্কার এবং আপডেট সম্পূর্ণ।"',
        'sysup_rebootreq': 'sysup_rebootreq="পরিষ্কার এবং আপডেট সম্পূর্ণ। আপডেটটি কার্যকর হতে একটি পুনর্বুট প্রয়োজন।"'
    },
    'bs.lib': {
        'sysup_starting': 'sysup_starting="-------- PUNO AŽURIRANJE SISTEMA ZAPOČETO --------"',
        'sysup_completed': 'sysup_completed="Čišćenje i ažuriranje dovršeni."',
        'sysup_rebootreq': 'sysup_rebootreq="Čišćenje i ažuriranje dovršeni. Potreban je restart kako bi ažuriranje stupio na snagu."'
    },
    'cs.lib': {
        'sysup_starting': 'sysup_starting="-------- SPUŠTĚNA ÚPLNÁ AKTUALIZACE SYSTÉMU --------"',
        'sysup_completed': 'sysup_completed="Vyčištění a aktualizace dokončeny."',
        'sysup_rebootreq': 'sysup_rebootreq="Vyčištění a aktualizace dokončeny. Pro použití aktualizace je vyžadován restart."'
    },
    'da.lib': {
        'sysup_starting': 'sysup_starting="-------- FULD SYSTEMOPDATERING STARTER --------"',
        'sysup_completed': 'sysup_completed="Rengøring og opdatering afsluttet."',
        'sysup_rebootreq': 'sysup_rebootreq="Rengøring og opdatering afsluttet. En genstart er påkrævet for, at opdateringen træder i kraft."'
    },
    'de.lib': {
        'sysup_starting': 'sysup_starting="-------- VOLLSTÄNDIGE SYSTEMAKTUALISIERUNG GESTARTET --------"',
        'sysup_completed': 'sysup_completed="Bereinigung und Aktualisierung abgeschlossen."',
        'sysup_rebootreq': 'sysup_rebootreq="Bereinigung und Aktualisierung abgeschlossen. Ein Neustart ist erforderlich, damit die Aktualisierung in Kraft tritt."'
    },
    'el.lib': {
        'sysup_starting': 'sysup_starting="-------- ΠΛΉΡΗΣ ΕΝΗΜΈΡΩΣΗ ΣΥΣΤΉΜΑΤΟΣ ΞΕΚΙΝΆ --------"',
        'sysup_completed': 'sysup_completed="Ο καθαρισμός και η ενημέρωση ολοκληρώθηκαν."',
        'sysup_rebootreq': 'sysup_rebootreq="Ο καθαρισμός και η ενημέρωση ολοκληρώθηκαν. Απαιτείται επανεκκίνηση για να ισχύσει η ενημέρωση."'
    },
    'es.lib': {
        'sysup_starting': 'sysup_starting="-------- ACTUALIZACIÓN COMPLETA DEL SISTEMA INICIADA --------"',
        'sysup_completed': 'sysup_completed="Limpieza y actualización completadas."',
        'sysup_rebootreq': 'sysup_rebootreq="Limpieza y actualización completadas. Se requiere un reinicio para que la actualización surta efecto."'
    },
    'et.lib': {
        'sysup_starting': 'sysup_starting="-------- TÄIELIK SÜSTEEMI VÄRSKENDUS ALUSTATUD --------"',
        'sysup_completed': 'sysup_completed="Puhastamine ja värskendamine lõpule viidud."',
        'sysup_rebootreq': 'sysup_rebootreq="Puhastamine ja värskendamine lõpule viidud. Värskenduse rakendamiseks on vajalik taaskäivitamine."'
    },
    'fa.lib': {
        'sysup_starting': 'sysup_starting="-------- بروزرسانی کامل سیستم آغاز شد --------"',
        'sysup_completed': 'sysup_completed="تمیز کردن و بروزرسانی کامل شد."',
        'sysup_rebootreq': 'sysup_rebootreq="تمیز کردن و بروزرسانی کامل شد. برای اعمال بروزرسانی نیاز به راه اندازی مجدد است."'
    },
    'fi.lib': {
        'sysup_starting': 'sysup_starting="-------- TÄYSI JÄRJESTELMÄN PÄIVITYS KÄYNNISTETTY --------"',
        'sysup_completed': 'sysup_completed="Siivous ja päivitys valmis."',
        'sysup_rebootreq': 'sysup_rebootreq="Siivous ja päivitys valmis. Päivityksen voimaantuloa varten vaaditaan uudelleenkäynnistys."'
    },
    'fr.lib': {
        'sysup_starting': 'sysup_starting="-------- MISE À JOUR COMPLÈTE DU SYSTÈME DÉMARRÉE --------"',
        'sysup_completed': 'sysup_completed="Nettoyage et mise à jour terminés."',
        'sysup_rebootreq': 'sysup_rebootreq="Nettoyage et mise à jour terminés. Un redémarrage est requis pour que la mise à jour prenne effet."'
    },
    'ga.lib': {
        'sysup_starting': 'sysup_starting="-------- NUASHONRÚ IOMLÁN CÓRAS TOSAITHE --------"',
        'sysup_completed': 'sysup_completed="Glanúchán agus nuashonrú críochnaithe."',
        'sysup_rebootreq': 'sysup_rebootreq="Glanúchán agus nuashonrú críochnaithe. Tá atosú ag teastáil chun an nuashonrú a chur i bhfeidhm."'
    },
    'he.lib': {
        'sysup_starting': 'sysup_starting="-------- עדכון מערכת מלא החל --------"',
        'sysup_completed': 'sysup_completed="ניקוי ועדכון הושלמו."',
        'sysup_rebootreq': 'sysup_rebootreq="ניקוי ועדכון הושלמו. נדרש אתחול מחדש כדי שהעדכון יכנס לתוקף."'
    },
    'hi.lib': {
        'sysup_starting': 'sysup_starting="-------- संपूर्ण सिस्टम अपडेट शुरू --------"',
        'sysup_completed': 'sysup_completed="सफाई और अपडेट पूर्ण।"',
        'sysup_rebootreq': 'sysup_rebootreq="सफाई और अपडेट पूर्ण। अपडेट लागू होने के लिए पुनः बूट की आवश्यकता है।"'
    },
    'hr.lib': {
        'sysup_starting': 'sysup_starting="-------- PUNE AŽURIRANJE SISTEMA POČETO --------"',
        'sysup_completed': 'sysup_completed="Čišćenje i ažuriranje dovršeni."',
        'sysup_rebootreq': 'sysup_rebootreq="Čišćenje i ažuriranje dovršeni. Potreban je restart kako bi ažuriranje stupio na snagu."'
    },
    'hu.lib': {
        'sysup_starting': 'sysup_starting="-------- TELJES RENDSZERFRISSÍTÉS ELINDÍTVA --------"',
        'sysup_completed': 'sysup_completed="Megtisztítás és frissítés befejezve."',
        'sysup_rebootreq': 'sysup_rebootreq="Megtisztítás és frissítés befejezve. A frissítés érvénybe lépéséhez újraindítás szükséges."'
    },
    'hy.lib': {
        'sysup_starting': 'sysup_starting="-------- ԱՄԲՈՂՋԱԿԱՆ ՀԱՄԱԿԱՐԳԻ ԹԱՐՄԱՑՈՒՄ ՍԿՍՎԵԼ --------"',
        'sysup_completed': 'sysup_completed="Մաքրում և թարմացում ավարտված։"',
        'sysup_rebootreq': 'sysup_rebootreq="Մաքրում և թարմացում ավարտված։ Թարմացումը ուժի մեջ մտնելու համար անհրաժեշտ է վերաբեռնում։"'
    },
    'id.lib': {
        'sysup_starting': 'sysup_starting="-------- PEMBARUAN SISTEM LENGKAP DIMULAI --------"',
        'sysup_completed': 'sysup_completed="Pembersihan dan pembaruan selesai."',
        'sysup_rebootreq': 'sysup_rebootreq="Pembersihan dan pembaruan selesai. Diperlukan boot ulang agar pembaruan berlaku."'
    },
    'is.lib': {
        'sysup_starting': 'sysup_starting="-------- VOLLUM KERFI UPPFÆRSLA HEFUR HAFIST --------"',
        'sysup_completed': 'sysup_completed="Hreinsun og uppfærsla lokið."',
        'sysup_rebootreq': 'sysup_rebootreq="Hreinsun og uppfærsla lokið. Endurræsing er nauðsynleg til að uppfærslan taki gildi."'
    },
    'it.lib': {
        'sysup_starting': 'sysup_starting="-------- AGGIORNAMENTO COMPLETO DEL SISTEMA AVVIATO --------"',
        'sysup_completed': 'sysup_completed="Pulizia e aggiornamento completati."',
        'sysup_rebootreq': 'sysup_rebootreq="Pulizia e aggiornamento completati. È necessario un riavvio affinché l\'aggiornamento abbia effetto."'
    },
    'ja.lib': {
        'sysup_starting': 'sysup_starting="-------- システムの完全なアップデートを開始しています --------"',
        'sysup_completed': 'sysup_completed="クリーンアップとアップデートが完了しました。"',
        'sysup_rebootreq': 'sysup_rebootreq="クリーンアップとアップデートが完了しました。アップデートを有効にするには再起動が必要です。"'
    },
    'ka.lib': {
        'sysup_starting': 'sysup_starting="-------- ᲡᲘᲡᲢᲔᲛᲘᲡ სრული განახლება დაწყეს --------"',
        'sysup_completed': 'sysup_completed="გაწმენდა და განახლება დასრულებულია."',
        'sysup_rebootreq': 'sysup_rebootreq="გაწმენდა და განახლება დასრულებულია. განახლების ძალაში შესასვლელად საჭიროა თავიდან ჩატვირთვა."'
    },
    'km.lib': {
        'sysup_starting': 'sysup_starting="-------- ការអាប់ដេតប្រព័ន្ធពេញលេញបានចាប់ផ្តើម --------"',
        'sysup_completed': 'sysup_completed="ការសម្អាត និងអាប់ដេតបានзавершено។"',
        'sysup_rebootreq': 'sysup_rebootreq="ការសម្អាត និងអាប់ដេតបានបញ្ចប់។ ការផ្តើមឡើងវិញគឺត្រូវការដើម្បីឱ្យការអាប់ដេតមានប្រសិទ្ធភាព។"'
    },
    'ko.lib': {
        'sysup_starting': 'sysup_starting="-------- 전체 시스템 업데이트 시작 --------"',
        'sysup_completed': 'sysup_completed="정리 및 업데이트 완료."',
        'sysup_rebootreq': 'sysup_rebootreq="정리 및 업데이트가 완료되었습니다. 업데이트를 적용하려면 재부팅이 필요합니다."'
    },
    'lo.lib': {
        'sysup_starting': 'sysup_starting="-------- ອັບເດດລະບົບເຕັມ ເລີ່ມຕົ້ນ --------"',
        'sysup_completed': 'sysup_completed="ການກາຈະ ແລະ ອັບເດດສໍາເລັດ."',
        'sysup_rebootreq': 'sysup_rebootreq="ການກາຈະ ແລະ ອັບເດດສໍາເລັດ. ຕ້ອງການເริ່ມຕົ້ນໃໝ່ເພື່ອໃຫ້ອັບເດດມີຜົນ."'
    },
    'lt.lib': {
        'sysup_starting': 'sysup_starting="-------- PILNA SISTEMOS ATNAUJINIMAS PRADĖTAS --------"',
        'sysup_completed': 'sysup_completed="Valymas ir atnaujinimas baigti."',
        'sysup_rebootreq': 'sysup_rebootreq="Valymas ir atnaujinimas baigti. Atnaujinimui įsigalioti reikalingas iš naujo paleistas kompiuteris."'
    },
    'lv.lib': {
        'sysup_starting': 'sysup_starting="-------- PILNĪGS SISTĒMAS ATJAUNINĀJUMS SĀCIES --------"',
        'sysup_completed': 'sysup_completed="Tīrīšana un atjauninājums pabeigts."',
        'sysup_rebootreq': 'sysup_rebootreq="Tīrīšana un atjauninājums pabeigts. Lai atjauninājums stātos spēkā, nepieciešama pārstartēšana."'
    },
    'mn.lib': {
        'sysup_starting': 'sysup_starting="-------- СИСТЕМ НООГДСОН ШИНЭЧЛЭЛ ЭХЭЛСЭН --------"',
        'sysup_completed': 'sysup_completed="Цэвэрлэгээ ба шинэчлэл дуусав."',
        'sysup_rebootreq': 'sysup_rebootreq="Цэвэрлэгээ ба шинэчлэл дуусав. Шинэчлэл хэрэгжүүлэхийн тулд системийг дахин эхлүүлэх шаардлагатай."'
    },
    'ms.lib': {
        'sysup_starting': 'sysup_starting="-------- KEMASKINI SISTEM PENUH DIMULA --------"',
        'sysup_completed': 'sysup_completed="Pembersihan dan kemaskini selesai."',
        'sysup_rebootreq': 'sysup_rebootreq="Pembersihan dan kemaskini selesai. Permulaan semula diperlukan untuk kemaskini berkuat kuasa."'
    },
    'my.lib': {
        'sysup_starting': 'sysup_starting="-------- အပြည့်အစုံ စနစ်အဆင့်မြှင့်တင်မှု စတင်ခြင်း --------"',
        'sysup_completed': 'sysup_completed="တစ်ခြင်း ကျ ခြင်း နှင့် အဆင့်မြှင့်တင်မှု ပြီးစုံ။"',
        'sysup_rebootreq': 'sysup_rebootreq="တစ်ခြင်း ကျ ခြင်း နှင့် အဆင့်မြှင့်တင်မှု ပြီးစုံ။ အဆင့်မြှင့်တင်မှု ထိရောက်စေရန် ပြန်လည်စတင်ရန် လိုအပ်။"'
    },
    'nb.lib': {
        'sysup_starting': 'sysup_starting="-------- FULL SYSTEMOPPDATERING STARTET --------"',
        'sysup_completed': 'sysup_completed="Opprydding og oppdatering fullført."',
        'sysup_rebootreq': 'sysup_rebootreq="Opprydding og oppdatering fullført. En omstart kreves for at oppdateringen skal tre i kraft."'
    },
    'ne.lib': {
        'sysup_starting': 'sysup_starting="-------- संपूर्ण प्रणाली अद्यावधिक सुरु भएको --------"',
        'sysup_completed': 'sysup_completed="सफाई र अद्यावधिक पूर्ण।"',
        'sysup_rebootreq': 'sysup_rebootreq="सफाई र अद्यावधिक पूर्ण। अद्यावधिक प्रभावमा आनको लागि रिबुट आवश्यक छ।"'
    },
    'nl.lib': {
        'sysup_starting': 'sysup_starting="-------- VOLLEDIGE SYSTEEMUPDATE GESTART --------"',
        'sysup_completed': 'sysup_completed="Opschoning en update voltooid."',
        'sysup_rebootreq': 'sysup_rebootreq="Opschoning en update voltooid. Een herstart is vereist om de update van kracht te laten worden."'
    },
    'pl.lib': {
        'sysup_starting': 'sysup_starting="-------- PEŁNA AKTUALIZACJA SYSTEMU ROZPOCZĘTA --------"',
        'sysup_completed': 'sysup_completed="Czyszczenie i aktualizacja ukończone."',
        'sysup_rebootreq': 'sysup_rebootreq="Czyszczenie i aktualizacja ukończone. Wymagany jest restart, aby aktualizacja weszła w życie."'
    },
    'pt.lib': {
        'sysup_starting': 'sysup_starting="-------- ATUALIZAÇÃO COMPLETA DO SISTEMA INICIADA --------"',
        'sysup_completed': 'sysup_completed="Limpeza e atualização concluídas."',
        'sysup_rebootreq': 'sysup_rebootreq="Limpeza e atualização concluídas. Um reinício é necessário para que a atualização entre em vigor."'
    },
    'ro.lib': {
        'sysup_starting': 'sysup_starting="-------- ACTUALIZARE COMPLETĂ A SISTEMULUI PORNITĂ --------"',
        'sysup_completed': 'sysup_completed="Curățare și actualizare finalizate."',
        'sysup_rebootreq': 'sysup_rebootreq="Curățare și actualizare finalizate. Este necesară o repornire pentru ca actualizarea să intre în vigoare."'
    },
    'ru.lib': {
        'sysup_starting': 'sysup_starting="-------- ПОЛНОЕ ОБНОВЛЕНИЕ СИСТЕМЫ ЗАПУЩЕНО --------"',
        'sysup_completed': 'sysup_completed="Очистка и обновление завершены."',
        'sysup_rebootreq': 'sysup_rebootreq="Очистка и обновление завершены. Требуется перезагрузка для вступления обновления в силу."'
    },
    'sk.lib': {
        'sysup_starting': 'sysup_starting="-------- ÚPLNÁ AKTUALIZÁCIA SYSTÉMU SPUSTENÁ --------"',
        'sysup_completed': 'sysup_completed="Čistenie a aktualizácia boli dokončené."',
        'sysup_rebootreq': 'sysup_rebootreq="Čistenie a aktualizácia boli dokončené. Pre vplyv aktualizácie je potrebný reštart."'
    },
    'sl.lib': {
        'sysup_starting': 'sysup_starting="-------- POLNA POSODOBITEV SISTEMA ZAČETA --------"',
        'sysup_completed': 'sysup_completed="Čiščenje in posodobitev sta dokončana."',
        'sysup_rebootreq': 'sysup_rebootreq="Čiščenje in posodobitev sta dokončana. Ponovno zagon je potreben, da se posodobitev uveljavи."'
    },
    'sq.lib': {
        'sysup_starting': 'sysup_starting="-------- PËRDITËSIM I PLOTË I SISTEMIT FILLUAR --------"',
        'sysup_completed': 'sysup_completed="Pastrimi dhe përditësimi u përfunduan."',
        'sysup_rebootreq': 'sysup_rebootreq="Pastrimi dhe përditësimi u përfunduan. Kërkohet rilindja për të zënë fuqi përditësimi."'
    },
    'sr.lib': {
        'sysup_starting': 'sysup_starting="-------- ПОТПУНА АЖУРИРАЊА СИСТЕМА ПОЧЕТА --------"',
        'sysup_completed': 'sysup_completed="Чишћење и ажурирање су завршени."',
        'sysup_rebootreq': 'sysup_rebootreq="Чишћење и ажурирање су завршени. Потребан је поновни покрет да ажурирање стане на снагу."'
    },
    'sv.lib': {
        'sysup_starting': 'sysup_starting="-------- FULLSTÄNDIG SYSTEMUPPDATERING STARTAD --------"',
        'sysup_completed': 'sysup_completed="Rensning och uppdatering slutförda."',
        'sysup_rebootreq': 'sysup_rebootreq="Rensning och uppdatering slutförda. En omstart krävs för att uppdateringen ska träda i kraft."'
    },
    'sw.lib': {
        'sysup_starting': 'sysup_starting="-------- KUSASISHA KWA KAMILI KWA MFUMO KUANZISHWA --------"',
        'sysup_completed': 'sysup_completed="Kusafisha na kusasisha kumalizwa."',
        'sysup_rebootreq': 'sysup_rebootreq="Kusafisha na kusasisha kumalizwa. Uanzishaji upya unahitajika ili kusasisha kuwe na matokeo."'
    },
    'ta.lib': {
        'sysup_starting': 'sysup_starting="-------- முழு கணினி மேம்பாடு தொடங்கியுள்ளது --------"',
        'sysup_completed': 'sysup_completed="பরிசோதனை மற்றும் மேம்பாடு முடிந்துவிட்டது."',
        'sysup_rebootreq': 'sysup_rebootreq="பரிசோதனை மற்றும் மேம்பாடு முடிந்துவிட்டது. மேம்பாடு பயனில் நுழைய மறுதொடக்கம் தேவை।"'
    },
    'tg.lib': {
        'sysup_starting': 'sysup_starting="-------- НАВИ КАРДАНИ ПУРРАСИМОНА СИСТЕМАМОН ОҒОЗ ЁФТА --------"',
        'sysup_completed': 'sysup_completed="Тоза кардан ва нави кардан ба охир расид."',
        'sysup_rebootreq': 'sysup_rebootreq="Тоза кардан ва нави кардан ба охир расид. Барои кушодани нави кардан аз нави оғоз кардани система зарур аст."'
    },
    'th.lib': {
        'sysup_starting': 'sysup_starting="-------- การอัปเดตระบบทั้งหมดเริ่มต้นแล้ว --------"',
        'sysup_completed': 'sysup_completed="การทำความสะอาดและการอัปเดตเสร็จสิ้น"',
        'sysup_rebootreq': 'sysup_rebootreq="การทำความสะอาดและการอัปเดตเสร็จสิ้น จำเป็นต้องรีบูตเพื่อให้การอัปเดตมีผล"'
    },
    'tl.lib': {
        'sysup_starting': 'sysup_starting="-------- BUONG SISTEMA NG PANGANGAILANGAN NAGSIMULA --------"',
        'sysup_completed': 'sysup_completed="Paglilinis at pag-update ay nakumpleto."',
        'sysup_rebootreq': 'sysup_rebootreq="Paglilinis at pag-update ay nakumpleto. Kailangan ng pag-reboot para sa pag-update na maging epektibo."'
    },
    'tr.lib': {
        'sysup_starting': 'sysup_starting="-------- TAM SİSTEM GÜNCELLEMESI BAŞLATILDI --------"',
        'sysup_completed': 'sysup_completed="Temizlik ve güncelleme tamamlandı."',
        'sysup_rebootreq': 'sysup_rebootreq="Temizlik ve güncelleme tamamlandı. Güncellemenin etkili olması için yeniden başlatma gereklidir."'
    },
    'uk.lib': {
        'sysup_starting': 'sysup_starting="-------- ПОВНЕ ОНОВЛЕННЯ СИСТЕМИ РОЗПОЧАТО --------"',
        'sysup_completed': 'sysup_completed="Очищення та оновлення завершені."',
        'sysup_rebootreq': 'sysup_rebootreq="Очищення та оновлення завершені. Для вступлення оновлення в силу вимагається перезавантаження."'
    },
    'ur.lib': {
        'sysup_starting': 'sysup_starting="-------- مکمل نظام کی تازہ کاری شروع ہو گئی --------"',
        'sysup_completed': 'sysup_completed="صفائی اور تازہ کاری مکمل ہو گئی۔"',
        'sysup_rebootreq': 'sysup_rebootreq="صفائی اور تازہ کاری مکمل ہو گئی۔ تازہ کاری کو نافذ کرنے کے لیے ری بوٹ ضروری ہے۔"'
    },
    'uz.lib': {
        'sysup_starting': 'sysup_starting="-------- TOLIQ TIZIM YANGILANISHI BOSHLAB BERILDI --------"',
        'sysup_completed': 'sysup_completed="Tozalash va yangilash yakunlandi."',
        'sysup_rebootreq': 'sysup_rebootreq="Tozalash va yangilash yakunlandi. Yangilashning amal qilishi uchun qayta yuklanish kerak."'
    },
    'vi.lib': {
        'sysup_starting': 'sysup_starting="-------- CẬP NHẬT TOÀN BỘ HỆ THỐNG ĐƯỢC BẮT ĐẦU --------"',
        'sysup_completed': 'sysup_completed="Dọn dẹp và cập nhật hoàn tất."',
        'sysup_rebootreq': 'sysup_rebootreq="Dọn dẹp và cập nhật hoàn tất. Cần khởi động lại để cập nhật có hiệu lực."'
    },
    'zh.lib': {
        'sysup_starting': 'sysup_starting="-------- 完整系统更新开始 --------"',
        'sysup_completed': 'sysup_completed="清理和更新完成。"',
        'sysup_rebootreq': 'sysup_rebootreq="清理和更新完成。需要重新启动才能使更新生效。"'
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
    
    print("Adding system update translations to all language files...")
    print("=" * 70)
    
    for filename, translations in TRANSLATIONS.items():
        filepath = os.path.join(LANG_DIR, filename)
        
        if os.path.exists(filepath):
            print(f"Processing {filename}...")
            added, skipped = add_translations_to_file(filepath, translations)
            total_added += added
            total_skipped += skipped
            
            if added > 0:
                print(f"  ✓ Added {added} translations")
            if skipped > 0:
                print(f"  ⊘ Skipped {skipped} (already exist)")
        else:
            print(f"✗ File not found: {filepath}")
            errors += 1
    
    print("=" * 70)
    print("Summary:")
    print(f"  Total added: {total_added}")
    print(f"  Total skipped: {total_skipped}")
    print(f"  Files with errors: {errors}")
    print(f"  Total files processed: {len(TRANSLATIONS)}")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import json
import os
import sys

# LinuxToys languages. English is normally already present in the descriptions file.
LANGUAGES = (
    "am", "ar", "az", "bg", "bn", "bs", "cs", "da", "de", "el", "es", "et",
    "fa", "fi", "fr", "ga", "he", "hi", "hr", "hu", "hy", "id", "is", "it",
    "ja", "ka", "km", "ko", "lo", "lt", "lv", "mn", "ms", "my", "nb", "ne",
    "nl", "pl", "pt", "ro", "ru", "sk", "sl", "sq", "sr", "sv", "sw", "ta",
    "tg", "th", "tl", "tr", "uk", "ur", "uz", "vi", "zh",
)

# Fill this dictionary in the translation step.
#
# The key is the description tag from the target descriptions.json and each value is
# a language -> translated short-description mapping, following the same layout used
# by the old translate_json.py helper.
#
# Example:
# translations = {
#     "vkvolt_desc": {
#         "am": "...",
#         "ar": "...",
#         ...
#         "pt": "Painel de controle para jogos Vulkan no Linux, uma alternativa ao AMD Adrenalin e NVIDIA Settings para Linux.",
#         ...
#         "zh": "...",
#     },
# }
translations = {
    "punktfunk_client_desc": {
        "am": "የPunktfunk ጨዋታ ዥረት ደንበኛ ክፍል።",
        "ar": "جانب العميل لبث الألعاب عبر Punktfunk.",
        "az": "Punktfunk oyun yayımı üçün klient tərəfi.",
        "bg": "Клиентска страна за стрийминг на игри с Punktfunk.",
        "bn": "Punktfunk গেম স্ট্রিমিংয়ের ক্লায়েন্ট অংশ।",
        "bs": "Klijentska strana za Punktfunk streaming igara.",
        "cs": "Klientská část pro streamování her pomocí Punktfunk.",
        "da": "Klientside til Punktfunk-spilstreaming.",
        "de": "Client-Seite für Punktfunk-Game-Streaming.",
        "el": "Η πλευρά πελάτη για streaming παιχνιδιών με το Punktfunk.",
        "es": "Componente cliente para la transmisión de juegos con Punktfunk.",
        "et": "Punktfunki mängude voogedastuse kliendipool.",
        "fa": "بخش کلاینت برای استریم بازی با Punktfunk.",
        "fi": "Punktfunk-pelisuoratoiston asiakaspuoli.",
        "fr": "Composant client pour le streaming de jeux avec Punktfunk.",
        "ga": "Taobh cliaint do shruthú cluichí Punktfunk.",
        "he": "צד הלקוח להזרמת משחקים באמצעות Punktfunk.",
        "hi": "Punktfunk गेम स्ट्रीमिंग के लिए क्लाइंट साइड।",
        "hr": "Klijentska strana za Punktfunk streaming igara.",
        "hu": "Kliensoldali komponens Punktfunk játékstreameléshez.",
        "hy": "Punktfunk խաղերի հեռարձակման հաճախորդային կողմը։",
        "id": "Sisi klien untuk streaming game Punktfunk.",
        "is": "Biðlarahlið fyrir Punktfunk-leikjastreymi.",
        "it": "Componente client per lo streaming di giochi con Punktfunk.",
        "ja": "Punktfunk ゲームストリーミングのクライアント側コンポーネント。",
        "ka": "კლიენტის მხარე Punktfunk-ით თამაშების სტრიმინგისთვის.",
        "km": "ផ្នែកម៉ាស៊ីនភ្ញៀវសម្រាប់ការស្ទ្រីមហ្គេម Punktfunk។",
        "ko": "Punktfunk 게임 스트리밍용 클라이언트 측 구성 요소입니다.",
        "lo": "ຝັ່ງໄຄລເອັນສຳລັບການສະຕຣີມເກມດ້ວຍ Punktfunk.",
        "lt": "Punktfunk žaidimų transliavimo kliento dalis.",
        "lv": "Klienta puse Punktfunk spēļu straumēšanai.",
        "mn": "Punktfunk тоглоом стриймингийн клиент тал.",
        "ms": "Bahagian klien untuk penstriman permainan Punktfunk.",
        "my": "Punktfunk ဂိမ်း streaming အတွက် client ဘက်ခြမ်း။",
        "nb": "Klientside for Punktfunk-spillstrømming.",
        "ne": "Punktfunk गेम स्ट्रिमिङका लागि क्लाइन्ट पक्ष।",
        "nl": "Clientcomponent voor gamestreaming met Punktfunk.",
        "pl": "Część klienta do strumieniowania gier przez Punktfunk.",
        "pt": "Componente cliente para streaming de jogos com o Punktfunk.",
        "ro": "Componentă client pentru streaming de jocuri cu Punktfunk.",
        "ru": "Клиентский компонент для трансляции игр через Punktfunk.",
        "sk": "Klientská časť na streamovanie hier pomocou Punktfunk.",
        "sl": "Odjemalska stran za pretakanje iger s Punktfunk.",
        "sq": "Ana e klientit për transmetimin e lojërave me Punktfunk.",
        "sr": "Клијентска страна за Punktfunk стримовање игара.",
        "sv": "Klientsida för Punktfunk-spelströmning.",
        "sw": "Upande wa mteja kwa utiririshaji wa michezo wa Punktfunk.",
        "ta": "Punktfunk கேம் ஸ்ட்ரீமிங்கிற்கான கிளையன்ட் பகுதி.",
        "tg": "Қисми муштарӣ барои пахши бозиҳо бо Punktfunk.",
        "th": "ฝั่งไคลเอนต์สำหรับการสตรีมเกมด้วย Punktfunk",
        "tl": "Client side para sa Punktfunk game streaming.",
        "tr": "Punktfunk oyun akışı için istemci tarafı.",
        "uk": "Клієнтський компонент для трансляції ігор через Punktfunk.",
        "ur": "Punktfunk گیم اسٹریمنگ کے لیے کلائنٹ سائیڈ۔",
        "uz": "Punktfunk o'yin strimingi uchun klient tomoni.",
        "vi": "Phía máy khách cho tính năng phát trực tuyến trò chơi Punktfunk.",
        "zh": "Punktfunk 游戏串流的客户端。"
    },
}


def resolve_target(argument: str) -> str:
    """Resolve either a direct path or a path relative to ../p3/scripts/lists."""
    if os.path.isfile(argument):
        return os.path.abspath(argument)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    lists_dir = os.path.normpath(os.path.join(script_dir, "..", "p3", "scripts", "lists"))
    candidate = os.path.join(lists_dir, argument)

    if os.path.isfile(candidate):
        return candidate

    raise FileNotFoundError(
        f"Could not find '{argument}' directly or under '{lists_dir}'."
    )


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: python3 {os.path.basename(sys.argv[0])} <path/to/descriptions.json>")
        print(f"Example: python3 {os.path.basename(sys.argv[0])} volt/descriptions.json")
        return 2

    try:
        target = resolve_target(sys.argv[1])
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    try:
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Error reading {target}: {exc}", file=sys.stderr)
        return 1

    description_tag = data.get("description_tag")
    if not isinstance(description_tag, str) or not description_tag:
        print(f"Error: {target} has no valid 'description_tag'.", file=sys.stderr)
        return 1

    lang_translations = translations.get(description_tag)
    if lang_translations is None:
        print(
            f"Error: no translations were provided for '{description_tag}' in translations.",
            file=sys.stderr,
        )
        return 1

    unknown = sorted(set(lang_translations) - set(LANGUAGES) - {"en"})
    if unknown:
        print(
            "Error: unsupported language code(s): " + ", ".join(unknown),
            file=sys.stderr,
        )
        return 1

    written = 0
    missing = []

    for lang in LANGUAGES:
        translation = lang_translations.get(lang)
        if not isinstance(translation, str) or not translation.strip():
            missing.append(lang)
            continue

        section = data.get(lang)
        if section is None:
            section = {}
            data[lang] = section
        elif not isinstance(section, dict):
            print(
                f"Error: language section '{lang}' is not a JSON object.",
                file=sys.stderr,
            )
            return 1

        # Only touch the short-description key. Existing long-description paths and
        # any other per-language metadata are preserved.
        section[description_tag] = translation
        written += 1

    if missing:
        print(
            "Error: translations are missing for: " + ", ".join(missing),
            file=sys.stderr,
        )
        print("No changes were written.", file=sys.stderr)
        return 1

    try:
        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except OSError as exc:
        print(f"Error writing {target}: {exc}", file=sys.stderr)
        return 1

    print(f"Added {written} translations for '{description_tag}' to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

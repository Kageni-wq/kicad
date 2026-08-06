import gettext
import os
import locale

def init_locale(lang: str = 'Default'):
    if lang == 'Русский':
        lang = "ru"
    elif lang == 'Default':
        temp = locale.getlocale(category=locale.LC_CTYPE)
        if 'Rus' in temp[0]:
            lang = "ru"
        else:
            lang = "en"
    else:
        lang = "en"

    BASE_DIR = os.path.dirname(__file__)
    LOCALE_DIR = os.path.join(BASE_DIR, 'ui', 'locales')

    translation = gettext.translation(
        domain='copper_filler',
        localedir=LOCALE_DIR,
        languages=[lang],
        fallback=True
    )

    translation.install()
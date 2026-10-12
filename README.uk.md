<div align="center">

<img src="src/changeimagehash/assets/icon.png" width="96" alt="Іконка Change Image Hash">

# Change Image Hash

**Новий MD5 і SHA-256 для будь-якого зображення, і при цьому жоден піксель не змінюється.**

[![CI](https://github.com/SilentCasting/ChangeImagehashMD5/actions/workflows/ci.yml/badge.svg)](https://github.com/SilentCasting/ChangeImagehashMD5/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/SilentCasting/ChangeImagehashMD5)](https://github.com/SilentCasting/ChangeImagehashMD5/releases/latest)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

[English](README.md) · Українська

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/screenshot-dark.png">
  <img src="docs/screenshot-light.png" width="820" alt="Вікно Change Image Hash зі списком оброблених зображень і їхніми MD5 до та після">
</picture>

</div>

## Навіщо

Багато систем розпізнають файли за контрольною сумою: сервіси завантаження,
кеші, інструменти бекапу та дедуплікації. Дві копії одного зображення завжди
мають однаковий MD5, тому їх вважають одним файлом. Change Image Hash робить
кожну копію унікальною на рівні байтів, але вона **виглядає точно так само**.

Типові сценарії:

- тестування завантаження, CDN і дедуплікації на «різних» файлах;
- скидання кешу, який прив'язаний до хешу файлу;
- кілька незалежних копій одного зображення.

## Можливості

- 🖱️ **Drag & drop**: перетягуйте у вікно файли або цілі папки
- 📦 **Пакетна обробка**, зокрема з підпапками
- 🔍 Таблиця **MD5 до / після**: подвійний клік копіює хеш, правий клік дає SHA-256
- 🛡️ **Оригінали в безпеці**: за замовчуванням зберігається копія `photo_unique.png`
- ✅ **Файли лишаються коректними**: дані пишуться у штатні блоки метаданих, де це можливо
- 🖼️ PNG, JPG/JPEG/JFIF, GIF, WEBP, BMP, TIFF або будь-які файли з опцією «All file types»
- 🌗 Світла й темна тема
- ⌨️ **Командний рядок** для скриптів і автоматизації
- 💾 **Портативний `.exe`** для Windows, Python не потрібен

## Завантаження

Скачайте **`ChangeImageHash.exe`** з
[останнього релізу](https://github.com/SilentCasting/ChangeImagehashMD5/releases/latest)
і запустіть. Встановлювати нічого не треба.

> Windows SmartScreen може попередити про невідомого видавця, бо exe не
> підписаний сертифікатом. Натисніть **Докладніше → Усе одно запустити**
> або зберіть програму з коду самостійно (див. нижче).

## Встановлення з коду

Потрібен Python 3.10+.

```bash
git clone https://github.com/SilentCasting/ChangeImagehashMD5.git
cd ChangeImagehashMD5
pip install .
```

Після цього з'являться дві команди: `changeimagehash-gui` (програма) і
`changeimagehash` (командний рядок).

## Використання

### Програма

```bash
changeimagehash-gui
```

1. Перетягніть у вікно зображення чи папки або натисніть **Add files… / Add folder…**.
2. Виберіть **Save a copy** (зберегти копію, за замовчуванням) або **Overwrite original** (перезаписати оригінал).
3. Натисніть **Change hashes**.
4. Подвійний клік по рядку копіює новий MD5. Правий клік дає новий SHA-256,
   старий MD5, **Show in folder** (показати в папці) і **Remove from list** (прибрати зі списку).

Файли можна також перетягнути прямо на `ChangeImageHash.exe`, і вони відкриються в програмі.

### Командний рядок

```bash
# Зберегти photo_unique.png поруч із photo.png
changeimagehash photo.png

# Усі зображення в папці та підпапках, копії в ./out
changeimagehash ./pictures -r -o ./out

# Змінити самі оригінали
changeimagehash *.jpg --overwrite

# Вивід у JSON
changeimagehash photo.png --json
```

| Опція | Опис |
| --- | --- |
| `--overwrite` | Змінювати оригінали замість створення копій |
| `-o, --output-dir DIR` | Зберігати копії в `DIR` |
| `--suffix TEXT` | Суфікс для копій (за замовчуванням `_unique`) |
| `-r, --recursive` | Обробляти й підпапки |
| `--all-files` | Обробляти в папках усі файли, не лише зображення |
| `--json` | Вивести результат у JSON |

Коди виходу: `0` успіх, `1` частина файлів не оброблена, `2` нема що робити або неправильні аргументи.

## Як це працює

У файл записуються 32 випадкові hex-символи. Вони потрапляють у місце, яке
переглядачі пропускають, тож пікселі не змінюються, а байти (і хеш) стають іншими.

| Формат | Куди йдуть випадкові дані | Файл відповідає специфікації |
| --- | --- | :---: |
| PNG | Чанк `tEXt` з назвою `ChangeImageHash` перед `IEND` | ✅ |
| JPEG | Сегмент-коментар `COM` після заголовків JFIF/EXIF | ✅ |
| GIF | Розширення-коментар перед кінцевим байтом (GIF87a оновлюється до 89a) | ✅ |
| WEBP, BMP, TIFF, інші | Дописуються після кінця даних зображення | Декодери їх ігнорують |

Щоразу генеруються нові випадкові дані, тому те саме зображення, оброблене
двічі, отримає два різні хеші. EXIF та інші метадані зберігаються.

> **Важливо:** змінюються *криптографічні* хеші (MD5, SHA-1, SHA-256 тощо).
> *Перцептивні* хеші (pHash, dHash) і все, що порівнює саму картинку, не
> зміняться, бо картинка навмисно лишається ідентичною.

## Розробка

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -e ".[dev,build]"

pytest                          # тести
ruff check . && ruff format .   # лінтер і форматування
python packaging/build_exe.py   # зібрати dist/ChangeImageHash.exe
```

Тести створюють справжні зображення в кожному форматі, змінюють їм хеш і
через Pillow перевіряють, що всі пікселі лишилися ідентичними.

Щоб випустити нову версію, оновіть `__version__` у `src/changeimagehash/__init__.py`
та `CHANGELOG.md` і запуште тег (`git tag v1.0.0 && git push origin v1.0.0`).
GitHub Actions прожене тести, збере exe і опублікує реліз.

## Ліцензія

[MIT](LICENSE) © SilentCasting

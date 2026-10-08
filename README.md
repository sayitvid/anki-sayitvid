# SayItVid — Anki Desktop Add-on

[![Anki Version](https://img.shields.io/badge/Anki-2.1.50+-blue.svg)](https://apps.ankiweb.net/)
[![Python](https://img.shields.io/badge/Python-3.9+-brightgreen.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![SayItVid](https://img.shields.io/badge/Powered%20By-SayItVid.com-e11d48.svg)](https://sayitvid.com)

> **Native English pronunciations, 100% offline audio downloads, IPA, stressed syllables, CEFR difficulty levels, and authentic timestamped video clips for your Anki flashcards.**

---

## 🌟 Key Features

1. **100% Offline Audio Downloader (Forvo Alternative)**
   - Automatically downloads native `.mp3` audio files directly into Anki's `collection.media`.
   - Inserts `[sound:sayitvid_word_accent.mp3]` so pronunciation audio plays completely offline on **Anki Desktop**, **AnkiMobile (iOS)**, and **AnkiDroid (Android)**.
   - Switch seamlessly between **US (American)**, **UK (British)**, and **AUS (Australian)** accents.

2. **Contextual Speech Video Clips (YouGlish Alternative)**
   - Embeds authentic YouTube video clips starting at the exact second where the word is spoken in natural conversation (interviews, TED talks, science lectures, and news).
   - Shows the transcript sentence with the target word highlighted and before/after sentence context.

3. **Linguistic Intelligence**
   - **IPA Phonetics**: Accurate International Phonetic Alphabet transcriptions (e.g. `/ˈkɜːrɪdʒ/`).
   - **Syllables & Primary Stress**: Visual syllable breakdown with primary stress bolded in brand color (e.g. `cour · <b class="sayitvid-stress">AGE</b>`).
   - **CEFR Difficulty Levels**: Automatic tagging (`CEFR:A1` through `CEFR:C2`) for vocabulary level tracking.
   - **Heteronyms & Homophones**: Visual badges and alerts for words with variable pronunciation.
   - **Definitions & Part of Speech**: Instant lexical definitions.

4. **Zero-Configuration & Non-Destructive**
   - **Standard Decks**: Works out-of-the-box on standard 2-field cards (`Front` / `Back`). It compiles a clean, responsive composite card block on the back.
   - **Preserves Your Existing Notes**: If your card already has translations or study notes, SayItVid appends below a clean dashed divider without erasing your work.
   - **Advanced Decks**: Supports custom multi-field setups (separate target fields for Audio, IPA, Syllables, Definition, Sentence, Video, CEFR).

5. **Dynamic Card Template Filter**
   - Add `{{sayitvid:Front}}` to any Card Template for live, interactive video and audio playback during reviews without modifying your note database.

---

## 🚀 Installation

### Method 1: Install from `.ankiaddon` File (Recommended)
1. Download the latest `sayitvid.ankiaddon` from the [Releases](https://github.com/sayitvid/anki-sayitvid/releases) tab (or clone the repository).
2. Open **Anki Desktop**.
3. Go to **Tools** → **Add-ons**.
4. Click **Install from file...** in the bottom-right corner.
5. Select `sayitvid.ankiaddon` and restart Anki.

### Method 2: Git Clone (For Developers)
Clone this repository directly into your Anki `addons21` directory:

* **macOS**:
  ```bash
  git clone https://github.com/sayitvid/anki-sayitvid.git ~/Library/Application\ Support/Anki2/addons21/sayitvid
  ```
* **Windows** (PowerShell):
  ```powershell
  git clone https://github.com/sayitvid/anki-sayitvid.git "$env:APPDATA\Anki2\addons21\sayitvid"
  ```
* **Linux**:
  ```bash
  git clone https://github.com/sayitvid/anki-sayitvid.git ~/.local/share/Anki2/addons21/sayitvid
  ```
Restart Anki after cloning.

---

## 🛠️ How to Use

### 1. Single Note Quick Enrich (Note Editor)
* When creating or editing a flashcard in the **Add** or **Edit** window, press **`F8`** (or click the **SayItVid** icon in the editor toolbar).
* The current note is immediately populated with native audio, phonetic data, and video context.

### 2. Batch Enrich Existing Cards (Note Browser)
1. Open the Anki **Browse** window (`B`).
2. Select any number of cards (e.g. 50 cards).
3. Select **Edit** → **SayItVid: Enrich Selected Notes...** (or press **`Ctrl+Shift+S`** / **`Cmd+Shift+S`**).
4. Review your field mappings and selected accent.
5. Click **Start Enrichment** and watch the live progress bar as audio files are saved to `collection.media`.

### 3. Dynamic Card Template Filter
To display the interactive SayItVid player dynamically during reviews without altering your card fields, add this to your **Card Back Template**:

```html
{{Front}}
<hr id="answer">
{{Back}}

<!-- Dynamic SayItVid Video Player -->
{{sayitvid:Front}}
```

---

## ⚙️ Configuration

Go to **Tools** → **Add-ons** → select **SayItVid** → click **Config**:

| Option | Type | Default | Description |
|---|---|---|---|
| `api_base_url` | string | `"https://sayitvid.com"` | API endpoint for linguistic and clip lookups |
| `api_key` | string | `""` | Optional API key for higher batch enrichment quotas |
| `default_accent` | string | `"us"` | Default accent: `"us"`, `"uk"`, or `"aus"` |
| `download_audio` | boolean | `true` | Download native MP3 into `collection.media` |
| `overwrite_existing` | boolean | `false` | Overwrite non-empty fields during enrichment |
| `tag_cefr` | boolean | `true` | Automatically add CEFR tags (e.g. `CEFR:B2`) |
| `video_embed_width` | number | `560` | Width of embedded video iframe |
| `video_embed_height`| number | `315` | Height of embedded video iframe |
| `field_mappings` | object | *see defaults* | Map SayItVid attributes to your deck's field names |

---

## 📦 Building from Source

To package the add-on into a distributable `.ankiaddon` file:

```bash
chmod +x build.sh
./build.sh
```

This creates `sayitvid.ankiaddon` in the root folder, ready to be shared or uploaded.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

Powered by [SayItVid.com](https://sayitvid.com) — Free native pronunciation search engine and video dictionary.

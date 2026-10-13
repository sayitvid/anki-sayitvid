# SayItVid — Anki Desktop Add-on

> Authentic video pronunciation widgets, interactive native clips, and synchronized subtitles for Anki flashcards.

---

## 🌟 Key Features

1. **Interactive Embed Widget (YouGlish / Aglish alternative)**:
   * Embeds SayItVid's responsive HTML5 video player into Anki cards.
   * Plays authentic timestamped video clips from TED, BBC, podcasts, and interviews.
   * Displays highlighted subtitle context and playback controls.
2. **Zero Configuration & Zero API Keys**:
   * Works out of the box with zero setup—no accounts or API keys required.
   * All player improvements and features deployed to SayItVid update automatically in your cards.
3. **Dynamic Card Template Filter (`{{sayitvid:Front}}`)**:
   * Add `{{sayitvid:Front}}` to your card template to stream pronunciation videos on-the-fly during reviews without altering your note fields.
   * Supports custom accents and themes: `{{sayitvid accent=uk theme=dark:Front}}`.
4. **Batch Note Enrichment & Toolbar Button**:
   * Embed the widget into selected notes via the Note Browser (`Ctrl+Shift+S`).
   * One-click toolbar button in the Note Editor (`F8`).

---

## 🚀 Installation

### Method A: Install `.ankiaddon` Package
1. Download or build `sayitvid.ankiaddon`.
2. In Anki Desktop, go to **Tools > Add-ons > Install from file...** and select `sayitvid.ankiaddon`.
3. Restart Anki.

### Method B: Development Symlink (macOS / Linux / Windows)
On macOS:
```bash
ln -s "$(pwd)/anki/sayitvid" ~/Library/Application\ Support/Anki2/addons21/sayitvid
```
On Windows:
```cmd
mklink /D "%APPDATA%\Anki2\addons21\sayitvid" "%CD%\anki\sayitvid"
```
On Linux:
```bash
ln -s "$(pwd)/anki/sayitvid" ~/.local/share/Anki2/addons21/sayitvid
```

---

## 🛠️ Usage

### 1. Dynamic Card Template (Recommended — Zero Note Changes)
Open your Note Type editor in Anki (**Tools > Manage Note Types > Cards...**) and add the following to your **Back Template**:

```html
{{Front}}
<hr id="answer">
{{Back}}

<!-- SayItVid Interactive Video Player -->
{{sayitvid:Front}}
```

#### Custom Options:
* **British Accent**: `{{sayitvid accent=uk:Front}}`
* **Australian Accent**: `{{sayitvid accent=aus:Front}}`
* **Dark Theme**: `{{sayitvid theme=dark:Front}}`
* **Combined**: `{{sayitvid accent=uk theme=dark:Front}}`

### 2. Batch Embed into Notes (Note Browser)
1. Open the **Browse** window in Anki (`B`).
2. Select any number of cards.
3. Select **Edit > SayItVid: Embed Widgets in Selected Notes...** (or press `Ctrl+Shift+S`).
4. Select your target field (e.g. `Video` or `SayItVid`) and click **Embed Widgets**.

### 3. Note Editor Quick Button
While editing a card, click the **SayItVid** toolbar button or press `F8` to embed the widget into your note's video field.

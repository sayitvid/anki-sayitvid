# SayItVid Anki Add-on Configuration

### `base_url`
* Default: `"https://sayitvid.com"`
* The base domain for loading SayItVid video widgets.

### `default_accent`
* Options: `"us"` (American English), `"uk"` (British English), `"aus"` (Australian English), `"ca"` (Canadian English).
* Sets the default pronunciation and video accent for the widget.

### `theme`
* Options: `"auto"` (Match System / Anki Night Mode), `"dark"`, `"light"`.
* Controls the color scheme of the embedded video player.

### `overwrite_existing`
* Default: `false`
* When set to `false`, batch embedding will never overwrite non-empty fields in existing cards.

### `field_mappings`
Configure field destinations:
* `source_word`: The field containing the word or phrase (e.g. `Front`, `Word`, `Text`).
* `target_video`: Where to store the SayItVid video widget (e.g. `Video`, `SayItVid`, `Back`).

---

### Dynamic Template Filter (Recommended)
You do not even need to modify notes in your database. Simply add this tag to your Card Back template:
```html
{{sayitvid:Front}}
```
With custom options:
```html
{{sayitvid accent=uk theme=dark:Front}}
```

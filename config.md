# SayItVid Anki Add-on Configuration

### `api_base_url`
* Default: `"https://sayitvid.com"`
* The base URL for SayItVid API calls. Set to a custom domain or localhost if running a self-hosted instance.

### `api_key`
* Default: `""` (Leave blank to use the free daily search quota).
* If you have a registered SayItVid account or API key, enter it here for higher batch limits.

### `default_accent`
* Options: `"us"` (American English), `"uk"` (British English), `"aus"` (Australian English).
* Sets the default pronunciation and video accent.

### `download_audio`
* Default: `true`
* When enabled, downloads clean native `.mp3` audio recordings into Anki's `collection.media` folder, inserting `[sound:filename.mp3]` into your audio field for 100% offline playback.

### `overwrite_existing`
* Default: `false`
* When set to `false`, SayItVid will never overwrite non-empty fields in existing cards.

### `field_mappings`
Configure which fields in your note types receive each piece of information:
* `source_word`: The field containing the English word or phrase (e.g. `Front`, `Word`, `Text`).
* `target_audio`: Where to store the `[sound:...]` tag (e.g. `Audio`, `Pronunciation`).
* `target_ipa`: Where to store the phonetic transcription (e.g. `IPA`, `Phonetics`).
* `target_syllables`: Where to store formatted syllables with primary stress highlighted (e.g. `Syllables`).
* `target_definition`: Where to store dictionary definition (e.g. `Definition`, `Meaning`).
* `target_sentence`: Where to store contextual subtitle sentence (e.g. `Sentence`, `Example`).
* `target_video`: Where to store the SayItVid video embed iframe or deep link (e.g. `Video`).
* `target_cefr`: Where to store CEFR difficulty tag (e.g. `CEFR`, `Level`).

### `tag_cefr`
* Default: `true`
* Automatically adds CEFR tags (e.g. `CEFR:B1`) to the note for easy filtering in the deck browser.

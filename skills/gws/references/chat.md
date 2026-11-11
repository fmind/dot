# Google Chat content and threads

Lead with one sentence, a few bullets, and a link—replacing headings with bold labels, tables with bullets or a Sheet link, and language-tagged fences with bare ` ``` ` fences. Pick one syntax per message:

| Element     | Native Chat (default)          | Markdown mode                  |
| ----------- | ------------------------------ | ------------------------------ |
| Bold        | `*bold*`                       | `**bold**`                     |
| Italic      | `_italic_`                     | `*italic*`                     |
| Strike      | `~strike~`                     | `~~strike~~`                   |
| Link        | `<https://example.com\|Label>` | `[Label](https://example.com)` |
| Bullets     | `- Item`                       | `- Item`                       |
| Inline code | Single backticks               | Single backticks               |

Always set `markupSyntax` (`MARKUP_SYNTAX_CHAT` default vs `MARKUP_SYNTAX_MARKDOWN`), since omitting it falls back to Markdown when no Chat app is configured and turns `*bold*` into italics. Never set output-only `formattedText`; author user-authenticated messages as text (cards use separate HTML rules):

```bash
python3 -I ~/.agents/skills/gws/scripts/chat_body.py message.txt > body.json
python3 -I ~/.agents/skills/gws/scripts/chat_body.py message.md --syntax markdown > body.json
```

Audit nested/escaped delimiters, images, and mentions (`<users/ID>` in native Chat, `chat-user` in Markdown; resolve user IDs explicitly and never mention `@all` unasked).

## Reply to an existing thread

Observe `thread.name` (`spaces/SPACE/threads/THREAD`, distinct from `message.name` and app thread keys), pass `--thread spaces/SPACE/threads/THREAD` to `chat_body.py`, and set `parent` + `messageReplyOption: "REPLY_MESSAGE_OR_FAIL"` in `--params` so bad references fail closed instead of opening a new thread. Preview via `--dry-run`, keep a stable `requestId` for retries, and verify authorized sends with `gws chat spaces messages get --params '{"name":"spaces/SPACE/messages/MESSAGE"}'` (`text`, `formattedText`, `thread`, `markupSyntax`)—never send test messages without explicit approval.

Sources: [Message formatting](https://developers.google.com/workspace/chat/format-messages), [Message resource](https://developers.google.com/workspace/chat/api/reference/rest/v1/spaces.messages), [Create and reply](https://developers.google.com/workspace/chat/api/reference/rest/v1/spaces.messages/create).

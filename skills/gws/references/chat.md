# Google Chat content and threads

Default to a short opening sentence, a few parallel bullets and one relevant link. Replace document headings with bold labels and tables with labeled bullets or a linked Sheet. Use blank lines between sections and bare triple-backtick code fences without a language label. Do not send a Markdown document unchanged and expect every feature to render.

Choose one syntax for the entire text body:

| Element | Native Chat (default) | Markdown mode |
| --- | --- | --- |
| Bold | `*bold*` | `**bold**` |
| Italic | `_italic_` | `*italic*` |
| Strike | `~strike~` | `~~strike~~` |
| Link | `<https://example.com|Label>` | `[Label](https://example.com)` |
| Bullets | `- Item` | `- Item` |
| Inline code | Single backticks | Single backticks |

Current Chat documentation and the observed discovery schema expose `markupSyntax`; `MARKUP_SYNTAX_MARKDOWN` selects Markdown interpretation. Confirm availability in the current schema/account before relying on it. Native Chat remains the portable default. Do not set `formattedText`: it is output-only. Text messages use this markup; card text uses a separate HTML subset, and card capabilities depend on authentication. Author user-authenticated messages as text unless the current API explicitly supports the requested card operation.

```bash
# Authored native Chat text (default), or explicitly selected Markdown:
uv run --no-project python ~/.agents/skills/gws/scripts/chat_body.py message.txt > body.json
uv run --no-project python ~/.agents/skills/gws/scripts/chat_body.py \
  message.md --syntax markdown > body.json
```

The helper validates common mistakes without rewriting prose or code. It is not a complete markup parser: review images, HTML, nested/escaped delimiters and any unsupported syntax yourself. Native mentions use `<users/ID>`; Markdown mentions use the documented `chat-user` element. Resolve the intended identity rather than guessing display names, and never add an all-space mention unless requested. The helper preserves mentions already in the authored text, so include their notification effect in the content review.

## Reply to an existing thread

Resolve the destination space and exact `thread.name` from a previous message. They are different from `message.name`. Build the body with `--thread spaces/SPACE/threads/THREAD`, set `parent` to that same space in params, and set `messageReplyOption` to `REPLY_MESSAGE_OR_FAIL`. This avoids accidentally starting a new thread if the reference is wrong. A thread key is an alternative app-defined identity, not a substitute for an observed thread name.

Use the file-based request workflow for preview and authorized sending. Keep a stable `requestId` when retries may be needed. Read the returned message with `gws chat spaces messages get --params '{"name":"spaces/SPACE/messages/MESSAGE"}'`; inspect `text`, `formattedText`, `thread` and `markupSyntax` as returned. API state confirms accepted content and location; inspect Chat UI when claiming rendered appearance. Do not send a test message just to verify a skill change without explicit sending authority.

Sources: [Message formatting](https://developers.google.com/workspace/chat/format-messages), [Message resource](https://developers.google.com/workspace/chat/api/reference/rest/v1/spaces.messages), [Create and reply](https://developers.google.com/workspace/chat/api/reference/rest/v1/spaces.messages/create).

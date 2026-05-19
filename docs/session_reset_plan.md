# Telegram Session Reset Plan

## Goal

Give each Telegram user a way to wipe their own conversation session so future messages are sent to the model without the previous chat history from `SESSIONS.json`.

## User Interface

Add Telegram commands:

- `/reset`
- `/reset_session`
- `/wipe_session`

All three commands do the same thing: clear the session history for the current Telegram chat and send a short confirmation message.

## Scope

The reset only affects the requesting Telegram chat session:

- It clears that session's `history`.
- It preserves the session metadata, such as `client_id`, `channel`, and `created_at`.
- It does not clear `MEMORY.json`.
- It does not affect other Telegram chats.

This separation is intentional because session history is short-term conversation context, while memory is explicit long-term user memory.

## Implementation Steps

1. Add a `clear_history(session_id)` method to `SessionManager`.
2. Register Telegram command handlers before the normal text message handler.
3. Exclude Telegram commands from the normal text handler so reset commands are not sent to the LLM.
4. In the reset handler:
   - derive the current Telegram `session_id`
   - clear that session's history
   - persist `SESSIONS.json`
   - reply with confirmation
   - log the reset
5. Run syntax checks for the changed files.

## Expected Behavior

Before reset, a Telegram message includes prior history from `SESSIONS.json`.

After `/reset`, the next normal Telegram message starts with an empty session history except for that new message. The model should no longer infer personal details from old session messages, unless those details also exist in `MEMORY.json`.

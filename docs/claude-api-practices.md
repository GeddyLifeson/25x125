# Claude API practices (from the Combining Games project)

Every session working on 25x125 reads this before calling the Claude API or planning bulk model work.

Copied 2026-11-01 from Marlon's Combining Games project. The master text there is `/mnt/project-files/CLAUDE.md` section 1 in that project's own shared folder. That folder is not mounted in this project, and the file is not committed to any repo, so this copy is built from what the repos do carry:

- `GeddyLifeson/DiaithirRPG`, branch `claude/project-thread-wixpzc`, commit `567f979`: `CLAUDE.md` (essentials), `tools/compute/README.md`, `tools/compute/api_lane/README.md`, `tools/compute/api_lane/{watch,batch,sync,common,recover}.py`, `.claude/skills/free-compute/SKILL.md`.
- `GeddyLifeson/diaithir-ports` and `GeddyLifeson/diaithir-laptop`, same branch name: CLAUDE.md files that point to the master and repeat the same essentials.

Facts about the API (prices, cache minimums, Batch limits) were checked against Anthropic's API reference on 2026-11-01. If Marlon uploads the master file, replace this copy with its section 1 and keep the 25x125 notes at the end.

## 1. Routing order

1. **Scripts first.** Anything a regex, lookup, sum or join can do is a script, not a model call. (25x125 rule: the engine computes; models only read text we can't parse.)
2. **Free lanes next.** In Combining Games this is ModelRouter on Marlon's desktop (port 11435) and free hosted pools. 25x125 has no free lane yet; do not add one without Marlon. No local models on his PC or laptop.
3. **Claude API job, Batch first.** Bulk work goes to the API as a batch on the small model (`claude-haiku-5-5`). Use Sonnet or Opus only where a sample shows the small model gets it wrong.
4. **Claude session last.** Session tokens are the scarce resource. Spend them on design, judgment and integration, never on row-by-row bulk calls the API can do.

## 2. Batch for bulk

- Message Batches cost 50% of list price. Limits: 100,000 requests or 256 MB per batch; most finish within an hour, maximum 24 hours; results are kept 29 days.
- Rule from the Combining Games watcher: Haiku jobs always go to Batch. Sonnet or Opus jobs of 40 rows or more go to Batch unless the job says `sync` (needs results now).
- Results come back in any order. Key them by `custom_id`, never by position.
- Save batch ids to disk as soon as they are submitted. A restarted container must be able to collect results from batches whose runner died (`recover.py` in DiaithirRPG does this).
- Make jobs resumable: skip rows already in the output file.

## 3. Prompt caching with the 1-hour TTL

- Put the stable text first: system prompt, then the instructions shared by every row, then the row's own content.
- Mark the end of the shared part with `"cache_control": {"type": "ephemeral", "ttl": "1h"}`. Use the 1-hour TTL because batch requests and parallel runs can be spread out over more than 5 minutes.
- Only text of at least 512 tokens caches on the current models (Haiku 5.5, Sonnet 5.5, Opus 5.5). Shorter prefixes are ignored without an error. The Combining Games code caches only when the shared part is over about 2,400 characters.
- Cost: a 1-hour cache write is 2x the input price, a read is about 0.1x (0.05x on Opus 5.5). It pays off from the third request that shares the prefix.
- For direct (non-batch) runs, send one request first to write the cache, then start the parallel requests so they read it.
- Check `usage.cache_read_input_tokens`. If it stays at zero, something in the prefix changes per request (a date, a row id, unsorted JSON).

## 4. Files API

- Upload a file once (`POST /v1/files`, no beta header now) and send its `file_id` in each request instead of the bytes. Combining Games keeps a map of file hash to `file_id` so the same image or PDF is never uploaded twice.
- Fall back to base64 if the upload fails.
- Use `"type": "document"` for PDFs and text, `"type": "image"` for images. The block type must match the file type.

## 5. Structured outputs

- Ask for JSON with a schema: `"output_config": {"format": {"type": "json_schema", "schema": {...}}}`. The old `output_format` parameter is deprecated.
- Keep the schema in the job's folder (`schema.json`) next to the prompt so a rule change is a file edit.
- Effort goes in the same object: `"output_config": {"effort": "low"}`. Use `low` for extraction and classification.
- Structured outputs cannot be combined with citations.

## 6. Cost control

- Before any paid run, count tokens with `POST /v1/messages/count_tokens` (free) on one row, multiply by the row count, and price it at Batch rates. Write the estimate next to the job.
- Log every run's model, input tokens, output tokens, cache write tokens and cache read tokens. (Combining Games: `compute/ledger.csv`. 25x125: `docs/ai-runs.md`.)
- Thinking: on Haiku 5.5 send `"thinking": {"type": "disabled"}` for plain extraction (allowed at effort `high` or below). On Sonnet 5.5 the off setting is `{"type": "between_tools"}`. On Opus 5.5 thinking cannot be turned off; lower the effort instead. (The Combining Games batch code sends `between_tools` to every non-Haiku model, which Opus 5.5 rejects.)

## 7. The API key

- The key lives only in the `ANTHROPIC_API_KEY` environment variable. Never print it, commit it, or write it into a CLAUDE.md, PR, job file, log or memory.
- In Combining Games the key is read from a secrets file in that project's shared folder. That file is not in this project. For 25x125 the key goes in the cloud environment's secrets or in the local `.env` (see the repo CLAUDE.md).

## 25x125 rules that sit on top of these

- Warn Marlon before anything that costs money and give a dollar estimate. Runs over about $5 wait for his go-ahead.
- Model output is data to check, not a source. Store which model produced each value and the date, and spot-check a sample against the original before it reaches a screen.
- MLS (MRED) data never goes to any model.
- The Combining Games rules about Minecraft mods, the Panscriptum, ModelRouter lanes and desktop shortcuts do not apply here.

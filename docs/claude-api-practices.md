# Claude API practices (master copy from the Combining Games project)

Every session working on 25x125 reads this before calling the Claude API or planning bulk model work.

Source: section 1 of Marlon's master CLAUDE.md, copied word for word on 2026-11-01.
- Master: https://github.com/GeddyLifeson/DiaithirRPG/blob/engine/docs/MASTER_CLAUDE.md (section 1 checked identical on 2026-11-01, engine at 96644dd)

If the master changes, copy its section 1 again. Do not edit the copied section here; put 25x125 differences in the last section.

The master's routing order (its Essentials, item 1): ModelRouter and free lanes first, then the Claude API (job folder, Haiku Batch), then Claude sessions. Session tokens are the scarce resource; spend them on judgment and integration only.

---

## 1. Claude API practices (all lanes)
Where it runs: bulk text work is a job folder `/mnt/project-files/compute/jobs/<name>/` holding `in.jsonl` (`{id,prompt[,system][,images]}`) and a README. The watcher (compute-lanes thread, `tools/compute/api_lane/` in DiaithirRPG) claims it within ~1 minute and writes `out.jsonl` (`{id,text,lane}`) beside it. Owners validate and merge; failed rows go in `<name>-retry`. Lane map: `/mnt/project-files/compute/LANES.md`. Spend log: `/mnt/project-files/compute/ledger.csv` (`ts,job,model,input,output,cache_write,cache_read`).

Job README keys the watcher reads: `max_tokens N` (required), `model: haiku|sonnet|opus` (default haiku), `effort: low|medium|high|max`, the word `sync` (force direct calls). A `schema.json` beside `in.jsonl` turns on structured outputs.

Features in use, with why:
- **Batch API** (50% off, up to 100k requests per batch; we chunk at 1,500). Every bulk job. Sonnet/Opus jobs of 40+ rows also go Batch unless README says `sync`. Do not use `stream`, `speed` (fast mode) or `max_tokens: 0` in a batch.
- **Prompt caching, 1-hour TTL.** Put everything shared FIRST (instructions, rules, few-shot, source text), then the per-row part. The runner puts `cache_control` on the common prompt prefix when it is over ~2,400 characters (minimum cacheable is 512 tokens on the 5.5 models) and on any `system` over that size. Batch hits are best effort, so keep the 1h TTL. Changing `output_config.format` invalidates the cache. Check `usage.cache_read_input_tokens`: the ledger's last column should be large on every row but the first.
- **Model choice.** Batch prices per MTok in/out: Haiku 5.5 $0.05/$0.25 (default, classify, extract, rewrite, pick); Sonnet 5.5 $1/$5 (judgment, adjudication, fact checks); Opus 5.5 $2/$10 (hardest only); Fable 5.1 $5/$25 (almost never). Haiku 5.5 input costs 5x more above 100k tokens per prompt, so keep prompts small.
- **Thinking.** Off for Haiku (`disabled`), `between_tools` for Sonnet/Opus, or max_tokens is eaten and text comes back empty. Use `effort` instead to tune depth: `low` for simple extraction and picks.
- **Structured outputs** (`output_config.format` json_schema) for any job whose output is JSON (capitals lat/lon, photo picks, validators). Guarantees valid JSON and removes retry rows. Not compatible with citations or prefill.
- **Files API** for images: each image is uploaded once and referenced by `file_id` (map in `/tmp/claude-0/run/files.json`), instead of base64 per row. Shrinks batch payloads and re-uses uploads across the pick and review passes.
- **Token counting** (free `count_tokens`, text only; file sources are rejected) runs at claim time and writes `<job>/.estimate` with a ceiling cost, so large jobs are visible before spend.
- **Not used, on purpose:** citations (conflicts with schemas; assay text is grounded by giving real page text in the prompt), context editing and compaction, memory tool, tool use and agents, fast mode, task budgets, streaming. Our calls are single-turn and stateless. Revisit if a job becomes multi-turn.
- If the API would cost more than doing the work in a session, do it in the session. Never pad or invent rows to use credits.

After a container restart the watcher and runners die but submitted batches keep going on Anthropic's side: export the key from the secrets file (`export ANTHROPIC_API_KEY=$(cat /mnt/project-files/compute/secrets/anthropic_key)`), run `recover.py`, relaunch `watch.py` under `nohup bash -c 'while true; do python3 -I watch.py; sleep 5; done'`. The file is on a network mount, so chmod 600 is not enforced there; treat the whole `compute/secrets/` folder as private and never move it into a repo.

---

## How this applies in 25x125

Paths in the section above (`/mnt/project-files/compute/...`, the watcher, the ledger, the secrets file) live in the Combining Games project's shared folder. They do not exist in this project. In 25x125:

- **Where jobs run.** API jobs are Python jobs in `jobs/` (for example `jobs/extract_rezoning_districts.py`), using the same features: Batch, the 1-hour cache, structured outputs, the Files API for files sent more than once, and a free `count_tokens` estimate before submit.
- **Routing.** Scripts first (the engine computes; models only read text we can't parse), then a Haiku 5.5 batch, then a Claude session. 25x125 has no free lane or ModelRouter; do not add one without Marlon. No local models.
- **Key.** `CLAUDE_API_KEY_25X125` comes from the cloud environment (Claude Code settings ignore `ANTHROPIC_API_KEY` there) or the local `.env`, where `ANTHROPIC_API_KEY` also works. Jobs pass it to the SDK client explicitly. There is no secrets file in this project's shared folder. The never-print, never-commit rule is the same.
- **Spend log.** `docs/ai-runs.md` in the repo, with the ledger's columns: model, rows, input, output, cache write, cache read, dollars.
- **Cost warnings.** Warn Marlon before any paid run with a dollar estimate. Runs likely over about $5 wait for his go-ahead.
- **Thinking on Opus 5.5.** The master says `between_tools` for Sonnet and Opus. Per Anthropic's API reference (checked 2026-11-01), only Sonnet 5.5 accepts `between_tools`; Opus 5.5 rejects both `disabled` and `between_tools`, so omit `thinking` there and set `effort` low. Haiku 5.5 accepts `disabled` at effort `high` or below.
- **Checking output.** Model output is data to check, not a source. Store the model and date on each value and spot-check a sample against the original before it reaches a screen.
- **MLS.** MRED data never goes to any model.
- The rest of the master (Minecraft pack, Panscriptum, novels, PC rules) does not apply to 25x125.

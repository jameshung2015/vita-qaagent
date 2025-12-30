# VITA QA Agent – AI Working Notes

- **Goal**: Turn PRD markdown (local or URL) into structured walkthrough rules, JSONL testcases/scenes/mappings, DB/ES materialized JSONL, and a Markdown summary via the enhanced Typer CLI.
- **Entrypoint**: [cli/main.py](cli/main.py) (单入口，支持多PRD、URL、自定义prompts、merge-prds、materialize)。

## Runbook
- Activate Python 3.9+ env, install deps: `pip install -r requirements.txt`.
- Generate (multi-PRD) example: `python cli/main.py generate --prd metric/识人识物_用例设计原则与示例.md --project recognition --merge-prds --materialize --verbose`.
- Multi-PRD with custom prompts: `python cli/main.py generate --prd a.md --prd b.md --prompts-config config/prompts.yaml --no-merge-prds --materialize`.
- Tests: `pytest tests/ -v`; coverage: `pytest tests/ --cov=src --cov-report=html`.

## Configuration & Secrets
- Load env from [config/.env](config/.env) (created from `.env.example`); keys: `ARK_API_KEY` (Doubao, preferred), `G2M_API_KEY` (fallback). `ModelFactory` auto-picks based on these vars.
- Prompt & global generation knobs live in [config/prompts.yaml](config/prompts.yaml); v2 CLI can point to a custom file via `--prompts-config`.
- Logging: [src/utils/logger.py](src/utils/logger.py) writes timestamped files under `outputs/logs/` plus console output.

## Data Flow & Components
- **Model layer**: [src/models/model_factory.py](src/models/model_factory.py) selects [doubao_client](src/models/doubao_client.py) (OpenAI-compatible) or [g2m_client](src/models/g2m_client.py) (HTTP). `safe_model_call` in [src/utils/error_handler.py](src/utils/error_handler.py) retries on timeouts/API errors.
- **Requirement parsing**: [src/agents/requirement_parser.py](src/agents/requirement_parser.py) builds an LLM prompt, extracts JSON modules/features/flows, and normalizes into `ParsedRequirement` (see module/feature/flow schemas).
- **Rule generation**: [src/agents/rule_generator.py](src/agents/rule_generator.py) crafts a walkthrough rule (scenario dimensions, template, priority rules) and fills defaults when LLM output is sparse.
- **Testcase synthesis**: [src/agents/testcase_generator.py](src/agents/testcase_generator.py) walks modules→features→flows, applies scenario dimensions, assigns priority/level, generates steps/expected via LLM when not provided, stamps timestamps, and keeps `_metadata` used for scene mapping before stripping on write.
- **File/URI loading**: v2 CLI uses [src/utils/file_loader.py](src/utils/file_loader.py) to accept local paths or HTTP(S), merge multiple PRDs, and load optional metric/principles content.

## Outputs & Conventions
- Output root defaults to `outputs/`; filenames are timestamped via `generate_output_filename` ([src/utils/file_utils.py](src/utils/file_utils.py)).
- Artifacts: `testcases/*.jsonl` (one JSON per line), optional `scenes*.jsonl` and `scene_mappings*.jsonl`, `rules/*.json` (walkthrough rule), `reports/*.md` summary. `_metadata` is removed from saved testcase rows but kept transiently for scene mapping.
- Markdown summary rows are generated within the CLI helpers; modifying formats requires changing `generate_markdown_summary` in the CLIs.

## Error Handling & Validation
- Use `QAAgentError` hierarchy in [src/utils/exceptions.py](src/utils/exceptions.py) for surfaced failures; CLIs catch and render user-friendly messages.
- JSON extraction from LLM responses is manual (code-block stripping); keep outputs valid JSON and match required fields (`rule_id`, `scenario_dimensions`, modules list) to avoid downstream crashes.

## When Extending
- Adding a new model: subclass `BaseModelClient` ([src/models/base.py](src/models/base.py)), implement `chat_completion`/`multimodal_completion`, and register in `ModelFactory`.
- Prompt tuning: adjust templates in [config/prompts.yaml](config/prompts.yaml) or point `--prompts-config` to a custom file.
- New scenario dimensions/priority logic: extend defaults in [src/agents/rule_generator.py](src/agents/rule_generator.py) and ensure `TestCaseGenerator` uses the same identifiers.

## Quick Checks Before Runs
- Ensure PRD/metric/principles files exist or URLs are reachable; `FileOperationError` will halt otherwise.
- Set env keys; without `ARK_API_KEY`/`G2M_API_KEY`, model init fails.
- Clear previous outputs if reruns should not append; files are regenerated with new timestamps per run.

Let me know what feels unclear or if you want deeper coverage (e.g., DB schema alignment or CI integration).
# Lucy Actions

Generated from action_router --describe.

| Action | Path | Required |
| --- | --- | --- |
| chatgpt_ask | SERVICE|DIRECT_FALLBACK | prompt |
| daily_plan | LOCAL|SERVICE|DIRECT_FALLBACK |  - |
| echo | LOCAL |  - |
| summarize_forense | LOCAL | dir |

## chatgpt_ask

```json
{"payload":{"required":["prompt"],"optional":["timeout_sec","use_service"]},"returns":{"answer_text":"str","answer_line":"str|None"},"path":"SERVICE|DIRECT_FALLBACK","notes":"uses ChatGPT UI bridge"}
```

## daily_plan

```json
{"payload":{"required":[],"optional":["date","use_chatgpt","prompt_hint","max_chars"]},"returns":{"base_plan":"str","final_plan":"str","source":"FILE|OFFLINE","chatgpt_used":"bool","chatgpt_path":"SERVICE|DIRECT_FALLBACK|NONE|FAILED"},"path":"LOCAL|SERVICE|DIRECT_FALLBACK","notes":"local-first plan, optional ChatGPT enhancement"}
```

## echo

```json
{"payload":{"required":[],"optional":["..."]},"returns":"payload passthrough","path":"LOCAL","notes":"sanity/offline"}
```

## summarize_forense

```json
{"payload":{"required":["dir"],"optional":[]},"returns":"forensics summary dict","path":"LOCAL","notes":"offline parser"}
```


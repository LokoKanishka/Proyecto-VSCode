# Lucy Actions

Generated from action_router --describe.

| Action | Path | Required |
| --- | --- | --- |
| chatgpt_ask | SERVICE|DIRECT_FALLBACK | prompt |
| echo | LOCAL |  - |
| summarize_forense | LOCAL | dir |

## chatgpt_ask

```json
{"payload":{"required":["prompt"],"optional":["timeout_sec","use_service"]},"returns":{"answer_text":"str","answer_line":"str|None"},"path":"SERVICE|DIRECT_FALLBACK","notes":"uses ChatGPT UI bridge"}
```

## echo

```json
{"payload":{"required":[],"optional":["..."]},"returns":"payload passthrough","path":"LOCAL","notes":"sanity/offline"}
```

## summarize_forense

```json
{"payload":{"required":["dir"],"optional":[]},"returns":"forensics summary dict","path":"LOCAL","notes":"offline parser"}
```


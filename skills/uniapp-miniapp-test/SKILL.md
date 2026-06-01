---
name: uniapp-miniapp-test
description: Test uni-app WeChat mini program changes with AI-driven validation. Use when the user asks to test, verify, QA, debug, or generate a test plan for a uni-app / wellness_uniapp / WeChat mini program page, pages.json route, subpackage, login/auth, API integration, payment, location, scan, subscription message, or HBuilderX / WeChat DevTools CLI workflow.
---

# Uni-App Miniapp Test

Use this skill to make Codex actively test uni-app WeChat mini program changes instead of only writing a checklist.

## Core Workflow

1. Identify the changed feature and target mini program entry.
   - Read `pages.json` first.
   - Then inspect the target page, components, API wrappers, `common/js`, and `manifest.json` only when relevant.
2. Split validation into:
   - build or compile checks
   - route and subpackage checks
   - page interaction checks
   - API request/response checks
   - login/auth checks
   - platform capability checks
   - regression checks
3. Prefer actual execution with local tools.
4. Record evidence: command output, page path, console errors, network responses, screenshots, or clear blocker reason.
5. If AI cannot complete a real-device or authenticated step, produce precise manual verification steps with expected results.
6. If defects are found, localize the likely file, fix when requested, and re-test the affected path.

## Tool Selection

Use available tools in this order:

1. File/code inspection for routes, page logic, API calls, and config.
2. HBuilderX CLI if configured locally.
3. WeChat DevTools CLI if configured locally.
4. WeChat DevTools UI / logs / screenshots when accessible.
5. Real-device verification for platform capabilities.

Before using HBuilderX or WeChat DevTools CLI:

- Check whether the executable exists or is on `PATH`.
- Run its help command if unsure about supported flags.
- Do not invent CLI flags; versions differ.
- If unavailable, state the blocker and provide a substitute manual path.

For detailed local-tool guidance, read `references/tooling.md` when CLI or DevTools execution is needed.

## Test Focus

### Build And Route

- `pages.json` contains the page path or subpackage path.
- TabBar, navigation, redirects, and back behavior remain valid.
- Added pages use the intended style and permission configuration.
- Subpackage changes do not break package boundaries.

### Page Interaction

- Initial load, empty data, loading state, error state, and success state are visible and usable.
- Forms validate required fields, length, format, duplicate submit, and disabled states.
- Buttons and links trigger the intended actions once.
- Returned data maps correctly to UI fields.

### API Integration

- Confirm request URL, method, params, body, headers, and auth token flow.
- Validate success, business error, network error, timeout, and empty response handling.
- Check field compatibility when backend DTOs changed.
- Do not log sensitive values such as tokens, phone numbers, IDs, or payment credentials.

### Login And Platform Capabilities

Login, payment, location, scan, subscription messages, sharing, and real authorization often need manual or real-device confirmation.

AI should still prepare:

- exact page path
- preconditions
- account/role needed
- operation steps
- expected UI result
- expected request/response
- screenshots or logs to capture

Human confirmation is required for payment, production app IDs, upload/submit review, real authorization, and any irreversible operation.

## Output Format

Return a compact report:

```text
测试范围：
使用工具：
已执行验证：
关键证据：
发现问题：
已修复或建议修复：
未能自动验证：
人工验证步骤：
是否可以进入 Review：
```

## Guardrails

- Do not modify `manifest.json`, AppID, production endpoints, or platform configuration unless the user explicitly asks and confirms.
- Do not upload experience versions, submit review, trigger payment, or change production/test data without explicit confirmation.
- Keep test fixes scoped to the failing route or component.
- Prefer existing project scripts and local workflow over introducing new test frameworks.

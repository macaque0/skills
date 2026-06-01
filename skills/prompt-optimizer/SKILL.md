---
name: prompt-optimizer
description: "Rewrite rough user prompts into clear, structured, executable prompts for general Q&A, Codex programming, copywriting, image generation, and data analysis. Use when a user asks to optimize, polish, structure, expand, or repair a prompt, when a vague request needs to become a better prompt, or when the user explicitly invokes `$prompt-optimizer`, `Prompt Optimizer`, or this skill chip and appends text after it. In explicit-invocation cases, treat the appended text as the prompt to optimize even if the user does not say optimize."
---

# Prompt Optimizer

## Goal
Rewrite the user's rough prompt into a ready-to-use version that preserves intent, adds structure, and makes the expected output explicit.

## Trigger and Input Handling
- If the user explicitly invokes this skill and provides text after the skill mention/chip, treat that trailing text as the rough prompt to optimize.
- Default to optimizing the trailing text, not answering or executing it as the underlying task.
- Only both optimize and execute the prompt when the user explicitly asks for both.
- If no prompt text is provided after an explicit invocation, ask for the prompt to optimize.

## Workflow
1. Identify the task type: general Q&A, Codex programming, writing, image generation, data analysis, or mixed.
2. Extract the essentials: goal, context, inputs, constraints, audience, tone, success criteria, and output format.
3. Infer safe defaults when the user leaves gaps. Do not invent domain facts; note assumptions when they matter.
4. Rewrite the prompt in the user's language and keep technical terms unchanged.
5. Make the prompt concise but complete. Remove ambiguity, duplicate wording, and open-ended phrasing.
6. If the prompt is too underspecified, include optional follow-up questions instead of blocking.

## Scenario Patterns
- General Q&A: define the question, scope, depth, audience, and answer format.
- Codex programming: include repository context, target files, exact change, constraints, edge cases, tests, and acceptance criteria.
- Copywriting: include audience, channel, tone, length, key message, CTA, banned points, and examples if useful.
- Image generation: include subject, style, composition, lighting, camera or view, aspect ratio, mood, and negative constraints.
- Data analysis: include dataset or source, question, time range, metrics, filters, method, and output tables or charts.

## Output Format
Return these sections:

### 优化后的提示词
Put the optimized prompt in a fenced code block.

### 优化点
List the specific changes made and why they help.

### 可选补充问题
List 0-3 optional questions that would improve the prompt further, or write `无` if none are needed.

## Output Rules
- Keep changes minimal when the original prompt is already strong.
- Preserve the user's intent. Do not add unrelated goals.
- Prefer concrete constraints over vague advice.
- Do not explain prompt theory unless the user asks for it.

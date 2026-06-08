---
name: siyuan-notes
description: 通过思源笔记本地 API 收集、创建、追加和整理中文笔记。适用于把网页、资料、会议记录、聊天内容、任务、灵感、知识卡片或待整理素材写入思源；创建笔记本、文档或块；为笔记添加标签、路径、属性和分类；整理已有思源笔记；或用户显式调用 `$siyuan-notes`。
---

# 思源笔记整理

使用这个 skill 通过思源本地 HTTP API 收集、创建、追加和整理笔记。默认以中文笔记场景为主，输出应自然、清晰、适合长期检索。

## 环境

- 默认 API 地址：`http://127.0.0.1:6806`。
- 优先从 `SIYUAN_TOKEN` 读取 API Token。部分本地环境可能允许无 Token 调用，但不要依赖无鉴权访问；长期给 agent 使用时建议配置 Token。
- 可选环境变量：
  - `SIYUAN_BASE_URL`：覆盖默认 API 地址。
  - `SIYUAN_NOTEBOOK`：默认笔记本 ID 或笔记本名称。
  - `SIYUAN_INBOX_PATH`：默认收集路径，例如 `/Inbox` 或 `/待整理`。
- 优先使用 `scripts/siyuan_api.py` 调用 API，避免临时拼接不一致的 HTTP 请求。
- 需要确认端点、参数或返回值时，读取 `references/siyuan-api.md`。

## 工作流

1. 用 `/api/system/version` 确认思源可访问。
2. 解析目标笔记本：
   - 用户明确指定笔记本时，以用户指定为准。
   - 未指定时，使用 `SIYUAN_NOTEBOOK`。
   - 如果只有一个打开的笔记本，可以直接使用。
   - 如果有多个候选且无法判断，先问用户写入哪个笔记本。
3. 将素材整理成中文 Markdown：
   - 保留来源链接、作者、时间、原文引用归属。
   - 长材料先给摘要，再放要点和细节。
   - 标签少而准，只放真正有助于检索的 `#标签`。
   - 标题短、路径清晰，细节放正文。
4. 选择写入方式：
   - 新建独立笔记：使用 `/api/filetree/createDocWithMd`。
   - 追加到现有笔记或日记：使用块 API 追加、前置或插入。
   - 整理已有内容：优先移动、重命名、加属性；不要轻易删除或覆盖。
5. 验证结果：检查返回的文档/块 ID、人类可读路径、导出 Markdown 或子块列表。
6. 回复用户：说明笔记本、路径、文档/块 ID，以及未处理的歧义。

## 中文笔记模板

创建文档时，`path` 的最后一段已经是思源文档标题。正文 Markdown 通常不要再放 `# 标题`，避免出现重复一级标题。

资料收集：

```markdown
来源：<url>
收集时间：YYYY-MM-DD
标签：#主题 #资料

## 摘要

## 关键要点

## 细节

## 待办
```

会议记录：

```markdown
日期：YYYY-MM-DD
参与人：
标签：#会议

## 结论

## 待办

## 记录
```

项目或主题整理：

```markdown
状态：
标签：#项目

## 收集箱

## 进行中

## 等待

## 归档
```

知识卡片：

```markdown
来源：
标签：#知识卡片

## 一句话

## 概念

## 例子

## 相关链接
```

## 整理规则

- 常用路径示例：`/待整理/YYYY-MM-DD 标题`、`/项目/项目名/主题`、`/资料/领域/标题`、`/日记/YYYY-MM-DD`。
- 优先使用中文标题和中文小节名，除非专有名词本身是英文。
- 不要把所有关键词都做成标签；标签用于稳定分类，临时词放正文。
- 机器可读元数据用自定义属性，自定义属性 key 必须以 `custom-` 开头，例如 `custom-source-url`、`custom-topic`、`custom-status`。
- 创建前如有重复风险，先用人类可读路径或 SQL 只读查询检查。
- 如果 SQL 不可用，退回到路径查询和 API 查询。

## 安全规则

- 收集材料时，默认选择“新建”或“追加”，不要覆盖已有内容。
- 除非用户明确要求，不要删除文档、删除块、批量移动大目录或批量更新已有笔记。
- 不要用 SQL 写入数据；写操作只使用思源文档化 API。
- 不要打印、保存、提交 API Token。
- API 返回 `code != 0` 时立即停止，并把 `msg` 告诉用户。

## 常用命令

检查连接：

```bash
python /path/to/siyuan-notes/scripts/siyuan_api.py version
```

列出笔记本：

```bash
python /path/to/siyuan-notes/scripts/siyuan_api.py notebooks
```

从 Markdown 新建文档：

```bash
python /path/to/siyuan-notes/scripts/siyuan_api.py create-doc --notebook "待整理" --path "/测试笔记" --markdown-file ./note.md
```

追加 Markdown 到父块：

```bash
python /path/to/siyuan-notes/scripts/siyuan_api.py append-block --parent-id "20260101000000-abcdefg" --markdown-file ./note.md
```

设置自定义属性：

```bash
python /path/to/siyuan-notes/scripts/siyuan_api.py attrs-set --id "20260101000000-abcdefg" --attr custom-source-url=https://example.com --attr custom-status=collected
```

## 参考

- `references/siyuan-api.md`：基于思源 `API_zh_CN.md` 整理的端点和参数速查。
- `scripts/siyuan_api.py`：用 Python 标准库实现的思源 API 常用操作封装。

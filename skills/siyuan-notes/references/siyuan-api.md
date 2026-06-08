# 思源 API 速查

来源：https://github.com/siyuan-note/siyuan/blob/master/API_zh_CN.md

## 基本约定

- 默认地址：`http://127.0.0.1:6806`
- 方法：`POST`
- JSON 请求头：`Content-Type: application/json`
- Token 请求头：`Authorization: Token <token>`
- 常见返回：

```json
{
  "code": 0,
  "msg": "",
  "data": {}
}
```

`code != 0` 表示失败，应停止后续写操作并查看 `msg`。

## 系统

- `/api/system/version`：无参数，返回思源版本。
- `/api/system/currentTime`：无参数，返回当前时间戳。
- `/api/system/bootProgress`：无参数，返回启动进度。

## 笔记本

- `/api/notebook/lsNotebooks`：无参数，返回 `data.notebooks`。
- `/api/notebook/createNotebook`

```json
{ "name": "笔记本名称" }
```

- `/api/notebook/openNotebook`

```json
{ "notebook": "笔记本ID" }
```

- `/api/notebook/closeNotebook`
- `/api/notebook/renameNotebook`
- `/api/notebook/removeNotebook`
- `/api/notebook/getNotebookConf`
- `/api/notebook/setNotebookConf`

写入文档时使用笔记本 ID；如果用户给的是名称，先通过 `lsNotebooks` 解析。

## 文档

通过 Markdown 创建文档：

- `/api/filetree/createDocWithMd`

```json
{
  "notebook": "笔记本ID",
  "path": "/待整理/标题",
  "markdown": "正文 Markdown"
}
```

返回的 `data` 是新文档 ID。重复调用同一个 `path` 不会覆盖已有文档。

注意：`path` 最后一段会成为思源文档标题，正文 Markdown 通常不要再包含 `# 同名标题`。

重命名、删除、移动：

- `/api/filetree/renameDoc`
- `/api/filetree/renameDocByID`
- `/api/filetree/removeDoc`
- `/api/filetree/removeDocByID`
- `/api/filetree/moveDocs`
- `/api/filetree/moveDocsByID`

路径和 ID 查询：

- `/api/filetree/getHPathByPath`
- `/api/filetree/getHPathByID`
- `/api/filetree/getPathByID`
- `/api/filetree/getIDsByHPath`

有重复风险时，创建前先用 `getIDsByHPath` 查询。

## 块

插入到已有块附近：

- `/api/block/insertBlock`

```json
{
  "dataType": "markdown",
  "data": "Markdown 内容",
  "nextID": "",
  "previousID": "前一个块ID",
  "parentID": ""
}
```

`nextID`、`previousID`、`parentID` 至少需要一个。

追加或前置子块：

- `/api/block/prependBlock`
- `/api/block/appendBlock`

```json
{
  "dataType": "markdown",
  "data": "Markdown 内容",
  "parentID": "父块ID"
}
```

其他块操作：

- `/api/block/updateBlock`
- `/api/block/deleteBlock`
- `/api/block/moveBlock`
- `/api/block/foldBlock`
- `/api/block/unfoldBlock`
- `/api/block/getBlockKramdown`
- `/api/block/getChildBlocks`
- `/api/block/transferBlockRef`

更新、删除、移动属于高风险操作，只有用户明确要求时才执行。

## 属性

- `/api/attr/setBlockAttrs`

```json
{
  "id": "块或文档ID",
  "attrs": {
    "custom-source-url": "https://example.com",
    "custom-status": "collected"
  }
}
```

- `/api/attr/getBlockAttrs`

自定义属性 key 必须以 `custom-` 开头。

## SQL

- `/api/query/sql`

```json
{ "stmt": "SELECT * FROM blocks WHERE content LIKE '%关键词%' LIMIT 10" }
```

只把 SQL 用于查询。某些模式会禁用该端点。

- `/api/sqlite/flushTransaction`：无参数，提交事务。

## 资源文件

- `/api/asset/upload`：multipart form 上传。

常用字段：

- `assetsDirPath`：通常用 `/assets/`
- `file[]`：一个或多个文件

返回值会把原文件名映射为思源资源路径，例如 `assets/foo-id.png`。写入 Markdown 前，应把本地图片链接替换成返回的资源路径。

## 模板

- `/api/template/render`
- `/api/template/renderSprig`

渲染日期路径示例：

```json
{ "template": "/daily note/{{now | date \"2006/01\"}}/{{now | date \"2006-01-02\"}}" }
```

用于日记路径或符合用户笔记本配置的 Sprig 模板。

## 文件和导出

- `/api/file/getFile`
- `/api/file/putFile`
- `/api/file/removeFile`
- `/api/file/renameFile`
- `/api/file/readDir`
- `/api/export/exportMdContent`
- `/api/export/exportResources`

验证写入结果时，优先用 `exportMdContent`，不要直接读 `.sy` 原始文件。

## 通知和网络

- `/api/notification/pushMsg`
- `/api/notification/pushErrMsg`
- `/api/network/forwardProxy`

长时间导入完成后可以推送通知。不要使用代理端点，除非用户明确要求让思源代发网络请求。

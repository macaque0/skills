# SiYuan API Reference

Source: https://github.com/siyuan-note/siyuan/blob/master/API_zh_CN.md

## Contract

- Base URL: `http://127.0.0.1:6806`
- Method: `POST`
- JSON requests use `Content-Type: application/json`
- Token header: `Authorization: Token <token>`
- Typical JSON response:

```json
{
  "code": 0,
  "msg": "",
  "data": {}
}
```

Treat non-zero `code` as a failed operation.

## System

- `/api/system/version`: no payload; returns the SiYuan version.
- `/api/system/currentTime`: no payload; returns current time in milliseconds.
- `/api/system/bootProgress`: no payload; returns startup progress.

## Notebooks

- `/api/notebook/lsNotebooks`: no payload; returns `data.notebooks`.
- `/api/notebook/createNotebook`

```json
{ "name": "Notebook name" }
```

- `/api/notebook/openNotebook`

```json
{ "notebook": "notebook-id" }
```

- `/api/notebook/closeNotebook`
- `/api/notebook/renameNotebook`
- `/api/notebook/removeNotebook`
- `/api/notebook/getNotebookConf`
- `/api/notebook/setNotebookConf`

Notebook write operations use the notebook ID.

## Documents

Create a document from Markdown:

- `/api/filetree/createDocWithMd`

```json
{
  "notebook": "notebook-id",
  "path": "/Inbox/Title",
  "markdown": "# Title\n\nBody"
}
```

The returned `data` is the new document ID. Reusing the same path does not overwrite an existing document.

Rename, remove, and move:

- `/api/filetree/renameDoc`
- `/api/filetree/renameDocByID`
- `/api/filetree/removeDoc`
- `/api/filetree/removeDocByID`
- `/api/filetree/moveDocs`
- `/api/filetree/moveDocsByID`

Path and ID lookups:

- `/api/filetree/getHPathByPath`
- `/api/filetree/getHPathByID`
- `/api/filetree/getPathByID`
- `/api/filetree/getIDsByHPath`

Use `getIDsByHPath` before creating if duplicate title/path risk matters.

## Blocks

Insert relative to an existing block:

- `/api/block/insertBlock`

```json
{
  "dataType": "markdown",
  "data": "Markdown content",
  "nextID": "",
  "previousID": "previous-block-id",
  "parentID": ""
}
```

At least one of `nextID`, `previousID`, or `parentID` must be set.

Add children:

- `/api/block/prependBlock`
- `/api/block/appendBlock`

```json
{
  "dataType": "markdown",
  "data": "Markdown content",
  "parentID": "parent-block-id"
}
```

Other block operations:

- `/api/block/updateBlock`
- `/api/block/deleteBlock`
- `/api/block/moveBlock`
- `/api/block/foldBlock`
- `/api/block/unfoldBlock`
- `/api/block/getBlockKramdown`
- `/api/block/getChildBlocks`
- `/api/block/transferBlockRef`

Use update/delete/move only when the user clearly requested editing existing content.

## Attributes

- `/api/attr/setBlockAttrs`

```json
{
  "id": "block-or-doc-id",
  "attrs": {
    "custom-source-url": "https://example.com",
    "custom-status": "collected"
  }
}
```

- `/api/attr/getBlockAttrs`

Custom attribute keys must start with `custom-`.

## SQL

- `/api/query/sql`

```json
{ "stmt": "SELECT * FROM blocks WHERE content LIKE '%keyword%' LIMIT 10" }
```

Use SQL only for read queries. Some modes disable this endpoint for safety.

- `/api/sqlite/flushTransaction`: no payload; commit pending transactions.

## Assets

- `/api/asset/upload`: multipart form upload.

Fields:

- `assetsDirPath`: usually `/assets/`
- `file[]`: one or more files

Return value maps original filenames to SiYuan asset paths such as `assets/foo-id.png`. Replace local Markdown links with those returned asset paths.

## Templates

- `/api/template/render`
- `/api/template/renderSprig`

Render a date path:

```json
{ "template": "/daily note/{{now | date \"2006/01\"}}/{{now | date \"2006-01-02\"}}" }
```

Use this for daily-note paths when the user's notebook configuration follows a Sprig template.

## Files and Export

- `/api/file/getFile`
- `/api/file/putFile`
- `/api/file/removeFile`
- `/api/file/renameFile`
- `/api/file/readDir`
- `/api/export/exportMdContent`
- `/api/export/exportResources`

For verification, `exportMdContent` is usually safer than reading raw `.sy` files.

## Notifications and Network

- `/api/notification/pushMsg`
- `/api/notification/pushErrMsg`
- `/api/network/forwardProxy`

Notifications are useful after long imports. Avoid using the proxy endpoint unless the user explicitly needs SiYuan to make the network request.

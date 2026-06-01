# {{title}}

时间范围：{{since}} 至 {{until}}
统计口径：{{scan_mode}}
目标分支：{{base_branches}}

## 总览

本期共统计 {{employees}} 位员工、{{commits}} 个提交，归并为 {{work_items}} 个工作事项。

| 员工 | 工作事项 | 已合入 | 部分合入 | 尚未合入 | 涉及范围 |
| --- | ---: | ---: | ---: | ---: | --- |
| {{employee}} | {{work_items}} | {{merged_items}} | {{partial_items}} | {{unmerged_items}} | {{scopes}} |

## {{employee}}

### 工作内容

| 工作内容 | 状态 | 涉及范围 | 关联提交 |
| --- | --- | --- | --- |
| {{summary}} | {{status}} | {{scope}} | {{hashes}} |

### 提交明细

- {{repository}}/{{branch}}：{{message}}（{{hash}}）

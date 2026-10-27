# 三层记忆模块
Python 3.10+，仅标准库。数据库文件的父目录自动创建。通过 `with MemoryStore(...)` 或 `close()` 关闭连接。

- 短期：实例中的 `_sessions` 字典，仅保留当前问题、选中文件、页面筛选、草稿、检索结果；不写 SQLite。读取返回深拷贝。会话 ID 由服务器持有，生产应使用按用户隔离的会话服务；实例重建即丢失。
- 长会话：`workspace_records` 持久化文档、分块、批次、用户确认记录、问题摘要、操作历史；`memories.scope=long_session` 保存候选。所有记录有 workspace_id。
- 长期：仅允许五种 kind，必须显式 confirmed=True 或调用 confirm_memory，必须非空来源。更新内容后撤销确认。标题、摘要和偏好均使用 content 对象保存。

候选可以无来源暂存，但不能确认。临时草稿只能使用短期 draft 字段，kind=draft 会拒绝。确认记录可通过 add_workspace_record 单独保存，模块不会自动生成审计记录。

`MemoryStore(db_path, workspace_id='course-a')` 是网页请求所需形式。绑定后列表、搜索、导出、清空和长会话接口校验 workspace；ID 接口的 SQL 同样限定 workspace。不绑定是项目负责人离线管理模式，不应用于未经鉴权的请求。绑定课程不等于用户授权，A 仍需验证课程成员资格。

来源以外部 chunk ID 保存，原文由 A 的解析存储负责；也可用 add_workspace_record('course-a','chunk',{'chunk_id':..., 'text':...}) 保存副本。核心库校验来源非空，不会猜测外部 ID 是否真实存在；网页应采用 integration_example.py 的 source_resolver，按同一课程验证 ID 和原文。偏好来源可以是 A 记录的用户确认事件 ID。

搜索是内容 JSON 的 Unicode 不区分大小写的字面子串搜索，无向量模型、分词和排序。默认 list/export/search 只返回未删除且已确认长期内容；显式 scope='long_session' 可读取候选，不能作为长期回答上下文。

删除是软删除，所有公开读取均过滤 deleted_at。清空只清除该课程长期内容，保留候选、长会话资料和审计；这不是物理擦除。记录时间使用 UTC ISO 8601，ID 使用 UUID。数据库含约束和课程索引，SQLite 写事务原子提交；每个请求/线程单独连接，不共享实例。当前无迁移框架。

所有接口、返回结构、异常和网页接入流程见 ../integration_contract.md。


## 课程 Agent 档案归组

网页长期记忆按来源文件保存：每个课程文件对应一个 `course_document_archive`，其中 `document_id` 是唯一归组键，`knowledge_points` 保存该文件已确认的知识点和原文位置。重复确认只更新同一档案；打开长期记忆页面时会将旧版逐知识点记录合并为文件档案，并清理已删除资料对应的档案。

删除某份资料档案只删除该资料的长期记忆，不删除资料库和知识目录内容；清空长期记忆也不会在页面刷新时自动重建。以后新确认的知识点会再写入该资料对应的档案。

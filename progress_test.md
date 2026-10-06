2026年10月2日
发现jd切换问题

- 发现
- INFO:     127.0.0.1:64534 - "GET /api/jd HTTP/1.1" 401 Unauthorized
INFO:     127.0.0.1:64535 - "GET /api/auth/me HTTP/1.1" 401 Unauthorized 
- jd列表全部消失
- 安装 DB Browser for SQLite - Standard installer for 64-bit Windows
- 修复前端 workspace 初始化竞态：未登录时 `/api/jd` 请求 401 后，不再错误地将 `workspace.initialized` 标记为 `true`。同时避免 Router 尚未完成认证判断时提前挂载 `AppLayout`，确保登录成功后能正常重新加载已保存 JD。

- codex出现深挖浏览器的致命错误
  
- 寻找jd变换但jd内容没有变换问题
- toRaw js无法读取vue 响应式 proxy
- “数据改了，页面自己跟着改”，就叫响应式。不用去刷新
- 语言几秒切换问题，其实是自己后端关了...


## 2026年10月6日
-- 暂时省略很多问题

-- 今天换模型，出现疑似输出不稳定问题
-- 升级结构化输出
-- 然后deepseekai信誓旦旦说兼容，实际不兼容
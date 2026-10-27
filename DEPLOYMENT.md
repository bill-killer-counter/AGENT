# 公网演示版部署

本目录提供 `demo_app.py` 作为公开演示入口。访客各自使用隔离的临时课程数据库，并自动获得三份示例资料；这适合课程展示和功能试用，不是带永久账号与云端备份的正式多人服务。

## 用 Streamlit Community Cloud 发布

1. 将本目录中的文件提交到一个 GitHub 仓库。不要提交 `data/`、真实学生资料、账号文件或密钥。
2. 登录 [Streamlit Community Cloud](https://share.streamlit.io/) 并连接该 GitHub 仓库。
3. 创建应用时选择部署分支，并将主文件路径设为 `demo_app.py`。
4. 点击部署。平台启动成功后会生成 `https://<应用名称>.streamlit.app` 形式的公开地址；以平台实际显示的地址为准。
5. 把生成的地址发给访客。无需让访客下载 ZIP 或安装 Python。

## 当前演示版的数据边界

- 示例资料会自动载入；访客上传的数据只进入该浏览器会话自己的临时空间。
- 不提供真实注册、跨设备账号同步或持久化保障。服务重启、休眠或重新部署后，临时演示数据可能消失。
- 不要上传个人信息、未公开课程资料或其他敏感文件。
- 公开演示不是生产环境。若要长期给多人使用，需要接入有持久化能力的云数据库和文件存储、正式身份认证、备份与删除策略，再做权限和并发验证。

## 本地预览演示模式

在项目目录中运行：

```powershell
python -m pip install -r requirements.txt
python -m streamlit run demo_app.py
```

本地完整开发模式仍可运行 `python -m streamlit run app.py`。

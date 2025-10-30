# arXiv Quant-ph 每日速递

这是一个基于 Python 和 GitHub Actions 的全自动工作流，用于每日抓取 arXiv `quant-ph` (量子物理) 分类的最新论文，将其标题和摘要自动翻译为中文，并生成一份易于阅读的 Markdown 报告。

## 🌟 主要功能

* **全自动运行**: 利用 GitHub Actions，每天定时（默认北京时间上午9点）自动执行。
* **增量更新**: 自动记录已处理的论文ID (`processed_ids.txt`)，确保每天只推送*新*的论文，不重复抓取。
* **自动翻译**: 调用腾讯机器翻译 (TMT) API，将论文标题和摘要翻译为中文。
* **稳定可靠**:
    * 使用 arXiv 官方 API (`arxiv` 库)，而非爬虫，杜绝被封IP。
    * 内置 API 访问重试逻辑，应对 arXiv 服务器的瞬时不稳定。
    * 内置 QPS 限制 (延时)，符合腾讯云API的调用频率要求。
* **自动归档**: 自动将生成的 `.md` 报告和 `processed_ids.txt` 提交 (push) 回您的 GitHub 仓库。

## 🚀 工作原理

1.  **定时触发**: GitHub Actions 按照 `.github/workflows/arxiv_fetcher.yml` 文件中 `cron` 表达式设定的时间自动启动。
2.  **环境准备**: Action 检出 (checkout) 代码，设置 Python 环境，并安装 `requirements.txt` 中的所有依赖库。
3.  **执行脚本**: Action 运行 `run_arxiv_fetcher.py` 脚本。
    * 脚本读取 GitHub Secrets (`TENCENT_SECRET_ID`, `TENCENT_SECRET_KEY`) 作为环境变量。
    * 脚本读取 `processed_ids.txt`，了解哪些论文已被处理过。
    * 脚本调用 arXiv API，获取 `quant-ph` 分类最新的 50 篇论文。
    * 脚本筛选出未被处理过的新论文。
    * 脚本循环调用腾讯翻译 API (TMT)，翻译标题和摘要（内置延时和截断）。
    * 脚本将结果写入 `reports/quant-ph_YYYY-MM-DD.md` 文件。
    * 脚本将新论文的 ID 写入 `processed_ids.txt`。
4.  **提交归档**: Action 使用 `git` 命令将新生成的 `reports/*.md` 和更新后的 `processed_ids.txt` 自动提交并推回仓库。

## 🛠️ 如何部署 (Setup)

您只需按照以下步骤，即可在您自己的仓库中部署这套系统：

### 1. 创建仓库

* 您可以 Fork 本仓库，或者创建一个新的**私有**仓库（推荐，因为报告是为您个人生成的）。
* 将本项目中的三个核心文件推送到您的仓库：
    1.  `run_arxiv_fetcher.py` (核心脚本)
    2.  `requirements.txt` (依赖列表)
    3.  `.github/workflows/arxiv_fetcher.yml` (GitHub Action 配置文件)

### 2. 开通腾讯机器翻译 (TMT)

1.  登录您的腾讯云控制台。
2.  搜索并进入“**机器翻译 TMT**”服务。
3.  点击“**立即开通**”，按照指引开通服务（它有充足的免费额度）。
4.  记下您开通服务的**地域**（例如 `ap-guangzhou` 或 `ap-shanghai`）。

### 3. 获取腾讯云 API 密钥

1.  在腾讯云控制台，进入“**访问管理 (CAM)**”。
2.  在左侧菜单选择“**API密钥管理**”。
3.  点击“**新建密钥**”，获取一对 `SecretId` 和 `SecretKey`。

### 4. 设置 GitHub Secrets

1.  在您的 GitHub 仓库页面，点击 `Settings` > `Secrets and variables` > `Actions`。
2.  点击 `New repository secret`，创建以下两个 Secrets：
    * **`TENCENT_SECRET_ID`**: 值为您上一步获取的 `SecretId` (以 `AKID` 开头)。
    * **`TENCENT_SECRET_KEY`**: 值为您上一步获取的 `SecretKey`。

### 5. （重要）检查并配置

1.  **授予权限**: 确保 `.github/workflows/arxiv_fetcher.yml` 文件中包含以下权限设置，否则 Action 无法提交文件：
    ```yaml
    jobs:
      build-and-commit:
        runs-on: ubuntu-latest
        permissions:
          contents: write # 必须有这一行
    ```
2.  **检查地域**: 检查 `run_arxiv_fetcher.py` 脚本顶部的配置，确保 `TRANSLATE_REGION` (例如 `"ap-guangzhou"`) 与您在步骤2中开通服务的地域一致。

### 6. 手动触发测试

1.  转到仓库的 `Actions` 标签页。
2.  在左侧点击 `Daily arXiv Fetcher`。
3.  点击 `Run workflow` 按钮，手动触发一次运行。
4.  稍等片刻，刷新仓库页面，查看 `reports` 文件夹中是否已生成了当天的 `.md` 报告。

## ⚙️ 自定义配置

您可以直接修改 `run_arxiv_fetcher.py` 顶部的配置区（`--- 1. 配置区域 ---`）来自定义：

* `ARXIV_QUERY`: 要查询的 arXiv 分类，默认为 `cat:quant-ph`。
* `ARXIV_MAX_RESULTS`: 每次 API 请求拉取的最大数量，默认为 `50`。
* `TRANSLATE_REGION`: 腾讯云TMT服务地域。

## 💡 常见问题 (Troubleshooting)

* **Action 报错 403 (Write access... not granted)**
    * **原因**: GitHub Action 默认没有写入仓库的权限。
    * **解决**: 参见 **[步骤 5.1](#5-授予权限)**，在 `.yml` 文件中添加 `permissions: contents: write`。
* **翻译结果为 `[Translation Failed]`**
    * **原因**: 腾讯云 API 调用失败。
    * **解决**:
        1.  检查 GitHub Secrets (`TENCENT_SECRET_ID`, `TENCENT_SECRET_KEY`) 是否设置正确（**注意**：不要有空格）。
        2.  检查 `run_arxiv_fetcher.py` 中的 `TRANSLATE_REGION` 是否与您开通服务的地域一致。
        3.  检查您是否已在腾讯云控制台**开通**了“机器翻译 TMT”服务。
* **Action 报错 `fatal: pathspec 'processed_ids.txt' did not match...`**
    * **原因**: 脚本首次运行，或某次运行因 arXiv API 临时故障而没有产生新文件，导致 `git add` 找不到文件。
    * **解决**: 这个问题通常已被 `.yml` 文件中的 `git add ... || true` 命令解决。如果仍然出现，请检查 `Run arXiv Fetcher` 步骤的日志，看是否是 Python 脚本执行失败。
* **只有标题被翻译，摘要是 `[Translation Failed]`**
    * **原因**: 触发了腾讯云 QPS 限制（免费版每秒5次）。
    * **解决**: 脚本中已内置 `time.sleep(0.3)` 延时来解决此问题。如果仍然出现，可以适当调高延时（例如到 `0.5`）。

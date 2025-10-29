import os
import datetime
import arxiv # 导入arxiv库
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.tmt.v20180321 import tmt_client, models

# --- 1. 配置区域 ---
YOUR_SECRET_ID = 1335386935
YOUR_SECRET_KEY = "AKIDb9TaWFl6GI9nDQQFsIWWItQkxAIE1snc"
# 腾讯云API密钥 (从您的腾讯云控制台获取)
# 强烈建议使用环境变量来存储，而不是硬编码在代码中
SECRET_ID = os.environ.get("TENCENT_SECRET_ID", "YOUR_SECRET_ID")
SECRET_KEY = os.environ.get("TENCENT_SECRET_KEY", "YOUR_SECRET_KEY")

# 翻译配置
TRANSLATE_REGION = "ap-guangzhou"  # 使用您开通服务的地域，例如 "ap-guangzhou"
TRANSLATE_ENDPOINT = "tmt.tencentcloudapi.com"

# arXiv 查询配置
ARXIV_QUERY = "cat:quant-ph"  # 分类：量子物理
ARXIV_MAX_RESULTS = 50       # 每次最多拉取最近50篇

# 输出配置
OUTPUT_DIR = "reports"  # 报告存放的文件夹
PROCESSED_IDS_FILE = "processed_ids.txt"  # 存放已处理论文ID的文件

# --- 2. 腾讯翻译函数 ---


def translate_text(text, source='en', target='zh'):
    """调用腾讯API翻译文本"""
    if not SECRET_ID or SECRET_ID == "YOUR_SECRET_ID":
        print("错误：未配置腾讯云 SECRET_ID。跳过翻译。")
        return f"[Translation Skipped] {text}"

    try:
        cred = credential.Credential(SECRET_ID, SECRET_KEY)
        httpProfile = HttpProfile()
        httpProfile.endpoint = TRANSLATE_ENDPOINT

        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        client = tmt_client.TmtClient(cred, TRANSLATE_REGION, clientProfile)

        req = models.TextTranslateRequest()
        params = {
            "SourceText": text,
            "Source": source,
            "Target": target,
            "ProjectId": 0
        }
        req.from_json_string(str(params))

        resp = client.TextTranslate(req)
        return resp.TargetText
    except TencentCloudSDKException as err:
        print(f"翻译API错误: {err}")
        return f"[Translation Failed: {text[:30]}...]"
    except Exception as e:
        print(f"翻译函数发生未知错误: {e}")
        return "[Translation Failed]"

# --- 3. 辅助函数：加载已处理ID ---


def load_processed_ids():
    """从文件加载已处理过的arXiv ID，避免重复工作"""
    processed_ids = set()
    if os.path.exists(PROCESSED_IDS_FILE):
        with open(PROCESSED_IDS_FILE, 'r') as f:
            processed_ids = set(line.strip() for line in f)
    return processed_ids


def save_processed_id(paper_id):
    """将新处理的ID追加到文件"""
    with open(PROCESSED_IDS_FILE, 'a') as f:
        f.write(f"{paper_id}\n")

# --- 4. 主函数：抓取和生成报告 ---


def main():
    print("开始抓取 arXiv quant-ph 最新论文...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    processed_ids = load_processed_ids()

    # 1. 搜索 arXiv
    # 按提交日期降序排序，获取最新的论文
    search = arxiv.Search(
        query=ARXIV_QUERY,
        max_results=ARXIV_MAX_RESULTS,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending
    )

    # 2. 筛选新论文
    papers_to_process = []
    for result in search.results():
        # result.entry_id 的格式是 'http://arxiv.org/abs/2410.12345v1'
        # 我们可以只取ID部分
        paper_id = result.get_short_id()
        if paper_id not in processed_ids:
            papers_to_process.append(result)

    if not papers_to_process:
        print("没有发现新论文。")
        return

    # 为了报告的可读性，我们将新论文按从旧到新的顺序排列
    papers_to_process.reverse() 
    print(f"发现了 {len(papers_to_process)} 篇新论文。开始处理...")

    # 3. 准备 Markdown 内容
    today_str = datetime.date.today().isoformat()
    md_content = [f"# {today_str} · quant-ph 论文速递\n"]

    # 4. 循环处理每篇论文
    for paper in papers_to_process:
        paper_id = paper.get_short_id()
        try:
            print(f"正在处理: {paper.title}")

            # 翻译
            title_zh = translate_text(paper.title)
            # 摘要中的换行符可能导致API出错，先替换掉
            clean_summary = paper.summary.replace('\n', ' ')
            abstract_zh = translate_text(clean_summary)

            # 作者
            authors = ", ".join([author.name for author in paper.authors])

            # 拼接MD
            md_content.append(f"## {title_zh}")
            md_content.append(f"**Original Title:** {paper.title}")
            md_content.append(f"**Authors:** {authors}")
            md_content.append(f"**Link:** {paper.entry_id}")
            md_content.append(f"**PDF:** {paper.pdf_url}")
            md_content.append(f"**Submitted:** {paper.submitted.date()}")
            md_content.append("\n### 摘要")
            md_content.append(abstract_zh)
            md_content.append("\n### Abstract")
            md_content.append(paper.summary)
            md_content.append("\n---\n")  # 分隔符

            # 标记为已处理
            save_processed_id(paper_id)

        except Exception as e:
            print(f"处理论文 {paper_id} 时发生错误: {e}")
            # 如果处理失败，我们不保存ID，以便下次重试

    # 5. 保存 .md 文件
    filename = os.path.join(OUTPUT_DIR, f"quant-ph_{today_str}.md")
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("\n\n".join(md_content))

    print(f"报告已生成: {filename}")

if __name__ == "__main__":
    main()
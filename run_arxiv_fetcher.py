import os
import time
import datetime
import arxiv  # 导入arxiv库
import requests  # 确保导入 requests
import json
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.tmt.v20180321 import tmt_client, models

# --- 1. 配置区域 ---

# 腾讯云API密钥 (将从 GitHub Secrets 中读取)
SECRET_ID = os.environ.get("TENCENT_SECRET_ID")
SECRET_KEY = os.environ.get("TENCENT_SECRET_KEY")

# 翻译配置
TRANSLATE_REGION = "ap-guangzhou"
TRANSLATE_ENDPOINT = "tmt.tencentcloudapi.com"

# arXiv 查询配置
ARXIV_QUERY = "cat:quant-ph"
ARXIV_MAX_RESULTS = 100       # 每次拉取最新的 100 篇

# 输出配置
OUTPUT_DIR = "reports"
PROCESSED_IDS_FILE = "processed_ids.txt"

# --- 2. 腾讯翻译函数 ---


def translate_text(text, source='en', target='zh'):
    """调用腾讯API翻译文本"""
    if not SECRET_ID or not SECRET_KEY:
        print("错误：未在 GitHub Secrets 中配置 TENCENT_SECRET_ID 或 TENCENT_SECRET_KEY。")
        print("将跳过翻译。")
        return f"[Translation Skipped - Check GitHub Secrets] {text}"

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
        req.from_json_string(json.dumps(params))

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

    # --- 这是修复了 'DeprecationWarning' 的正确代码 ---

    # 1. 实例化一个 Client (不需要任何代理参数)
    client = arxiv.Client()
    search = arxiv.Search(
        query=ARXIV_QUERY,
        max_results=ARXIV_MAX_RESULTS,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending
    )
    # 2. 筛选新论文
    papers_to_process = []
    print("正在连接到 arXiv API 获取结果...")
    try:
        # 使用 client.results() (这在 GitHub 上会正常工作)
        results_generator = client.results(search)
        for result in results_generator:
            paper_id = result.get_short_id()
            if paper_id not in processed_ids:
                papers_to_process.append(result)
    except Exception as e:
        print(f"!!! 访问 arXiv API 失败 (GitHub Runner)。错误详情: {e}")
        return  # 失败则退出
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
            time.sleep(0.5)
            clean_summary = paper.summary.replace('\n', ' ')
            if len(clean_summary) > 2000:
                print(f"  [警告] 摘要过长 ({len(clean_summary)} 字符)，将进行截断...")
                clean_summary = clean_summary[:2000]  # 截断为前2000个字符
            abstract_zh = translate_text(clean_summary)
            # 作者
            authors = ", ".join([author.name for author in paper.authors])
            # 拼接MD
            md_content.append(f"## {title_zh}")
            md_content.append(f"**Original Title:** {paper.title}")
            md_content.append(f"**Authors:** {authors}")
            md_content.append(f"**Link:** {paper.entry_id}")
            md_content.append(f"**PDF:** {paper.pdf_url}")
            md_content.append(f"**Submitted:** {paper.published.date()}")
            md_content.append("\n### 摘要")
            md_content.append(abstract_zh)
            md_content.append("\n### Abstract")
            md_content.append(paper.summary)
            md_content.append("\n---\n")  # 分隔符
            # 标记为已处理
            save_processed_id(paper_id)
        except Exception as e:
            print(f"处理论文 {paper_id} 时发生错误: {e}")
    # 5. 保存 .md 文件
    filename = os.path.join(OUTPUT_DIR, f"quant-ph_{today_str}.md")
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("\n\n".join(md_content))
    print(f"报告已生成: {filename}")


if __name__ == "__main__":
    main()

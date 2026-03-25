"""推送通知模块 — 邮件 / Webhook"""

import json
import logging
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

import requests

from src.config import NotifyConfig

logger = logging.getLogger(__name__)


def send_notification(title: str, content: str, config: NotifyConfig) -> bool:
    """发送通知，根据配置选择渠道"""
    if not config.enabled:
        return False

    if config.method == "email":
        return send_email(title, content, config)
    elif config.method == "webhook":
        return send_webhook(title, content, config)
    else:
        logger.warning(f"Unknown notify method: {config.method}")
        return False


def send_email(title: str, content: str, config: NotifyConfig) -> bool:
    """通过 SMTP 发送邮件"""
    if not all([config.smtp_user, config.smtp_password, config.email_to]):
        logger.warning("Email config incomplete")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = title
        msg["From"] = config.smtp_user
        msg["To"] = config.email_to

        # 同时发送纯文本和 HTML
        text_part = MIMEText(content, "plain", "utf-8")
        html_content = _markdown_to_simple_html(content)
        html_part = MIMEText(html_content, "html", "utf-8")
        msg.attach(text_part)
        msg.attach(html_part)

        if config.smtp_port == 465:
            # SSL
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(config.smtp_server, config.smtp_port, context=context) as server:
                server.login(config.smtp_user, config.smtp_password)
                server.sendmail(config.smtp_user, config.email_to.split(","), msg.as_string())
        else:
            # STARTTLS
            with smtplib.SMTP(config.smtp_server, config.smtp_port) as server:
                server.starttls()
                server.login(config.smtp_user, config.smtp_password)
                server.sendmail(config.smtp_user, config.email_to.split(","), msg.as_string())

        logger.info(f"Email sent to {config.email_to}")
        return True
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        return False


def send_webhook(title: str, content: str, config: NotifyConfig) -> bool:
    """通过 Webhook 发送通知 (支持钉钉/飞书/企业微信/通用)"""
    if not config.webhook_url:
        logger.warning("Webhook URL not configured")
        return False

    url = config.webhook_url
    try:
        if "dingtalk" in url or "oapi.dingtalk.com" in url:
            # 钉钉机器人
            payload = {
                "msgtype": "markdown",
                "markdown": {"title": title, "text": f"## {title}\n\n{content}"}
            }
        elif "feishu" in url or "open.feishu.cn" in url:
            # 飞书机器人
            payload = {
                "msg_type": "interactive",
                "card": {
                    "header": {"title": {"tag": "plain_text", "content": title}},
                    "elements": [{"tag": "markdown", "content": content}]
                }
            }
        elif "qyapi.weixin.qq.com" in url:
            # 企业微信
            payload = {
                "msgtype": "markdown",
                "markdown": {"content": f"## {title}\n\n{content}"}
            }
        else:
            # 通用 Webhook
            payload = {"title": title, "content": content, "type": "markdown"}

        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            logger.info(f"Webhook sent successfully")
            return True
        else:
            logger.warning(f"Webhook returned {resp.status_code}: {resp.text[:200]}")
            return False
    except Exception as e:
        logger.error(f"Webhook send failed: {e}")
        return False


def format_daily_push(results: list, market_overview: str = "") -> tuple:
    """格式化每日推送内容，返回 (title, content)"""
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")

    lines = [f"**巴菲特智能投研 -- {today}**\n"]

    if market_overview:
        lines.append(market_overview)
        lines.append("\n---\n")

    # 按评级排序
    sorted_r = sorted(results, key=lambda r: r.overall_score, reverse=True)

    # 重点关注 (A/B 级)
    highlights = [r for r in sorted_r if r.buffett_result.get("grade") in ("A", "B")]
    if highlights:
        lines.append("### 重点关注")
        for r in highlights:
            g = r.buffett_result.get("grade", "?")
            lines.append(
                f"- **{r.symbol}** ({r.name}) [{g}] "
                f"综合 {r.overall_score:.0f} | {r.recommendation}"
            )
        lines.append("")

    # 风险预警 (D/F 级)
    risks = [r for r in sorted_r if r.buffett_result.get("grade") in ("D", "F")]
    if risks:
        lines.append("### 风险预警")
        for r in risks:
            g = r.buffett_result.get("grade", "?")
            lines.append(f"- **{r.symbol}** ({r.name}) [{g}] {r.recommendation}")
        lines.append("")

    # 全部列表
    lines.append("### 完整列表")
    market_labels = {"us": "美股", "hk": "港股", "a_share": "A股"}
    for r in sorted_r:
        g = r.buffett_result.get("grade", "?")
        m = market_labels.get(r.market, "")
        price_str = f"{r.price:.2f}" if r.price else "N/A"
        lines.append(f"- [{m}] {r.symbol} ({r.name}): {g} | {price_str} | {r.recommendation}")

    content = "\n".join(lines)
    title = f"巴菲特投研日报 {today}"

    return title, content


def _markdown_to_simple_html(md: str) -> str:
    """简单的 Markdown -> HTML 转换（不依赖外部库）"""
    import re
    html = md
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    html = html.replace('\n\n', '<br><br>')
    return f'<div style="font-family: sans-serif; line-height: 1.6;">{html}</div>'

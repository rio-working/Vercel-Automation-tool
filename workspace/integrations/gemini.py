"""
integrations/gemini.py  ─  Gemini AI 連携
google-genai 新SDK (v1.x) を使用。
モデル: gemini-2.0-flash
"""
import json
import os

from google import genai

from core.logger import log_error

_MODEL_NAME = "gemini-2.0-flash"


def _get_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY が未設定です")
    return genai.Client(api_key=api_key)


def analyze_todo(content: str) -> dict:
    """ToDoテキストから重要度・工数を判定する。"""
    try:
        client = _get_client()
        prompt = f"""以下のToDoタスクを分析して、JSONのみで返答してください。

タスク: {content}

返答形式（JSONのみ、説明不要）:
{{
  "priority": "高" または "中" または "低",
  "effort": "大" または "中" または "小",
  "reason": "判定理由を20文字以内で"
}}"""
        response = client.models.generate_content(model=_MODEL_NAME, contents=prompt)
        text = response.text.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except Exception as e:
        log_error("gemini.analyze_todo", "ToDo分析エラー", e)
        return {"priority": "中", "effort": "中", "reason": "AI分析失敗"}


def chat(message: str, context: dict = None) -> str:
    """AI壁打ちチャット。今日のToDo/予定をコンテキストとして送信する。"""
    try:
        client = _get_client()
        context_text = ""
        if context:
            todos = context.get("todos", [])
            agenda = context.get("agenda", [])
            if todos:
                todo_list = "\n".join([f"- {t}" for t in todos[:10]])
                context_text += f"\n【今日のToDo】\n{todo_list}"
            if agenda:
                agenda_list = "\n".join([f"- {a}" for a in agenda[:10]])
                context_text += f"\n【今日の予定】\n{agenda_list}"

        system = "あなたは個人ダッシュボードのAIアシスタントです。ユーザーの業務をサポートします。簡潔に日本語で答えてください。"
        full_prompt = f"{system}{context_text}\n\nユーザー: {message}"
        response = client.models.generate_content(model=_MODEL_NAME, contents=full_prompt)
        return response.text.strip()
    except Exception as e:
        log_error("gemini.chat", "チャットエラー", e)
        return "申し訳ありません。AIとの通信でエラーが発生しました。"


def generate_journal(completed_todos: list[str], agenda: list[str]) -> str:
    """完了タスク＋予定から日報テキストを自動生成する。"""
    try:
        client = _get_client()
        todos_text = "\n".join([f"- {t}" for t in completed_todos]) if completed_todos else "なし"
        agenda_text = "\n".join([f"- {a}" for a in agenda]) if agenda else "なし"
        prompt = f"""以下の情報をもとに、ビジネス向けの日報を生成してください。

【完了したタスク】
{todos_text}

【本日の予定】
{agenda_text}

日報形式:
- 本日の成果（箇条書き）
- 所感・課題
- 明日の予定

自然な日本語で、簡潔にまとめてください。"""
        response = client.models.generate_content(model=_MODEL_NAME, contents=prompt)
        return response.text.strip()
    except Exception as e:
        log_error("gemini.generate_journal", "日報生成エラー", e)
        return "日報の自動生成に失敗しました。手動で入力してください。"


def structure_chat(messages: list[dict]) -> str:
    """チャット履歴を箇条書き＋アクションアイテムに整理する。"""
    try:
        client = _get_client()
        if not messages:
            return "整理する会話がありません。"

        history_text = "\n".join([
            f"{'ユーザー' if m.get('role') == 'user' else 'AI'}: {m.get('text', '')}"
            for m in messages
        ])

        prompt = f"""以下の会話を整理して、日本語で構造化してください。

【会話履歴】
{history_text}

以下の形式で出力してください：

## 会話のサマリー
（2〜3文で要点をまとめる）

## 主なポイント
- （箇条書きで要点を列挙）

## アクションアイテム
- （具体的に実行すべき行動を列挙。なければ「なし」）

JSONや説明文は不要です。上記フォーマットのテキストのみを返してください。"""

        response = client.models.generate_content(model=_MODEL_NAME, contents=prompt)
        return response.text.strip()
    except Exception as e:
        log_error("gemini.structure_chat", "会話整理エラー", e)
        return "会話の整理に失敗しました。"


def suggest_focus(agenda: list[dict]) -> str:
    """カレンダー予定の隙間時間を分析して集中タイムを提案する。"""
    try:
        client = _get_client()
        if not agenda:
            return "本日の予定がありません。終日集中できる時間があります！"

        agenda_text = "\n".join([
            f"- {a.get('time', '終日')}: {a.get('title', '')}"
            for a in agenda[:15]
        ])
        prompt = f"""以下の本日のスケジュールを分析して、集中作業に最適な時間帯を提案してください。

【本日の予定】
{agenda_text}

30分以上の空き時間を見つけ、集中作業に適した時間帯を日本語で提案してください。
2〜3文で簡潔に。"""
        response = client.models.generate_content(model=_MODEL_NAME, contents=prompt)
        return response.text.strip()
    except Exception as e:
        log_error("gemini.suggest_focus", "集中タイム提案エラー", e)
        return "集中タイムの提案に失敗しました。"

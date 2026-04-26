import streamlit as st
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# ローカルは.envから、Streamlit Cloudはst.secretsから読む
load_dotenv(Path(__file__).parent / ".env")

def get_secret(key: str, default: str = "") -> str:
    """ローカル(.env) / Streamlit Cloud(st.secrets) 両対応"""
    try:
        return st.secrets[key]
    except Exception:
        return os.environ.get(key, default)

# ページ設定
st.set_page_config(
    page_title="BONIQナレッジAI",
    page_icon="🍖",
    layout="centered",
)

# スタイル
st.markdown("""
<style>
    .main { max-width: 800px; }
    .source-tag {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: bold;
        margin-right: 6px;
    }
    .tag-tachikawa { background: #e8f4f8; color: #1a6b8a; }
    .tag-jay { background: #fef3e2; color: #9a6000; }
    .ref-card {
        background: #f8f9fa;
        border-left: 3px solid #dee2e6;
        padding: 8px 12px;
        margin: 6px 0;
        border-radius: 0 6px 6px 0;
        font-size: 13px;
    }
</style>
""", unsafe_allow_html=True)

# ヘッダー
st.title("🍖 BONIQナレッジAI")
st.caption("立川光昭・ジェイ・エイブラハム 175本分の講義に質問できます")
st.divider()

# LLMラベル確認
ANTHROPIC_API_KEY = get_secret("ANTHROPIC_API_KEY")
DEFAULT_CLAUDE_MODEL = get_secret("CLAUDE_MODEL") or "claude-sonnet-4-5"
USE_CLAUDE = bool(ANTHROPIC_API_KEY and not ANTHROPIC_API_KEY.startswith("your_"))

# 入力エリア（サンプル質問選択時にpre-fill）
default_question = ""
if "sample_question" in st.session_state:
    default_question = st.session_state.pop("sample_question")

question = st.text_area(
    "質問を入力してください",
    value=default_question,
    placeholder="例: ヒット商品を作るためのターゲティングのコツは？",
    height=100,
)

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    source_option = st.selectbox(
        "検索対象",
        options=["全ナレッジ（立川＋Jay）", "立川光昭のみ", "ジェイ・エイブラハムのみ"],
    )
with col2:
    top_k = st.slider("参照チャンク数", min_value=3, max_value=12, value=8)
with col3:
    if USE_CLAUDE:
        model_options = {
            "Sonnet（速い）": "claude-sonnet-4-5",
            "Opus（高精度）": "claude-opus-4-5",
        }
        model_label = st.selectbox("モデル", options=list(model_options.keys()))
        CLAUDE_MODEL = model_options[model_label]
    else:
        CLAUDE_MODEL = DEFAULT_CLAUDE_MODEL
        st.caption("モデル: GPT-4o-mini")

llm_label = f"Claude ({CLAUDE_MODEL})" if USE_CLAUDE else "GPT-4o-mini"
st.caption(f"使用モデル: {llm_label}")

source_map = {
    "全ナレッジ（立川＋Jay）": None,
    "立川光昭のみ": "tachikawa",
    "ジェイ・エイブラハムのみ": "jay_abraham",
}
source = source_map[source_option]

# サンプル質問
with st.expander("💡 サンプル質問を見る"):
    samples = [
        "ヒット商品を作るためのターゲティングのコツは？",
        "価格競争に巻き込まれずに売る方法は？",
        "リピーターを増やすために何をすべきか",
        "少ない広告費で最大の効果を出すには？",
        "顧客の生涯価値（LTV）を最大化する方法は？",
        "独自のウリ（USP）をどうやって見つけるか",
        "口コミを自然に広げる仕組みはどう作るか",
        "売上を2倍にするための3つのアプローチ",
    ]
    for s in samples:
        if st.button(s, key=s, use_container_width=True):
            st.session_state["sample_question"] = s
            st.rerun()

# 送信ボタン
run = st.button("🔍 検索して回答する", type="primary", use_container_width=True, disabled=not question.strip())

if run and question.strip():
    # 検索＋回答
    from openai import OpenAI
    from supabase import create_client

    openai_client = OpenAI(api_key=get_secret("OPENAI_API_KEY"))
    supabase = create_client(get_secret("SUPABASE_URL"), get_secret("SUPABASE_SERVICE_KEY"))

    with st.spinner("ナレッジを検索中..."):
        resp = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=question.replace("\n", " "),
        )
        embedding = resp.data[0].embedding

        result = supabase.rpc("match_knowledge_chunks", {
            "query_embedding": embedding,
            "match_threshold": 0.3,
            "match_count": top_k,
            "filter_source": source,
        }).execute()
        chunks = result.data

    if not chunks:
        st.warning("関連するナレッジが見つかりませんでした。質問を変えて試してみてください。")
    else:
        # コンテキスト構築
        context_parts = []
        for i, c in enumerate(chunks, 1):
            src_label = "立川光昭" if c["source"] == "tachikawa" else "ジェイ・エイブラハム"
            context_parts.append(
                f"【参考{i}: {src_label} / {c['course']} / {c['title']}】\n{c['content']}"
            )
        context = "\n\n---\n\n".join(context_parts)

        system_prompt = """あなたはBONIQ（低温調理専門ブランド）のサポートスタッフ向け社内アシスタントです。
立川光昭とジェイ・エイブラハムのマーケティング・商品企画・販売戦略ナレッジベースを持っています。

回答ルール:
- 日本語で回答する
- ナレッジベースの内容を根拠に具体的に答える
- 該当情報がない場合は正直に伝える
- 実践的なアクションが取れる形で答える
- 箇条書きを活用して見やすくまとめる"""

        user_message = f"=== ナレッジベース ===\n{context}\n\n=== 質問 ===\n{question}"

        with st.spinner(f"{llm_label}が回答を生成中..."):
            if USE_CLAUDE:
                import anthropic
                claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
                response = claude_client.messages.create(
                    model=CLAUDE_MODEL,
                    max_tokens=2048,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}],
                )
                answer = response.content[0].text
            else:
                response = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    max_tokens=2048,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                )
                answer = response.choices[0].message.content

        # 回答表示
        st.divider()
        st.subheader("💬 回答")
        st.markdown(answer)

        # 参照ナレッジ
        st.divider()
        st.subheader("📚 参照ナレッジ")
        for c in chunks:
            is_tachikawa = c["source"] == "tachikawa"
            tag_class = "tag-tachikawa" if is_tachikawa else "tag-jay"
            tag_label = "立川" if is_tachikawa else "Jay"
            sim_pct = int(c["similarity"] * 100)
            st.markdown(
                f'<div class="ref-card">'
                f'<span class="source-tag {tag_class}">{tag_label}</span>'
                f'<strong>{c["title"]}</strong>'
                f'<span style="float:right;color:#888;font-size:12px">関連度 {sim_pct}%</span>'
                f'<br><span style="color:#666;font-size:12px">{c["course"]}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

# フッター
st.divider()
st.caption("📊 ナレッジDB: 立川光昭 104本 (1,620チャンク) ＋ ジェイ・エイブラハム 71本 (549チャンク) = 合計2,169チャンク")

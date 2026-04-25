# BONIQ ナレッジ RAG システム

立川光昭・ジェイ・エイブラハムの175本分の講義をベクトル検索でAI回答。

## 構成

- Supabase (pgvector + HNSW index)  →  2,169チャンク格納済み
- OpenAI text-embedding-3-small     →  質問・チャンクをベクトル化
- GPT-4o-mini / Claude Sonnet       →  回答生成（Anthropic APIキーがあれば自動でSonnet）

## 使い方

```bash
cd /Users/hatakazuhiro/Desktop/cursor-master/00_knowledge/rag

# 全ナレッジから検索
python3 query_rag.py "ヒット商品を作るためのターゲティングのコツは？"

# 立川光昭のナレッジだけ検索
python3 query_rag.py "価格競争に巻き込まれずに売る方法は？" --source tachikawa

# ジェイ・エイブラハムのナレッジだけ検索
python3 query_rag.py "顧客獲得コストを下げる方法は？" --source jay_abraham
```

## Claude Sonnetに切り替える方法

1. https://console.anthropic.com/settings/keys でAPIキーを発行
2. `.env` の `ANTHROPIC_API_KEY=` に設定
3. 次回実行から自動でSonnetに切り替わる

## ナレッジの更新方法

新しいMDファイルを追加したら再インデックス（スキップ機能あり）:

```bash
python3 index_knowledge.py
```

## データ量

| ソース | ファイル数 | チャンク数 |
|--------|-----------|-----------|
| 立川光昭 | 104本 | 1,620 |
| ジェイ・エイブラハム | 71本 | 549 |
| 合計 | 175本 | 2,169 |

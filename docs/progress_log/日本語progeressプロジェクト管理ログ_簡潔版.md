# Resume Agent 開発・プロジェクト管理ログ
**開発期間：2026年8月上旬 ～ 2026年10月8日**

## 1. プロジェクト立ち上げ・JD解析基盤の構築（8月上旬）

AIを利用して大量の履歴書から採用担当者が確認すべき候補者を効率的に抽出することを目的として、Resume Agentの開発を開始した。

最初にFastAPI / Pydanticを中心としたバックエンド基盤を構築し、LLM呼び出し部分を業務ロジックから分離した。

第一段階としてJD（求人票）解析を実装し、

**JD原文 → LLM解析 → 構造化JD → HRによる修正 → 保存**

という基本フローを確立した。

JD Requirementにはカテゴリと相対Weightを持たせ、AIの解析結果をそのまま最終決定とせず、HRが内容・重要度を修正できる設計とした。

また、DeepSeek実API接続時に401エラーが発生した際には、Windows側の既存環境変数との競合を特定した。モデル固有の環境変数名を廃止し、`LLM_API_KEY / LLM_BASE_URL / LLM_MODEL` に統一することで、将来的にLLM事業者を切り替えやすい構成へ変更した。

---

## 2. 履歴書構造化モジュールの開発（8月8日～17日）

次にPDF履歴書の解析機能を実装した。

Candidateを単なるLLM出力として扱うのではなく、

**PDF / Text  
→ ResumeLLMResult  
→ Backend Mapping  
→ Candidate**

というレイヤー構造を採用した。

LLMには履歴書に記載されている事実のみを抽出させ、ID、原文、Metadataなどのシステム情報はバックエンド側で付与する設計とした。

教育、職歴、プロジェクト、スキル、言語、資格等に加えて、標準項目には入りにくいものの後続評価で有用となる事実を保持できる構造も用意した。

8月中旬にはPDFテキスト抽出、Resume Service、DeepSeekによる実データ解析、単一履歴書解析APIまで接続し、履歴書からCandidateを生成する基本フローを完成させた。

---

## 3. バッチ解析・非同期処理への拡張（8月後半～9月上旬）

単一履歴書処理から複数履歴書の一括処理へ拡張した。

大量処理を想定し、

- `async / await`
- `asyncio.gather`
- `asyncio.Semaphore`
- 個別worker
- task / item単位の状態管理
- Frontend polling
- Incremental Display

を組み合わせた方式へ発展させた。

一つの履歴書が失敗してもバッチ全体を停止させず、先に解析できたCandidateから順次表示・評価できる構成とした。

同時実行数についても無制限にせず、Semaphoreによる制御を導入した。

その後、画面遷移によってResume Uploadの進行状態が失われる問題を改善するため、フロントエンド側に**グローバルResume Task RunnerのSingleton**を導入し、画面のライフサイクルと解析タスクを分離した。

構造化解析が失敗した履歴書については、元データを利用して再試行できるRetry機能も追加した。

---

## 4. Job Matching Scoringの設計・実装（9月7日～14日）

採用判断を単純なLLMの総合点に依存させず、JD Requirement単位で評価する方式を設計した。

基本フローは、

**JD Requirement × Candidate  
→ LLMによる意味的判断  
→ Requirement単位の結果  
→ BackendによるWeight正規化・集計  
→ Job Match Score**

とした。

判定状態は、

- matched
- partially_matched
- not_matched
- insufficient_evidence

に分離した。

特に、

**「履歴書に書いていない」≠「条件を満たしていない」**

という原則を重視し、Evidence不足と明確な不一致を区別した。

また、`must_have` と `weight` を別概念として設計した。

`must_have` は採用上の必須条件、`weight` はその要件が職務遂行能力に対してどの程度重要かを表すため、必須条件だから自動的に高Weightになる設計にはしていない。

LLMは各Requirementに対する意味判断・理由・Evidenceを返すが、最終的なWeight計算やMust-have判定など、決定可能な業務ルールはバックエンドが担当する構成とした。

---

## 5. Evidence・Raw Review設計と評価品質の改善

Scoring設計段階から、モデルが提示したEvidenceを無条件に信用しない方針を採用した。

初期段階では、構造化Candidateだけでは判断できない場合に原文へ戻るRaw Resume ReviewのSchemaと拡張ポイントを設計した。

当初はLangGraphやTool Callingまで導入せず、`needs_raw_review` 等を利用して将来のOrchestration追加に耐えられる構成に留めた。

その後、実際の製品品質向上としてEvidence Validationを実装した。

LLMが提示したEvidenceをCandidate構造化データおよび履歴書原文と照合し、確認できないEvidenceをそのまま画面に出さないようにした。

さらにScoring / AI Talent / HR指定Talentの間でEvidence状態の扱いに差があった部分を整理し、フロントエンドにも**「Evidence確認済み」**等の表示を追加した。

これにより、採用担当者が「AIがそう言っている」だけではなく、判断根拠が実際の候補者資料に存在するかを確認しやすくした。

---

## 6. Talent Discoveryモジュール（9月中旬）

Job Matchingとは別に、「条件には完全一致していなくても、能力のある候補者を見落とさない」ことを目的としてTalent Discoveryを設計した。

本モジュールは最終的に二つの評価モードへ整理した。

### AI Auto Discovery
候補者資料から、学習力、スキル転用、問題解決、主体性、成果、継続性など、HRが追加で確認する価値のある能力Evidenceを自動的に発見する。

### HR Specified Traits
企業・求人側が「責任感」「細かさ」「自主性」など独自に注目したい観点を指定し、それを支持するEvidenceを候補者資料から探索する。

両者をJob Matchとは明確に分離し、

**Job Match：仕事の要件を満たしているか**

**Talent Discovery：その候補者に他にどのような注目すべき能力・特徴があるか**

という役割分担を定義した。

後にデータ保存・UIともAuto / Specifiedを独立させ、どちらか一方しか保持できない構造を解消した。

---

## 7. 多言語アーキテクチャ（9月23日～）

中国語・日本語・英語を主要対応言語として、多言語対応を実装した。

単純な画面翻訳ではなく、

- 入力資料の原文
- 内部構造化データ
- HRが見る表示言語
- AI分析結果の出力言語

を分離した。

JDおよび履歴書の原文は事実情報として保持し、LLMは原文を直接理解した上で、HRが選択した言語で分析結果を生成する。

Frontend locale → API → Service → Promptまで`analysis_language`を渡すことで、言語切替と評価ロジックを分離した。

Vue i18n導入後には、Navigationだけでなく各View、動的メッセージ、Placeholder、エラー、Backend Status Code由来の表示まで含めて多言語漏れを专项チェックした。

---

## 8. 永続化・認証・CRUDへの移行（9月末～10月上旬）

初期開発では一部データをメモリやフロントエンドStateで保持していたが、製品として継続利用できるよう、SQLite + SQLAlchemy + Alembicを導入した。

User / Session / Job / Candidate / Job-Candidate Relation / Scoring Result / Talent Result等を永続化し、主要バックエンド機能についてCRUD APIを整備した。

CookieベースのログインSessionも実装した。

この段階では永続化に伴うフロントエンドStateとの整合性問題も発生した。

特に、ログイン直後にJD一覧が空になる偶発的な問題について調査した結果、

**認証確認より先にAppLayoutが初期化  
→ `/api/jd` が401  
→ workspaceが誤ってinitializedになる**

というFrontend initialization race conditionを特定し修正した。

また、JDを切り替えても画面の内容が変わらない問題については、VueのReactive Proxyを直接`structuredClone()`していたことによるDataCloneErrorを特定し、`toRaw()`を利用して修正した。

---

## 9. Candidate Pool・原本履歴書・削除機能

採用担当者は最終的にAIの分析だけでなく候補者本人の履歴書を確認するため、原本PDFの保存・閲覧機能を追加した。

CandidateとPDF原本を紐付け、候補者一覧・詳細画面から元の履歴書を確認できるようにした。

また、JDごとの候補者一覧だけでは採用資産を横断的に確認できないため、**Global Candidate Pool**を追加した。

削除についても、

- JDから候補者との関連だけを削除
- Candidate Poolから候補者本体を削除
- JD自体を削除

を区別し、関連するScoring / Talent / Relationとの整合性を保つよう整理した。

JD削除についてもバックエンドだけでなくFrontend操作まで完成させた。

---

## 10. LLM出力安定性・Structured Output検証（10月6日前後）

別LLM ProviderとしてVolcengine Ark経由のモデルを検証したところ、

- Responseが遅い
- Contentが空になる場合がある
- JSON形式が不安定
- 同一モデル名でもProviderによって挙動が異なる

という問題が確認された。

対策としてStructured Outputの利用も実装・テストした。

しかし実測では、Structured Outputパラメータを追加しても業務上必要な安定性改善は限定的であり、既存の

**PromptへのSchema注入  
+ JSON Mode  
+ Pydantic Validation  
+ Backend Validation**

の方が実用上重要であると判断した。

一度Structured Output対応を実装したが、互換性と複雑性に対してメリットが小さかったため、検証後にロールバックした。

この検証には時間を要したが、「新しいAPI機能を導入すること自体」を目的にせず、実測結果から不要な複雑性を撤回する判断を行った。

---

## 11. Prompt Injectionへの軽量防御（10月7日）

履歴書・JDは外部から入力されるUntrusted Dataであるため、Prompt Injectionリスクを改めて調査した。

Resume / Scoring / Talentの主要Promptに対して、

- 外部文書内の命令に従わない
- 入力をInstructionではなく解析対象Dataとして扱う
- System Instructionを優先する
- Schemaおよび出力契約を維持する

という**Untrusted Data Boundary**を追加した。

多言語履歴書を扱うため、特定文字列を削除するような強いFilteringは誤検知や情報欠落のリスクがあると判断し、MVPでは導入を見送った。

---

## 12. UI/UX改善・製品価値の整理（10月上旬）

機能追加と並行して、Candidate ListおよびCandidate DetailのUIを繰り返し改善した。

特に、

- Must-have判定
- Job Match Score
- AI Talent
- HR Specified Talent
- Evidence状態
- 原本履歴書
- 再評価
- 削除等の操作

を、HRが可能な限り一画面で確認できるよう再配置した。

重複していた詳細情報や不要な画面遷移を削減し、Column Width、余白、操作領域、Card構成などを複数回調整した。

目的は単なるデザイン改善ではなく、

> **AIで情報を増やすのではなく、採用担当者が読む時間を実際に減らす**

ことである。

また、LLM Timeoutや結果の陳腐化に対応するため、既存Candidateを再アップロードせずに再Scoring / 再Talent Analysisできる機能も追加した。

---

## 13. 現在の状態（10月8日）

現在、主要な業務フローは以下まで接続されている。

**JD入力・解析  
→ HR編集・保存  
→ 履歴書一括アップロード  
→ 構造化解析  
→ Candidate永続化  
→ JDとの関連付け  
→ Job Matching  
→ Must-have判定  
→ AI Talent Discovery  
→ HR Specified Talent  
→ Evidence Validation  
→ 多言語表示・分析  
→ Retry / Re-scoring  
→ 原本履歴書確認  
→ Global Candidate Pool  
→ Candidate / JD管理**

直近ではPrompt Injectionへの軽量防御まで実装した。

また、同一履歴書を複数回アップロードした場合に、Global Candidate PoolおよびJD Candidate Relationへどのように登録されるかについて、既存処理の調査を完了した。

次の改善候補として、**同一履歴書の重複登録を防止しつつ、既存Candidateを別JDに再利用できる仕組み**を検討している。

---

## 開発を通じて重視した方針

本プロジェクトでは一貫して、LLMにすべてを任せるのではなく、

**LLMが得意な意味理解・情報抽出**

と

**バックエンドが得意な検証・集計・状態管理・業務ルール**

を分離してきた。

また、新しい技術や機能についても、実際に検証した結果メリットが小さい場合は導入を撤回し、MVPに必要な価値を優先した。

現段階のResume Agentは単なる「履歴書をAIに採点させるデモ」ではなく、**HRが判断根拠を確認しながら大量候補者を効率的に絞り込むための業務支援システム**として、一連の基本フローを実行できる状態まで到達している。
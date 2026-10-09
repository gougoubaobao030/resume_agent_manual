export default {
  auth: {
    login: { title: 'ログイン', description: '管理者が事前に作成した社内アカウントを使用します。', username: 'アカウント', password: 'パスワード', submit: 'ログイン', loading: 'ログイン中…', invalidCredentials: 'アカウント名またはパスワードが正しくありません。', failed: 'ログインできませんでした。しばらくしてからもう一度お試しください。', operation: 'ログイン' },
    logout: 'ログアウト',
    password: { title: 'パスワード変更', current: '現在のパスワード', new: '新しいパスワード（8文字以上）', submit: '保存', success: 'パスワードを変更し、他のセッションを終了しました。', failed: 'パスワードを変更できませんでした。', invalidCurrent: '現在のパスワードが正しくありません。', operation: 'パスワード変更' },
  },
  common: {
    loading: '読み込み中…',
    operations: { talent: '候補者の能力分析' },
    errors: {
      network: 'サービスに接続できません。しばらくしてからもう一度お試しください。', invalidRequest: '{action}の入力内容を確認して、もう一度お試しください。',
      sessionExpired: 'ログインの有効期限が切れました。もう一度ログインしてください。', permissionDenied: 'この操作を実行する権限がありません。', notFound: '{action}に必要なデータが見つからないか、期限切れです。',
      server: 'サービスを一時的に利用できません。しばらくしてからもう一度お試しください。', invalidResponse: 'AI の応答を処理できませんでした。もう一度お試しください。', unavailable: 'AI サービスが応答していません。しばらくしてからもう一度お試しください。',
      operationFailed: '{action}に失敗しました。しばらくしてからもう一度お試しください。', resumeNoReason: '解析に失敗しました。サーバーから詳細情報が返されませんでした。', resumeUnreadable: '履歴書を読み取れませんでした。テキスト形式の PDF か確認してください。', resumeGeneric: '履歴書を解析できませんでした。ファイルの内容を確認して、もう一度お試しください。',
    },
    candidateNameMissing: '氏名を抽出できませんでした', noInformation: '情報なし', dateMissing: '期間情報なし', colon: '：',
    sourceLabel: '出典：{source}', sourceWithIndex: '出典：{source} #{index}', sourceNameWithIndex: '{source} #{index}',
    evidenceStatus: { verified: '確認済み', review: '要確認', insufficient: '根拠不足', confirmationRequired: '確認待ち' },
    match: {
      waiting: 'スコア算出待ち', noAssessment: '判定なし', mustHaveFailed: '必須条件を満たしていません',
      mustHaveConfirmation: '必須条件の確認が必要です', mustHavePassed: '必須条件を満たしています',
      scoring: 'スコア算出中…', scoringShort: 'スコア算出中', scoringFailed: 'スコア算出失敗', noScore: 'スコアなし',
      noResult: '求人マッチング結果はまだありません', noSummary: 'サーバーから総合要約が返されませんでした。',
    },
    talent: {
      analyzing: '分析中', analyzingProgress: '分析中…', failed: '分析失敗', notAnalyzed: '未分析', completed: '完了',
      specifiedFit: '指定した候補者像との適合度', attention: '注目度', reanalyze: '再分析', analyze: '候補者の能力を分析',
      level: { high: '高', mediumHigh: 'やや高い', medium: '中', mediumLow: 'やや低い', low: '低' },
    },
    requirementStatus: { matched: '適合', partiallyMatched: '一部適合', notMatched: '不適合', insufficientEvidence: '根拠不足' },
    confidence: { high: '高', medium: '中', low: '低' },
    sources: {
      workExperience: '職務経歴', projects: 'プロジェクト経験', education: '学歴', skills: 'スキル', languages: '語学力',
      certifications: '資格', achievements: '実績', candidateEvidence: '事実根拠', rawText: '履歴書原文', resume: '履歴書', mockProfile: 'サンプル',
    },
  },
  talentSettings: {
    modeLabel: '候補者の能力分析モード', autoMode: 'AI による自動分析', specifiedMode: 'HR 指定の候補者像', traitLabel: '重視する候補者の特性',
    traitPlaceholder: '例：誠実、学習が速い', add: '追加', removeLabel: '{trait}を削除', traitRequired: '分析するには特性を 1 件以上追加してください。',
  },
  dashboard: {
    eyebrow: '概要', title: '候補者スクリーニングを開始',
    description: '求人票から始め、JD の確認、履歴書のインポート、候補者の確認を順に進めます。',
    actions: { viewJob: '現在の JD を表示', createJob: 'JD を作成・解析' },
    flow: {
      eyebrow: '基本フロー', title: '現在の採用フロー', confirmed: 'JD 確認済み', notStarted: '未開始',
      steps: {
        confirm: { title: '求人要件を確認', description: 'JD を入力・解析し、HR が編集して確認' },
        import: { title: '履歴書を一括インポート', description: 'テキスト形式の PDF を 1～30 件アップロード' },
        candidates: { title: '候補者を確認', description: '構造化プロフィールと解析結果を確認' },
        review: { title: '分析・目視確認', description: 'マッチング根拠と要確認事項を確認' },
      },
    },
    session: {
      eyebrow: '現在の選考', title: '今回の処理', currentJob: '現在の JD', notSet: '未設定', candidates: '候補者', scored: 'スコア算出済み',
      note: '現在選択中の JD のデータをデータベースから表示します。',
    },
    scope: {
      eyebrow: 'システム範囲', title: '現在利用できる機能', jd: 'JD 解析・HR 確認 API を利用できます',
      resume: '単一・一括履歴書解析 API を利用できます', scoring: '求人マッチング評価 API に接続済みです',
    },
  },
  jd: {
    eyebrow: '求人票', title: 'JD の解析と確認', description: '求人票を入力して AI が要件を抽出し、HR が編集・確認して保存します。',
    sample: `職種名：AIアプリケーションエンジニア

業務内容：
1. 大規模言語モデルを活用した AI アプリケーション（RAG、チャットボット、AI エージェントなど）の開発
2. Python によるバックエンドサービスおよび REST API の設計・開発・保守
3. 業務要件に応じたプロンプト設計、モデル連携、精度改善
4. 社内ナレッジベースや文書検索機能の開発

応募要件：
1. Python を用いたバックエンド開発を独力で進められること
2. 大学卒業以上の学歴
3. FastAPI、Flask などの Python Web フレームワークを用いた実務経験
4. 大規模言語モデル、Embedding、ベクトルデータベース、RAG の基礎知識
5. 関係者と円滑に連携できるコミュニケーション能力

歓迎要件：
- LangChain、LangGraph などを用いた AI エージェント開発経験
- JLPT N1 相当、または業務上の日本語コミュニケーション能力`,
    step1: { label: 'ステップ 1', title: '求人票を入力', helper: '職種名、業務内容、スキル、経験要件を含めることを推奨します。' },
    step2: { label: 'ステップ 2', title: 'HR による確認' },
    status: { parsing: '解析中', parseSuccess: '解析成功', needsAttention: '確認が必要', waiting: '解析待ち', editable: '編集可能' },
    fields: {
      rawText: '求人票（JD）', jobId: '求人 ID', jobTitle: '職種名', requirementName: '要件名', category: 'カテゴリー', weight: '相対ウェイト',
      mustHave: '必須条件', mustHaveHint: '満たさない場合は重点確認が必要', description: '詳細',
    },
    actions: {
      parsing: '解析中…', parse: 'AI で JD を解析', addRequirement: '＋ 要件を追加', deleteRequirementLabel: '{index} 番目の要件を削除',
      delete: '削除', deleteJob: 'JD を削除', deletingJob: '削除中…', saving: '保存中…', save: '確認済み JD を保存', selectJob: '保存済み JD を選択', newJob: '新規 JD',
    },
    empty: { title: '解析結果はまだありません', description: '解析後、職種名、要件、ウェイト、必須条件をここで編集できます。' },
    parseWarnings: '解析時の注意',
    warnings: { noRequirements: '明確な応募要件を抽出できませんでした。原文を確認し、必要な要件を追加してください。', noEducation: '明確な学歴要件を抽出できませんでした。必要に応じて追加してください。', zeroWeights: 'すべての要件の推奨ウェイトが 0 のため、後続の評価では均等に扱われます。' },
    requirements: { title: '求人要件', weightNote: 'ウェイトは相対的な重要度です。保存時にフロントエンドでは正規化しません。', item: '要件 {index}' },
    categories: { technical: '技術力', experience: '職務経験', education: '学歴', other: 'その他' },
    messages: {
      loaded: '現在のセッションの JD を読み込みました。', tooShort: '求人票が短すぎます。業務内容または応募要件を追加してください。',
      parsing: 'AI が求人票を解析しています。しばらくお待ちください…', parsed: '解析が完了し、{count} 件の求人要件を抽出しました。',
      saving: 'HR 確認済みの JD を保存しています…', saved: 'JD を保存しました。この採用フローで引き続き利用できます。',
      deleteConfirm: '「{title}」を削除しますか？\n\nこの求人との候補者の関連付けと求人マッチング評価も削除されます。\n候補者情報、人材分析、元の履歴書は削除されません。',
      deleteSuccess: 'JD「{title}」を削除しました。',
      deleteReloadFailed: 'JD は削除されましたが、ワークスペースを再読み込みできませんでした。ページを更新して再試行してください。',
    },
    validation: {
      jobTitle: '職種名を入力してください。', requirementRequired: '求人要件を 1 件以上残してください。',
      requirementName: '{index} 番目の要件に名前がありません。', requirementWeight: '{index} 番目の相対ウェイトは 0～1000 の数値にしてください。',
    },
    operations: { parse: 'JD 解析', save: 'JD 保存', delete: 'JD 削除' },
  },
  resumeUpload: {
    eyebrow: '履歴書インポート', title: '候補者を一括インポート', description: '現在の求人を選択し、テキスト形式の PDF 履歴書を 1～30 件アップロードします。', jobRequired: '先に JD を完了してください',
    talentExecution: {
      title: 'この一括処理で実行する評価', jobMatch: '求人マッチング：常に実行',
    },
    dropzone: { title: 'ここに履歴書をドロップ', description: 'テキスト形式の PDF のみ、1 回につき最大 30 件。スキャン PDF は現在未対応です。' },
    selectedFiles: '選択済みファイル',
    actions: { selectFiles: 'PDF ファイルを選択', parsing: '解析中…', start: '一括解析を開始', removeLabel: '{filename} を削除', remove: '削除', retry: '再解析', retrying: '再解析中…', viewCandidates: '候補者を表示' },
    status: { pending: '待機中', running: '解析中', success: '解析完了', failed: '解析エラー' },
    summary: { completed: '完了', success: '解析完了', failed: '解析エラー', running: '処理中', pending: '待機中' },
    scoring: { running: '求人スコア算出中…', failed: '求人スコア算出失敗', completed: '求人スコア算出完了' },
    failedFiles: '解析できなかったファイル', sessionNote: '解析に成功した候補者をデータベースに保存しました。',
    note: { title: '処理について', description: '履歴書は個別に解析され、1 件の失敗で他のファイルが中断されることはありません。' },
    messages: {
      notPdf: '{filename} は PDF ファイルではありません。選択し直してください。', tooMany: '一度に選択できる履歴書は最大 30 件です。',
      taskFailed: '一括解析タスクに失敗しました：{reason}', noBackendReason: 'サーバーから具体的な理由が返されませんでした。',
      completed: '履歴書解析完了：成功 {success} 件、失敗 {failed} 件。成功した候補者の求人スコア算出を個別に開始しました。',
      pollFailed: '{error} バックグラウンドタスクはまだ実行中の可能性があります。', jobRequired: '先に JD を完了して保存してください。',
      fileRequired: 'PDF 履歴書を 1 件以上選択してください。', starting: '{count} 件の履歴書の解析タスクを作成しています…',
      taskCreated: 'タスクを作成しました。{count} 件の履歴書を解析しています…',
    },
    operations: { scoring: '求人マッチング評価', taskStatus: 'タスク状態の確認', createTask: '履歴書解析タスクの作成', retry: '履歴書の再解析' },
  },
  pdfMerge: {
    title: 'PDF 結合ツール',
    description: 'ファイルはブラウザ内でのみ結合され、RA サーバーには送信されません。',
    currentFolder: '現在のフォルダー：',
    folderPathNote: 'ブラウザにはフォルダー名のみ表示され、完全なローカルパスは提供されません。',
    availableFiles: '同じ候補者の PDF を複数選択',
    noFiles: 'このフォルダーに PDF ファイルはありません。',
    selectedCount: '{count} 件選択中',
    selectHint: 'ファイルを選択すると、ここで結合順を変更できます。',
    outputFilename: '出力ファイル名',
    actions: {
      expand: 'PDF 結合ツールを開く',
      collapse: 'PDF 結合ツールを閉じる',
      selectFolder: '履歴書フォルダーを選択',
      merge: 'PDF を結合',
      merging: '結合中…',
      moveUpLabel: '{filename} を上へ移動',
      moveDownLabel: '{filename} を下へ移動',
    },
    messages: {
      unsupported: 'このブラウザはローカルフォルダーへの書き込みに対応していません。最新版の Chrome または Edge をご利用ください。',
      folderRequired: '先に履歴書フォルダーを選択してください。',
      filesRequired: '結合する PDF ファイルを 2 件以上選択してください。',
      permissionDenied: 'フォルダーへの書き込み権限を取得できません。再度選択して許可してください。',
      openFailed: '選択したフォルダーを読み取れません。フォルダーの権限を確認してください。',
      readFailed: '読み取れません：{filename}',
      mergeFailed: 'PDF の結合に失敗しました。選択したファイルが有効か確認してください。',
      overwriteConfirm: '{filename} は既に存在します。上書きしますか？',
      writeFailed: '結合は完了しましたが、対象フォルダーに書き込めません。フォルダーの権限を確認してください。',
      merging: 'ブラウザ内で PDF を結合しています…',
      success: '生成しました：{filename}',
    },
  },
  candidates: {
    eyebrow: '候補者', title: '候補者一覧', description: 'まず求人とのマッチ度を確認し、さらに詳しく見たい人材を選択します。',
    importResumes: '履歴書をインポート', currentCandidates: '現在の候補者', personCount: '{count} 人', matchScore: '求人マッチ度',
    sortLabel: '求人マッチ度で並べ替え', sortDescending: '高い順', sortAscending: '低い順', selectAll: '現在の候補者をすべて選択',
    clearSelection: '選択を解除', selectedCount: '{count} 人を選択中', analyzeSelected: '選択した候補者の能力を分析', selectCandidate: '{name} を選択',
    actions: { rescoreSelected: '選択した候補者を再評価', rescoring: '再評価中…', viewResume: '元の履歴書', viewDetails: '詳細', more: 'その他の操作' },
    messages: { rescoreSuccess: '評価を更新しました', rescorePartialFailed: '{success}名の再評価が完了し、{failed}名が失敗しました', rescoreFailed: '{failed}名の再評価に失敗しました', removeSuccess: '{name} を現在の求人から削除しました。' },
    operations: { rescore: '再評価', remove: '現在の求人から削除' },
    removeFromJob: '現在の求人から削除', removing: '削除中…',
    removeConfirm: '{name} を現在の求人からのみ削除し、この求人のマッチング評価を削除します。候補者情報と元の履歴書は候補者一覧に保持されます。',
    locationMissing: '所在地情報なし', highlights: '強み：', noHighlights: '明確な強みなし', viewResume: '元の履歴書を表示', viewDetails: '詳細を表示',
    mustHaveSummary: { allMet: '{passed}/{total} 充足', unmet: '{passed}/{total} {count}項目不足' },
    table: { select: '選択', candidate: '候補者', matchScore: '求人マッチ度', mustHave: '必須条件', assessment: '求人判定', autoTalent: 'AI による能力分析', specifiedTalent: 'HR 指定の候補者像', actions: '操作' },
    empty: { title: '候補者はまだいません', description: '履歴書のインポート後、解析に成功した候補者がここに表示されます。', action: '履歴書インポートへ →' },
  },
  candidatePool: {
    eyebrow: '全候補者', title: '候補者一覧', description: 'システムに保存されているすべての候補者を表示します。',
    allCandidates: 'すべての候補者', personCount: '{count} 人', experienceMissing: '職務経歴情報なし', skills: '主なスキル', skillsMissing: 'スキル情報なし', jobs: '参加した求人', jobsMissing: '関連する求人なし', sourceFile: '元の履歴書', createdAt: 'アップロード日時', viewDetails: '詳細を表示', viewResume: '元の履歴書を表示', resumeMissing: '元の履歴書を利用できません', deleteCandidate: '候補者を削除', deleting: '削除中…',
    deleteConfirm: '{name} の元の履歴書、すべての求人との関連、すべての求人評価、人材分析結果を完全に削除します。この操作は元に戻せません。',
    messages: { deleteSuccess: '候補者 {name} を削除しました。' },
    operations: { load: '候補者一覧の読み込み', delete: '候補者の削除' },
    empty: { title: '候補者一覧は空です', description: '正常にインポートされた候補者がここに表示されます。' },
  },
  candidateDetail: {
    back: '← 候補者一覧に戻る', backToPool: '← 候補者一覧に戻る', title: '候補者詳細', sourceFileMissing: '元のファイル名を取得できませんでした', viewResume: '元の履歴書を表示', viewEvidence: '根拠を表示', currentJob: '現在の JD：', notFound: '現在のセッションにこの候補者は見つかりませんでした。',
    actions: { rescore: '再評価', rescoring: '再評価中…', cancel: 'キャンセル', runSpecifiedAnalysis: '現在の特性で再分析' },
    messages: { rescoreSuccess: '評価を更新しました。' },
    warnings: {
      scoringEvidence: '一部の求人マッチング根拠は原文または出典位置を確認できず、関連する結論を人による確認が必要としてマークしました。',
      autoEvidence: '一部の AI 能力の根拠を履歴書で確認できませんでした。有効な根拠のない評価は自動的に除外し、要確認のまま残る評価は人による確認が必要です。',
      specifiedEvidence: '一部の指定人材特性には検証可能な根拠がなく、根拠不足として人による確認が必要です。',
    },
    metrics: { mustHave: '必須条件', autoTalent: 'AI 能力注目度', specifiedTalent: 'HR 指定能力適合度' },
    empty: { title: '候補者データを利用できません', description: '候補者がデータベースに存在しないか、選択中の JD に関連付けられていません。', action: '候補者一覧に戻る →', poolAction: '候補者一覧に戻る →' },
    basicInfo: { title: '基本情報', name: '氏名', location: '所在地', email: 'メール', phone: '電話' },
    match: { title: '求人マッチング概要', score: '求人マッチ度', requirements: '求人要件との適合', noResult: '現在のセッションにこの候補者の求人マッチング結果はありません。', highlights: '主な強み', risks: 'リスク / 要確認事項', noHighlights: '明確な高適合項目はありません。', noRisks: '明確なリスク項目はありません。', warningTitle: '根拠の確認が必要' },
    talent: {
      title: '候補者の能力分析', specifiedProfile: 'HR 指定の候補者像', evidence: '主な根拠', missingInformation: '要確認情報',
      additionalFindings: 'AI による追加発見', abilityProfile: '能力プロフィール', noAbilities: '追加能力を示す明確な根拠はありません。', warnings: '分析上の注意',
      autoTitle: 'AI 能力発見', specifiedTitle: 'HR 指定能力',
    },
    resume: {
      education: '学歴', degreeMissing: '学位・専攻情報なし', noEducation: '学歴情報なし', workExperience: '職務経歴', noWorkExperience: '職務経歴なし',
      projects: 'プロジェクト経験', noProjects: 'プロジェクト経験なし', skillsAndLanguages: 'スキル・語学', skills: 'スキル', noSkills: 'スキル情報なし',
      languages: '語学力', noLanguages: '語学情報なし', certifications: '資格', noCertifications: '資格情報なし', achievements: '実績', noAchievements: '実績情報なし',
    },
    evidence: { title: 'その他の能力 / 事実根拠', defaultTitle: '事実根拠', empty: 'その他の事実根拠はありません' },
    metadata: {
      title: '解析情報', sourceFile: '元ファイル', parser: '解析ツール', model: 'モデル', confidence: '抽出信頼度',
      customFields: 'カスタム項目', noCustomFields: 'カスタム項目なし',
    },
    rawText: { title: '履歴書原文を表示', empty: '履歴書原文なし' },
  },
  analysis: {
    eyebrow: '求人マッチング', title: '求人マッチング分析', currentJob: '現在の求人', description: '現在のセッションでバックエンドが完了した実際の求人マッチング結果を表示します。',
    candidate: '候補者', empty: { title: '求人マッチング結果はありません', description: '先に JD を保存して履歴書をインポートすると、既存の求人マッチング API が呼び出されます。', action: '履歴書インポートへ →' },
    matchScore: '求人マッチ度', overallAssessment: '総合判定',
    rawReview: { title: '履歴書原文の確認を推奨', description: '一部の要件は履歴書原文と照合して追加確認する必要があります。' },
    mustHave: '必須条件', confidence: '判定信頼度：{value}', reason: '判定理由', resumeEvidence: '履歴書の根拠',
    missingInformation: '要確認情報', overallMissingInformation: '全体の要確認情報',
    viewEvidence: '根拠を表示',
  },
  layout: {
    brandSubtitle: '採用分析ワークスペース',
    navigation: {
      label: 'メインナビゲーション',
      dashboard: 'ダッシュボード',
      jobs: '求人票管理',
      resumes: '履歴書インポート',
      candidates: '求人候補者一覧',
      candidatePool: '候補者プール',
      candidateDetail: '候補者詳細',
      expand: 'ナビを展開',
      collapse: 'ナビを折りたたむ',
      expandHint: 'ナビゲーションを展開',
      collapseHint: 'ナビゲーションを折りたたむ',
      openHint: 'ナビゲーションを開く',
      closeHint: 'ナビゲーションを閉じる',
    },
    footer: {
      phase: 'MVP 開発段階',
      status: '求人マッチング評価を実装済み',
    },
    header: {
      workbench: '採用一次選考ワークスペース',
    },
    language: {
      selectorLabel: '表示言語',
      zhCN: '中文',
      jaJP: '日本語',
      enUS: 'English',
    },
  },
}

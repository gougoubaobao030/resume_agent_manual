export default {
  auth: {
    login: { title: 'Sign in', description: 'Use an internal account created by an administrator.', username: 'Username', password: 'Password', submit: 'Sign in', loading: 'Signing in…', invalidCredentials: 'The username or password is incorrect.', failed: 'Could not sign in. Please try again.', operation: 'Sign-in' },
    logout: 'Sign out',
    password: { title: 'Change password', current: 'Current password', new: 'New password (8+ characters)', submit: 'Save password', success: 'Password changed; other sessions were signed out.', failed: 'Could not change password.', invalidCurrent: 'The current password is incorrect.', operation: 'Password change' },
  },
  common: {
    loading: 'Loading…',
    operations: { talent: 'Talent analysis' },
    errors: {
      network: 'Could not connect to the service. Please try again.', invalidRequest: 'Check the information submitted for {action} and try again.',
      sessionExpired: 'Your session has expired. Please sign in again.', permissionDenied: 'You do not have permission to perform this action.', notFound: 'The data required for {action} could not be found or has expired.',
      server: 'The service is temporarily unavailable. Please try again later.', invalidResponse: 'The AI response could not be processed. Please try again.', unavailable: 'The AI service is not responding. Please try again later.',
      operationFailed: '{action} failed. Please try again.', resumeNoReason: 'Parsing failed, and the server did not provide a reason.', resumeUnreadable: 'The resume could not be read. Make sure it is a text-based PDF.', resumeGeneric: 'The resume could not be parsed. Check the file and try again.',
    },
    candidateNameMissing: 'Name not extracted', noInformation: 'No information available', dateMissing: 'Dates unavailable', colon: ': ',
    sourceLabel: 'Source: {source}', sourceWithIndex: 'Source: {source} #{index}', sourceNameWithIndex: '{source} #{index}',
    match: {
      waiting: 'Awaiting score', noAssessment: 'No assessment', mustHaveFailed: 'Must-have criteria not met',
      mustHaveConfirmation: 'Must-have criteria need confirmation', mustHavePassed: 'Must-have criteria met',
      scoring: 'Scoring…', scoringShort: 'Scoring', scoringFailed: 'Scoring failed', noScore: 'No score',
      noResult: 'No job-match result yet', noSummary: 'No overall summary was returned by the server.',
    },
    talent: {
      analyzing: 'Analyzing', analyzingProgress: 'Analyzing…', failed: 'Analysis failed', notAnalyzed: 'Not analyzed', completed: 'Completed',
      specifiedFit: 'Target profile fit', attention: 'Talent priority', reanalyze: 'Analyze again', analyze: 'Analyze capabilities',
      level: { high: 'High', mediumHigh: 'Medium-high', medium: 'Medium', mediumLow: 'Medium-low', low: 'Low' },
    },
    requirementStatus: { matched: 'Met', partiallyMatched: 'Partially met', notMatched: 'Not met', insufficientEvidence: 'Insufficient evidence' },
    confidence: { high: 'High', medium: 'Medium', low: 'Low' },
    sources: {
      workExperience: 'Work experience', projects: 'Projects', education: 'Education', skills: 'Skills', languages: 'Languages',
      certifications: 'Certifications', achievements: 'Achievements', candidateEvidence: 'Supporting facts', rawText: 'Original resume', resume: 'Resume', mockProfile: 'Mock example',
    },
  },
  talentSettings: {
    modeLabel: 'Talent analysis mode', autoMode: 'AI discovery', specifiedMode: 'HR target profile', traitLabel: 'Target traits',
    traitPlaceholder: 'For example: dependable, quick learner', add: 'Add', removeLabel: 'Remove {trait}', traitRequired: 'Add at least one trait before running the analysis.',
  },
  dashboard: {
    eyebrow: 'Overview', title: 'Start screening candidates',
    description: 'Begin with the job description, then confirm the JD, import resumes, and review candidates.',
    actions: { viewJob: 'View Current JD', createJob: 'Create and Parse JD' },
    flow: {
      eyebrow: 'Core Flow', title: 'Current Hiring Workflow', confirmed: 'JD Confirmed', notStarted: 'Not Started',
      steps: {
        confirm: { title: 'Confirm Job Requirements', description: 'Enter and parse the JD, then have HR review it' },
        import: { title: 'Import Resumes in Bulk', description: 'Upload 1–30 text-based PDFs' },
        candidates: { title: 'Review Candidates', description: 'Inspect structured profiles and parsing results' },
        review: { title: 'Analyze and Review', description: 'Review match evidence and items needing confirmation' },
      },
    },
    session: {
      eyebrow: 'Current Session', title: 'This Session', currentJob: 'Current JD', notSet: 'Not set', candidates: 'Candidates', scored: 'Scored',
      note: 'Data for the currently selected JD is loaded from the database.',
    },
    scope: {
      eyebrow: 'System Scope', title: 'Currently Available', jd: 'JD parsing and HR confirmation APIs are available',
      resume: 'Single and batch resume parsing APIs are available', scoring: 'Job-match scoring API is connected',
    },
  },
  jd: {
    eyebrow: 'Job Description', title: 'Parse and Confirm JD', description: 'Enter a job description for AI extraction, then let HR edit, confirm, and save the requirements.',
    sample: `Job title: AI Application Engineer

Responsibilities:
1. Develop AI applications using large language models, including RAG, chatbots, and AI agents.
2. Design, develop, and maintain backend services and REST APIs in Python.
3. Create prompts, integrate models, and improve output quality based on business requirements.
4. Build internal knowledge-base and document-retrieval features.

Requirements:
1. Strong Python skills and the ability to develop backend features independently.
2. A bachelor's degree or higher is required.
3. Hands-on experience with Python web frameworks such as FastAPI or Flask.
4. Familiarity with large language models, embeddings, vector databases, and RAG.
5. Strong analytical, learning, and communication skills.

Preferred qualifications:
- Experience developing AI agents with LangChain, LangGraph, or similar frameworks.
- JLPT N1-level Japanese or the ability to communicate in Japanese at work.`,
    step1: { label: 'Step 1', title: 'Enter Job Description', helper: 'Include the job title, responsibilities, skills, and experience requirements.' },
    step2: { label: 'Step 2', title: 'HR Review' },
    status: { parsing: 'Parsing', parseSuccess: 'Parsed', needsAttention: 'Needs review', waiting: 'Awaiting parsing', editable: 'Editable' },
    fields: {
      rawText: 'Job Description (JD)', jobId: 'Job ID', jobTitle: 'Job Title', requirementName: 'Requirement Name', category: 'Category', weight: 'Relative Weight',
      mustHave: 'Must-have', mustHaveHint: 'Requires close review if unmet', description: 'Details',
    },
    actions: {
      parsing: 'Parsing…', parse: 'Parse JD with AI', addRequirement: '+ Add Requirement', deleteRequirementLabel: 'Delete requirement {index}',
      delete: 'Delete', saving: 'Saving…', save: 'Save Confirmed JD', selectJob: 'Select saved JD', newJob: 'New JD',
    },
    empty: { title: 'No Parsing Result Yet', description: 'After parsing, you can edit the job title, requirements, weights, and must-have criteria here.' },
    parseWarnings: 'Parsing Notes',
    warnings: { noRequirements: 'No clear job requirements were identified. Review the original text and add the required items.', noEducation: 'No clear education requirement was identified. Add one if needed.', zeroWeights: 'All suggested requirement weights are 0, so they will be weighted equally during scoring.' },
    requirements: { title: 'Job Requirements', weightNote: 'Weights indicate relative importance and are not normalized in the frontend when saved.', item: 'Requirement {index}' },
    categories: { technical: 'Technical Skills', experience: 'Work Experience', education: 'Education', other: 'Other' },
    messages: {
      loaded: 'The JD from this session has been loaded.', tooShort: 'The job description is too short. Add responsibilities or requirements.',
      parsing: 'AI is parsing the job description. Please wait…', parsed: 'Parsing complete. {count} job requirements identified.',
      saving: 'Saving the HR-confirmed JD…', saved: 'The JD has been saved and is ready for this hiring workflow.',
    },
    validation: {
      jobTitle: 'Enter a job title.', requirementRequired: 'Keep at least one job requirement.',
      requirementName: 'Requirement {index} is missing a name.', requirementWeight: 'The relative weight for requirement {index} must be a number between 0 and 1000.',
    },
    operations: { parse: 'JD parsing', save: 'JD saving' },
  },
  resumeUpload: {
    eyebrow: 'Resume Import', title: 'Import Candidates in Bulk', description: 'Select the current job, then upload 1–30 text-based PDF resumes.', jobRequired: 'Complete the JD first',
    talentExecution: {
      title: 'Evaluations for This Batch', jobMatch: 'Job matching: always included',
    },
    dropzone: { title: 'Drop Resumes Here', description: 'Text-based PDFs only, up to 30 at a time. Scanned PDFs are not supported yet.' },
    selectedFiles: 'Selected Files',
    actions: { selectFiles: 'Select PDF Files', parsing: 'Parsing…', start: 'Start Batch Parsing', removeLabel: 'Remove {filename}', remove: 'Remove', viewCandidates: 'View Candidates' },
    status: { pending: 'Pending', running: 'Parsing', success: 'Parsed', failed: 'Failed' },
    summary: { completed: 'Completed', success: 'Parsed', failed: 'Failed', running: 'Processing', pending: 'Pending' },
    scoring: { running: 'Job scoring…', failed: 'Job scoring failed', completed: 'Job scoring complete' },
    failedFiles: 'Files That Could Not Be Parsed', sessionNote: 'Successfully parsed candidates have been saved to the database.',
    note: { title: 'Processing Notes', description: 'Each resume is parsed independently; one failure will not interrupt other files.' },
    messages: {
      notPdf: '{filename} is not a PDF file. Select another file.', tooMany: 'You can select up to 30 resumes at a time.',
      taskFailed: 'Batch parsing failed: {reason}', noBackendReason: 'The server did not return a specific reason.',
      completed: 'Resume parsing complete: {success} succeeded and {failed} failed. Job scoring has started separately for successful candidates.',
      pollFailed: '{error} The background task may still be running.', jobRequired: 'Complete and save the JD first.',
      fileRequired: 'Select at least one PDF resume first.', starting: 'Parsing {count} resumes. Keep this page open…',
      taskCreated: 'Task created. Parsing {count} resumes…',
    },
    operations: { scoring: 'Job-match scoring', taskStatus: 'Task status check', createTask: 'Resume parsing task creation' },
  },
  candidates: {
    eyebrow: 'Candidates', title: 'Candidate List', description: 'Review job matches first, then select candidates worth exploring further.',
    importResumes: 'Import Resumes', currentCandidates: 'Current Candidates', personCount: '{count} people', matchScore: 'Match Score',
    sortLabel: 'Sort by match score', sortDescending: 'High to Low', sortAscending: 'Low to High', selectAll: 'Select All Current Candidates',
    clearSelection: 'Clear Selection', selectedCount: '{count} selected', analyzeSelected: 'Analyze Selected Candidates', selectCandidate: 'Select {name}',
    actions: { rescoreSelected: 'Rescore selected candidates', rescoring: 'Rescoring…' },
    messages: { rescoreSuccess: 'Scores updated', rescorePartialFailed: '{success} candidates rescored, {failed} failed', rescoreFailed: '{failed} candidates failed to rescore', removeSuccess: '{name} was removed from the current job.' },
    operations: { rescore: 'Candidate rescoring', remove: 'Remove from current job' },
    removeFromJob: 'Remove from Current Job', removing: 'Removing…',
    removeConfirm: 'This only removes {name} from the current job and deletes the match score for this job. The candidate profile and original resume will remain in Candidate Pool.',
    locationMissing: 'Location unavailable', highlights: 'Highlights: ', noHighlights: 'No clear highlights', viewResume: 'View Original Resume', viewDetails: 'View Details',
    table: { select: 'Select', candidate: 'Candidate', matchScore: 'Match Score', mustHave: 'Must-haves', assessment: 'Job Assessment', autoTalent: 'AI Capabilities', specifiedTalent: 'HR Target Profile', actions: 'Actions' },
    empty: { title: 'No Candidates Yet', description: 'Candidates whose resumes are parsed successfully will appear here.', action: 'Go to Resume Import →' },
  },
  candidatePool: {
    eyebrow: 'Global Candidates', title: 'Candidate Pool', description: 'View every candidate saved in the system.',
    allCandidates: 'All Candidates', personCount: '{count} people', experienceMissing: 'Work experience unavailable', skills: 'Key Skills', skillsMissing: 'No skills available', jobs: 'Participating Jobs', jobsMissing: 'No linked jobs', sourceFile: 'Original File', createdAt: 'Uploaded', viewDetails: 'View Details', viewResume: 'View Original Resume', resumeMissing: 'Original resume unavailable', deleteCandidate: 'Delete Candidate', deleting: 'Deleting…',
    deleteConfirm: 'This will permanently delete {name}, the original resume, every job link, every job score, and all talent analysis results. This cannot be undone.',
    messages: { deleteSuccess: 'Candidate {name} was deleted.' },
    operations: { load: 'Load Candidate Pool', delete: 'Delete candidate' },
    empty: { title: 'Candidate Pool Is Empty', description: 'Successfully imported candidates will appear here.' },
  },
  candidateDetail: {
    back: '← Back to Candidate List', backToPool: '← Back to Candidate Pool', title: 'Candidate Details', sourceFileMissing: 'Source filename unavailable', viewResume: 'View Original Resume', viewEvidence: 'View Evidence', currentJob: 'Current JD:', notFound: 'This candidate was not found in the current session.',
    actions: { rescore: 'Rescore', rescoring: 'Rescoring…' },
    messages: { rescoreSuccess: 'Score updated.' },
    metrics: { mustHave: 'Must-have Conditions', autoTalent: 'AI Capability Attention', specifiedTalent: 'HR Target Fit' },
    empty: { title: 'Candidate Data Unavailable', description: 'This candidate is not in the database or is not linked to the selected JD.', action: 'Back to Candidate List →', poolAction: 'Back to Candidate Pool →' },
    basicInfo: { title: 'Basic Information', name: 'Name', location: 'Location', email: 'Email', phone: 'Phone' },
    match: { title: 'Job Match Summary', score: 'Match Score', requirements: 'Requirement Matches', viewDetails: 'View Full Scoring Evidence', noResult: 'No job-match result for this candidate exists in the current session.', highlights: 'Key Strengths', risks: 'Risks / Items to Confirm', noHighlights: 'No clear high-match requirements.', noRisks: 'No material risks identified.' },
    talent: {
      title: 'Capability Discovery', specifiedProfile: 'HR Target Profile', evidence: 'Key Evidence', missingInformation: 'Information to Confirm',
      additionalFindings: 'Additional AI Findings', abilityProfile: 'Capability Profile', noAbilities: 'No clear evidence of additional capabilities.', warnings: 'Analysis Notes',
      autoTitle: 'AI Capability Discovery', specifiedTitle: 'HR-Specified Capabilities', settingsTitle: 'Capability Analysis Settings', settingsDescription: 'Configure HR-specified capabilities or select the analysis mode to edit.',
    },
    resume: {
      education: 'Education', degreeMissing: 'Degree and major unavailable', noEducation: 'No education information', workExperience: 'Work Experience',
      noWorkExperience: 'No work experience', projects: 'Projects', noProjects: 'No project experience', skillsAndLanguages: 'Skills and Languages',
      skills: 'Skills', noSkills: 'No skills information', languages: 'Languages', noLanguages: 'No language information', certifications: 'Certifications',
      noCertifications: 'No certification information', achievements: 'Achievements', noAchievements: 'No achievement information',
    },
    evidence: { title: 'Other Capabilities / Supporting Facts', defaultTitle: 'Supporting Fact', empty: 'No other supporting facts' },
    metadata: {
      title: 'Parsing Information', sourceFile: 'Source File', parser: 'Parser', model: 'Model', confidence: 'Extraction Confidence',
      customFields: 'Custom Fields', noCustomFields: 'No custom fields',
    },
    rawText: { title: 'View Original Resume', empty: 'Original resume unavailable' },
  },
  analysis: {
    eyebrow: 'Job Match', title: 'Job Match Analysis', currentJob: 'Current Job', description: 'Shows actual job-match results completed by the backend in this session.',
    candidate: 'Candidate', empty: { title: 'No Job-Match Results', description: 'Save a JD and import resumes first; the existing job-match API will then be called.', action: 'Go to Resume Import →' },
    matchScore: 'Match Score', overallAssessment: 'Overall Assessment',
    rawReview: { title: 'Review the Original Resume', description: 'Some requirements need further confirmation against the original resume.' },
    mustHave: 'Must-have', confidence: 'Assessment confidence: {value}', reason: 'Assessment Rationale', resumeEvidence: 'Resume Evidence',
    missingInformation: 'Information to Confirm', overallMissingInformation: 'Overall Information to Confirm',
    viewEvidence: 'View Evidence',
  },
  layout: {
    brandSubtitle: 'Recruiting Analytics Workspace',
    navigation: {
      label: 'Primary navigation',
      dashboard: 'Dashboard',
      jobs: 'Job Descriptions',
      resumes: 'Resume Import',
      candidates: 'Candidates',
      candidatePool: 'Candidate Pool',
      analysis: 'Analysis Results',
      candidateDetail: 'Candidate Details',
      expand: 'Expand navigation',
      collapse: 'Collapse navigation',
      expandHint: 'Expand navigation sidebar',
      collapseHint: 'Collapse navigation sidebar',
      openHint: 'Open navigation',
      closeHint: 'Close navigation',
    },
    footer: {
      phase: 'MVP Development',
      status: 'Job matching scores enabled',
    },
    header: {
      workbench: 'Recruiting Screening Workspace',
    },
    language: {
      selectorLabel: 'Interface language',
      zhCN: '中文',
      jaJP: '日本語',
      enUS: 'English',
    },
  },
}

import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import AppNavbar from '../../components/AppNavbar/AppNavbar';
import Footer from '../../components/Footer/Footer';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/* ── Icons ── */
const FileIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
    <line x1="16" y1="13" x2="8" y2="13" />
    <line x1="16" y1="17" x2="8" y2="17" />
    <polyline points="10 9 9 9 8 9" />
  </svg>
);

const DownloadIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <polyline points="7 10 12 15 17 10" />
    <line x1="12" y1="15" x2="12" y2="3" />
  </svg>
);

const CheckIcon = () => (
  <svg width="10" height="8" viewBox="0 0 10 8" fill="none">
    <path d="M1 4L3.5 6.5L9 1" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const ChevronUpIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="18 15 12 9 6 15" />
  </svg>
);

const ChevronDownIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="6 9 12 15 18 9" />
  </svg>
);

const UserIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="8" r="4" /><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" />
  </svg>
);

const BrainIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 5a3 3 0 1 0-5.997.142 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z" />
    <path d="M12 5a3 3 0 1 1 5.997.142 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z" />
    <path d="M15 13a4.5 4.5 0 0 1-3-4 4.5 4.5 0 0 1-3 4" />
    <path d="M17.599 6.5a3 3 0 0 0 .399-1.375" />
    <path d="M6.003 5.125A3 3 0 0 0 6.401 6.5" />
    <path d="M3.477 10.896a4 4 0 0 1 .585-.396" />
    <path d="M19.938 10.5a4 4 0 0 1 .585.396" />
    <path d="M6 18a4 4 0 0 1-1.967-.516" />
    <path d="M19.967 17.484A4 4 0 0 1 18 18" />
  </svg>
);

const PlusIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
  </svg>
);

const XIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
    <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
  </svg>
);

const MapPinIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 1 1 16 0Z" />
    <circle cx="12" cy="10" r="3" />
  </svg>
);

/* ── Step Indicator ── */
const StepItem = ({ status, title, subtitle, showLine }) => {
  const isDone = status === 'done';
  const isActive = status === 'active';

  return (
    <div className="flex items-start gap-4 relative">
      <div className="flex flex-col items-center flex-shrink-0">
        {isDone ? (
          <div className="w-6 h-6 rounded-full bg-[#2563EB] flex items-center justify-center">
            <CheckIcon />
          </div>
        ) : isActive ? (
          <div className="w-6 h-6 rounded-full border-2 border-[#2563EB] flex items-center justify-center">
            <div className="w-2 h-2 rounded-full bg-[#2563EB] animate-pulse" />
          </div>
        ) : (
          <div className="w-6 h-6 rounded-full border-2 border-[#C5C6CD]" />
        )}
        {showLine && (
          <div className={`w-0.5 h-6 mt-1 ${isDone ? 'bg-[#2563EB]/20' : 'bg-[#C5C6CD]/30'}`} />
        )}
      </div>
      <div className="pb-1">
        <p className={`text-base font-medium leading-6 ${isActive || isDone ? 'text-[#0D1C2D]' : 'text-[#75777D]'}`}>
          {title}
        </p>
        <p className={`text-sm leading-5 ${isActive ? 'text-[#2563EB]' : isDone ? 'text-[#75777D]' : 'text-[#C5C6CD]'}`}>
          {subtitle}
        </p>
      </div>
    </div>
  );
};

/* ── Editable Field ── */
const EditableField = ({ label, value, onChange, multiline = false }) => (
  <div className="flex flex-col gap-2 w-full">
    <label className="text-sm font-semibold text-[#45474C]">{label}</label>
    {multiline ? (
      <textarea
        rows={3}
        value={value}
        onChange={onChange}
        className="w-full px-2 py-3 border border-[#C5C6CD] rounded-lg text-base text-[#0F172A] focus:outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-blue-100 resize-none transition-all"
      />
    ) : (
      <input
        type="text"
        value={value}
        onChange={onChange}
        className="w-full px-2 py-3 h-[45px] border border-[#C5C6CD] rounded-lg text-base text-[#0F172A] focus:outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-blue-100 transition-all"
      />
    )}
  </div>
);

/* ── Section Header ── */
const SectionHeader = ({ icon, title, isExpanded, onToggle }) => (
  <button
    type="button"
    onClick={onToggle}
    className="flex items-center justify-between w-full pb-2 border-b border-black/[0.08] group"
  >
    <div className="flex items-center gap-2">
      <span className="text-[#0D1C2D]">{icon}</span>
      <span className="text-2xl font-semibold text-[#0D1C2D]">{title}</span>
    </div>
    <span className="text-[#75777D] group-hover:text-[#0D1C2D] transition-colors">
      {isExpanded ? <ChevronUpIcon /> : <ChevronDownIcon />}
    </span>
  </button>
);

/* ── Skill Chip ── */
const SkillChip = ({ label, onRemove }) => (
  <div className="flex items-center gap-1 px-3 py-1.5 bg-[#D4E4FA] border border-[#6366F1] rounded-full">
    <span className="text-sm font-medium text-[#2563EB]">{label}</span>
    {onRemove && (
      <button
        type="button"
        onClick={onRemove}
        className="ml-1 text-[#2563EB] hover:text-blue-800 transition-colors"
      >
        <XIcon />
      </button>
    )}
  </div>
);

/* ── Main Page ── */
const STEPS = [
  { title: 'Uploading file', active: 'Securely sending to server...', done: 'File successfully uploaded.', pending: 'Waiting to upload...' },
  { title: 'Extracting text', active: 'Parsing semantic content...', done: 'Text extracted successfully.', pending: 'Waiting for extraction...' },
  { title: 'Identifying skills', active: 'Running model extraction...', done: 'Skills identified.', pending: 'Waiting for model extraction...' },
];

const AnalyzingPage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const file = location.state?.file;

  const [stepStatuses, setStepStatuses] = useState(['active', 'pending', 'pending']);
  const [analysisId, setAnalysisId] = useState(null);
  const [profile, setProfile] = useState({ name: '', email_address: '', phone: '', location: '' });
  const [skills, setSkills] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [expanded, setExpanded] = useState({ personal: true, skills: true });
  const [newSkill, setNewSkill] = useState('');
  const [showAddInput, setShowAddInput] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!file) { navigate('/analyze'); return; }
    runAnalysis();
  }, []);

  const runAnalysis = async () => {
    setStepStatuses(['active', 'pending', 'pending']);
    await sleep(700);
    setStepStatuses(['done', 'active', 'pending']);

    try {
      const formData = new FormData();
      formData.append('cv_file', file);
      const token = localStorage.getItem('token');

      const res = await fetch(`${import.meta.env.VITE_API_URL}/api/cv/analyze`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      const data = await res.json();

      if (res.status === 401) {
        localStorage.removeItem('token');
        navigate('/login');
        return;
      }

      if (!res.ok) {
        setError(data.message || 'Gagal menganalisis CV.');
        setStepStatuses(['done', 'done', 'pending']);
        setIsLoading(false);
        return;
      }

      setStepStatuses(['done', 'done', 'active']);
      await sleep(600);
      setStepStatuses(['done', 'done', 'done']);

      setAnalysisId(data.data.id);
      setProfile(data.data.profile_entities || {});
      setSkills(data.data.extracted_skills || []);
    } catch {
      setError('Tidak dapat terhubung ke server.');
    } finally {
      setIsLoading(false);
    }
  };

  const removeSkill = (i) => setSkills((prev) => prev.filter((_, idx) => idx !== i));

  const addSkill = () => {
    const trimmed = newSkill.trim();
    if (!trimmed) return;
    setSkills((prev) => [...prev, { surface: trimmed, normalized_guess: trimmed.toLowerCase() }]);
    setNewSkill('');
    setShowAddInput(false);
  };

  const handleAnalyze = async () => {
    if (!analysisId) return;
    setSubmitting(true);
    navigate(`/recommend/${analysisId}`, { state: { skills, profile } });
  };

  const toggle = (key) => setExpanded((prev) => ({ ...prev, [key]: !prev[key] }));

  const allDone = stepStatuses.every((s) => s === 'done');
  const fileSize = file ? `${(file.size / 1024 / 1024).toFixed(1)} MB` : '';

  return (
    <div className="min-h-screen flex flex-col bg-[#F8F9FF]">
      <AppNavbar activeTab="analyze" />

      <main className="flex-1 flex flex-col gap-8 px-8 py-8 pt-[104px] pb-[104px]">
        {/* Page Header */}
        <div className="flex flex-col gap-1">
          <h1 className="text-[40px] font-bold leading-[48px] tracking-[-0.8px] text-black">
            Processing Document
          </h1>
          <p className="text-lg text-[#45474C]">
            Our AI is analyzing your uploaded content to identify skill gaps and professional insights.
          </p>
        </div>

        {/* Two Column Layout */}
        <div className="flex gap-8 items-start w-full">

          {/* Left Column */}
          <div className="flex flex-col gap-4 w-[592px] flex-shrink-0">

            {/* Uploaded File Card */}
            <div className="bg-white border border-black/[0.08] shadow-[0_1px_2px_rgba(0,0,0,0.05)] rounded-xl p-6">
              <div className="flex items-center justify-between">
                <div className="flex flex-col gap-2">
                  <div className="flex items-center gap-3">
                    <span className="text-[#45474C]"><FileIcon /></span>
                    <div className="flex flex-col">
                      <span className="text-sm font-medium text-[#45474C]">
                        {file?.name || 'Unknown file'}
                      </span>
                      <span className="text-xs font-semibold text-[#75777D] tracking-wide">
                        {fileSize}
                      </span>
                    </div>
                  </div>
                </div>
                {file && (
                  <a
                    href={URL.createObjectURL(file)}
                    download={file.name}
                    className="text-[#45474C] hover:text-[#2563EB] transition-colors"
                  >
                    <DownloadIcon />
                  </a>
                )}
              </div>
            </div>

            {/* Processing Steps Card */}
            <div className="bg-white border border-black/[0.08] shadow-[0_1px_2px_rgba(0,0,0,0.05)] rounded-xl p-6 flex flex-col gap-3">
              {STEPS.map((step, i) => {
                const status = stepStatuses[i];
                const subtitle =
                  status === 'done' ? step.done :
                  status === 'active' ? step.active :
                  step.pending;
                return (
                  <StepItem
                    key={i}
                    status={status}
                    title={step.title}
                    subtitle={subtitle}
                    showLine={i < STEPS.length - 1}
                  />
                );
              })}
            </div>

            {/* Error */}
            {error && (
              <div className="w-full px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-600">
                {error}
              </div>
            )}
          </div>

          {/* Right Column — Extracted Profile */}
          <div className="flex-1 bg-white border border-black/[0.08] shadow-[0_1px_2px_rgba(0,0,0,0.05)] rounded-xl flex flex-col overflow-hidden">

            {/* Card Header */}
            <div className="px-6 py-6 border-b border-black/[0.08] flex-shrink-0">
              <h2 className="text-3xl font-semibold text-black">Extracted Profile</h2>
              <p className="text-base text-[#45474C] mt-1">
                Review and refine the AI-extracted data before analysis.
              </p>
            </div>

            {/* Card Body */}
            <div className={`flex flex-col gap-9 p-6 transition-all ${!allDone ? 'opacity-40 pointer-events-none select-none' : ''}`}>

              {/* Personal Information */}
              <div className="flex flex-col gap-3">
                <SectionHeader
                  icon={<UserIcon />}
                  title="Personal Information"
                  isExpanded={expanded.personal}
                  onToggle={() => toggle('personal')}
                />
                {expanded.personal && (
                  <div className="bg-[#F8F9FF] border border-black/[0.08] rounded-lg p-4 flex flex-col gap-4">
                    <EditableField
                      label="Name"
                      value={profile.name || ''}
                      onChange={(e) => setProfile((p) => ({ ...p, name: e.target.value }))}
                    />
                    <EditableField
                      label="Email"
                      value={profile.email_address || ''}
                      onChange={(e) => setProfile((p) => ({ ...p, email_address: e.target.value }))}
                    />
                    <EditableField
                      label="Phone"
                      value={profile.phone || ''}
                      onChange={(e) => setProfile((p) => ({ ...p, phone: e.target.value }))}
                    />
                    <EditableField
                      label="Location"
                      value={profile.location || ''}
                      onChange={(e) => setProfile((p) => ({ ...p, location: e.target.value }))}
                    />
                  </div>
                )}
              </div>

              {/* Skills */}
              <div className="flex flex-col gap-3">
                <SectionHeader
                  icon={<BrainIcon />}
                  title="Skills"
                  isExpanded={expanded.skills}
                  onToggle={() => toggle('skills')}
                />
                {expanded.skills && (
                  <div className="flex flex-wrap gap-2 items-center">
                    {skills.map((sk, i) => (
                      <SkillChip
                        key={i}
                        label={sk.surface || sk.normalized_guess}
                        onRemove={() => removeSkill(i)}
                      />
                    ))}

                    {showAddInput ? (
                      <div className="flex items-center gap-2">
                        <input
                          autoFocus
                          type="text"
                          value={newSkill}
                          onChange={(e) => setNewSkill(e.target.value)}
                          onKeyDown={(e) => { if (e.key === 'Enter') addSkill(); if (e.key === 'Escape') setShowAddInput(false); }}
                          placeholder="e.g. Python"
                          className="px-3 py-1.5 border border-[#C5C6CD] rounded-full text-sm focus:outline-none focus:border-[#2563EB] w-32 transition-all"
                        />
                        <button
                          type="button"
                          onClick={addSkill}
                          className="text-xs text-[#2563EB] font-medium hover:underline"
                        >
                          Add
                        </button>
                        <button
                          type="button"
                          onClick={() => setShowAddInput(false)}
                          className="text-xs text-[#75777D] hover:underline"
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <button
                        type="button"
                        onClick={() => setShowAddInput(true)}
                        className="flex items-center gap-1.5 px-3 py-2 border border-dashed border-[#C5C6CD] rounded-full text-sm text-[#45474C] hover:border-[#2563EB] hover:text-[#2563EB] transition-colors"
                      >
                        <PlusIcon /> Add Skill
                      </button>
                    )}

                    {skills.length === 0 && !showAddInput && (
                      <p className="text-sm text-[#75777D]">No skills extracted yet.</p>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Card Footer — Analyze Button */}
            <div className="px-6 py-5 mt-auto border-t border-black/[0.05] bg-gradient-to-t from-white via-white to-transparent flex justify-end">
              <button
                type="button"
                onClick={handleAnalyze}
                disabled={!allDone || submitting || !!error}
                className="flex items-center justify-center gap-2 px-5 h-10 bg-[#2563EB] text-white text-base font-semibold rounded-lg hover:bg-[#1D4ED8] disabled:opacity-50 disabled:cursor-not-allowed transition-all active:scale-[0.99]"
              >
                {submitting ? (
                  <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                ) : null}
                Analyze
              </button>
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default AnalyzingPage;

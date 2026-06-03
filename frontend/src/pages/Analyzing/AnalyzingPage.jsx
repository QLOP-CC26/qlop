import { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { FileText, Download, Check, ChevronUp, ChevronDown, User, Briefcase, GraduationCap, Brain, Plus, X, Trash2 } from 'lucide-react';
import AppNavbar from '../../components/AppNavbar/AppNavbar';
import Footer from '../../components/Footer/Footer';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/* ── Step Indicator ── */
const StepItem = ({ status, title, subtitle, showLine }) => {
  const isDone = status === 'done';
  const isActive = status === 'active';
  return (
    <div className="flex items-start gap-4 relative">
      <div className="flex flex-col items-center flex-shrink-0">
        {isDone ? (
          <div className="w-6 h-6 rounded-full bg-[#2563EB] flex items-center justify-center">
            <Check className="w-3.5 h-3.5 text-white" />
          </div>
        ) : isActive ? (
          <div className="w-6 h-6 rounded-full border-2 border-[#2563EB] flex items-center justify-center">
            <div className="w-2 h-2 rounded-full bg-[#2563EB] animate-pulse" />
          </div>
        ) : (
          <div className="w-6 h-6 rounded-full border-2 border-[#C5C6CD]" />
        )}
        {showLine && <div className={`w-0.5 h-6 mt-1 ${isDone ? 'bg-[#2563EB]/20' : 'bg-[#C5C6CD]/30'}`} />}
      </div>
      <div className="pb-1">
        <p className={`text-base font-medium leading-6 ${isActive || isDone ? 'text-[#0D1C2D]' : 'text-[#75777D]'}`}>{title}</p>
        <p className={`text-sm leading-5 ${isActive ? 'text-[#2563EB]' : isDone ? 'text-[#75777D]' : 'text-[#C5C6CD]'}`}>{subtitle}</p>
      </div>
    </div>
  );
};

/* ── Editable Field ── */
const EditableField = ({ label, value, onChange, type = 'text' }) => (
  <div className="flex flex-col gap-1.5 w-full">
    <label className="text-xs font-semibold text-[#75777D] uppercase tracking-wide">{label}</label>
    <input
      type={type}
      value={value ?? ''}
      onChange={onChange}
      className="w-full px-3 py-2.5 border border-[#C5C6CD] rounded-lg text-sm text-[#0F172A] focus:outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-blue-100 transition-all"
    />
  </div>
);

/* ── Section Header ── */
const SectionHeader = ({ icon, title, count, isExpanded, onToggle }) => (
  <button
    type="button"
    onClick={onToggle}
    className="flex items-center justify-between w-full pb-2 border-b border-black/[0.08] group"
  >
    <div className="flex items-center gap-2">
      <span className="text-[#0D1C2D]">{icon}</span>
      <span className="text-lg font-semibold text-[#0D1C2D]">{title}</span>
      {count != null && (
        <span className="text-xs font-medium text-[#75777D] bg-[#F0F5FF] px-2.5 py-0.5 rounded-full">{count}</span>
      )}
    </div>
    <span className="text-[#75777D] group-hover:text-[#0D1C2D] transition-colors">
      {isExpanded ? <ChevronUp className="w-[18px] h-[18px]" /> : <ChevronDown className="w-[18px] h-[18px]" />}
    </span>
  </button>
);

/* ── Skill Chip ── */
const SkillChip = ({ label, onRemove }) => (
  <div className="flex items-center gap-1 px-3 py-1.5 bg-[#D4E4FA] border border-[#2563EB]/30 rounded-full">
    <span className="text-sm font-medium text-[#2563EB]">{label}</span>
    {onRemove && (
      <button type="button" onClick={onRemove} className="ml-1 text-[#2563EB] hover:text-blue-800 transition-colors flex items-center justify-center">
        <X className="w-3 h-3" />
      </button>
    )}
  </div>
);

/* ── Steps config (UX hint dari API_CONTRACT.md) ── */
const STEPS = [
  {
    title: 'Downloading document',
    active: 'Downloading document from Cloudinary…',
    done: 'Document downloaded.',
    pending: 'Waiting…',
  },
  {
    title: 'Reading PDF text',
    active: 'Reading text from PDF…',
    done: 'Text extracted successfully.',
    pending: 'Waiting for extraction…',
  },
  {
    title: 'AI extracting profile',
    active: 'AI model is extracting your CV information…',
    done: 'Profile extracted.',
    pending: 'Waiting for model…',
  },
  {
    title: 'Validating results',
    active: 'Almost done, validating extraction results…',
    done: 'Profile ready to review.',
    pending: 'Waiting…',
  },
];

/* ── Main Page ── */
const AnalyzingPage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const file = location.state?.file;

  const [stepStatuses, setStepStatuses] = useState(['active', 'pending', 'pending', 'pending']);
  const [analysisId, setAnalysisId] = useState(null);
  const [profile, setProfile] = useState({
    name: '', email: '', phone: '', location: '',
    total_experience_years: '',
    work_experience: [],
    education: [],
  });
  const [skills, setSkills] = useState([]);
  const [extractMeta, setExtractMeta] = useState(null); // page_count, extraction_mode, ner_model_version
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [expanded, setExpanded] = useState({ personal: true, work: true, education: true, skills: true });
  const [newSkill, setNewSkill] = useState('');
  const [showAddInput, setShowAddInput] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const didRun = useRef(false);
  const [extractSubStatus, setExtractSubStatus] = useState('AI model is extracting your CV information…');

  useEffect(() => {
    if (stepStatuses[2] !== 'active') return;

    const messages = [
      'AI model is extracting your CV information…',
      'Identifying educational background and degrees…',
      'Analyzing professional work experiences and timelines…',
      'Mapping technical and soft skill sets…',
      'Synthesizing data structures (almost ready)…'
    ];

    let idx = 0;
    const interval = setInterval(() => {
      idx = (idx + 1) % messages.length;
      setExtractSubStatus(messages[idx]);
    }, 3000);

    return () => clearInterval(interval);
  }, [stepStatuses[2]]);

  useEffect(() => {
    if (!file) { navigate('/analyze'); return; }
    if (didRun.current) return;
    didRun.current = true;
    runAnalysis();
  }, []);

  const runAnalysis = async () => {
    setError('');
    setIsLoading(true);
    setStepStatuses(['active', 'pending', 'pending', 'pending']);
    await sleep(700);
    setStepStatuses(['done', 'active', 'pending', 'pending']);
    await sleep(800);
    setStepStatuses(['done', 'done', 'active', 'pending']);

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
        setError(data.message || 'Failed to analyze CV.');
        setStepStatuses(['done', 'done', 'done', 'pending']);
        setIsLoading(false);
        return;
      }

      setStepStatuses(['done', 'done', 'done', 'active']);
      await sleep(600);
      setStepStatuses(['done', 'done', 'done', 'done']);

      setAnalysisId(data.data.id);

      const rawProfile = data.data.profile_entities || {};
      setProfile({
        name: rawProfile.name || '',
        email: rawProfile.email || rawProfile.email_address || '',
        phone: rawProfile.phone || '',
        location: rawProfile.location || '',
        total_experience_years: rawProfile.total_experience_years ?? '',
        work_experience: Array.isArray(rawProfile.work_experience) ? rawProfile.work_experience : [],
        education: Array.isArray(rawProfile.education) ? rawProfile.education : [],
      });

      const rawSkills = data.data.extracted_skills || rawProfile.skills || [];
      setSkills(rawSkills.map((s) => (typeof s === 'string' ? s : s.surface || '')).filter(Boolean));
      setExtractMeta(data.data.extract_metadata || null);
    } catch {
      setError('Unable to connect to the server.');
      setStepStatuses(['done', 'done', 'done', 'pending']);
    } finally {
      setIsLoading(false);
    }
  };

  /* ── Skills handlers ── */
  const removeSkill = (i) => setSkills((prev) => prev.filter((_, idx) => idx !== i));
  const addSkill = () => {
    const trimmed = newSkill.trim();
    if (!trimmed) return;
    setSkills((prev) => [...prev, trimmed]);
    setNewSkill('');
    setShowAddInput(false);
  };

  /* ── Work Experience handlers ── */
  const updateWorkExp = (i, field, val) =>
    setProfile((p) => {
      const we = [...(p.work_experience || [])];
      we[i] = { ...we[i], [field]: val };
      return { ...p, work_experience: we };
    });
  const addWorkExp = () =>
    setProfile((p) => ({
      ...p,
      work_experience: [...(p.work_experience || []), { company: '', designation: '', duration: '' }],
    }));
  const removeWorkExp = (i) =>
    setProfile((p) => ({ ...p, work_experience: p.work_experience.filter((_, idx) => idx !== i) }));

  /* ── Education handlers ── */
  const updateEdu = (i, field, val) =>
    setProfile((p) => {
      const ed = [...(p.education || [])];
      ed[i] = { ...ed[i], [field]: val };
      return { ...p, education: ed };
    });
  const addEdu = () =>
    setProfile((p) => ({
      ...p,
      education: [...(p.education || []), { degree: '', institution: '', year: '' }],
    }));
  const removeEdu = (i) =>
    setProfile((p) => ({ ...p, education: p.education.filter((_, idx) => idx !== i) }));

  const handleAnalyze = () => {
    if (!analysisId) return;
    setSubmitting(true);
    // Pass full profile (incl. work_experience, education) + flat skills ke RecommendPage
    const profileToPass = {
      ...profile,
      skills,
      total_experience_years: parseFloat(profile.total_experience_years) || 0,
    };
    navigate(`/recommend/${analysisId}`, { state: { skills, profile: profileToPass } });
  };

  const toggle = (key) => setExpanded((prev) => ({ ...prev, [key]: !prev[key] }));

  const allDone = stepStatuses.every((s) => s === 'done');
  const fileSize = file ? `${(file.size / 1024 / 1024).toFixed(1)} MB` : '';

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <AppNavbar activeTab="analyze" />

      <main className="flex-1 flex flex-col gap-8 px-8 py-8 pt-[104px] pb-[104px] max-w-[1280px] w-full mx-auto">
        {/* Page Header */}
        <div className="flex flex-col gap-1">
          <h1 className="text-[40px] font-bold leading-[48px] tracking-[-0.8px] text-black">
            Processing Document
          </h1>
          <p className="text-lg text-[#45474C]">
            Our AI is analyzing your CV to extract your complete profile.
          </p>
        </div>

        <div className="flex flex-col lg:flex-row gap-8 items-start w-full">
          {/* Left Column — Steps + File Info */}
          <div className="w-full lg:w-[400px] lg:flex-shrink-0 flex flex-col gap-6">

            {/* File card */}
            <div className="bg-white border border-black/[0.08] shadow-[0_1px_2px_rgba(0,0,0,0.05)] rounded-xl p-6 flex flex-col gap-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-[#EFF6FF] flex items-center justify-center text-[#2563EB]">
                  <FileText className="w-5 h-5" />
                </div>
                <div className="flex flex-col flex-1 min-w-0">
                  <p className="text-sm font-semibold text-[#0D1C2D] truncate">{file?.name}</p>
                  <p className="text-xs text-[#75777D]">{fileSize}</p>
                </div>
                {allDone && file && (
                  <a href={URL.createObjectURL(file)} download={file.name}
                    className="w-9 h-9 rounded-lg border border-black/[0.08] flex items-center justify-center text-[#45474C] hover:text-[#2563EB] hover:border-[#2563EB] transition-all">
                    <Download className="w-5 h-5" />
                  </a>
                )}
              </div>


            </div>

            {/* Steps card */}
            <div className="bg-white border border-black/[0.08] shadow-[0_1px_2px_rgba(0,0,0,0.05)] rounded-xl p-6 flex flex-col gap-3">
              {STEPS.map((step, i) => {
                const status = stepStatuses[i];
                let subtitle = status === 'done' ? step.done : status === 'active' ? step.active : step.pending;
                if (i === 2 && status === 'active') {
                  subtitle = extractSubStatus;
                }
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

            {error && (
              <div className="flex flex-col gap-3 w-full">
                <div className="w-full px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-600">
                  {error}
                </div>
                <button
                  type="button"
                  onClick={runAnalysis}
                  className="w-full h-10 bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-sm font-semibold rounded-xl transition-all flex items-center justify-center gap-2 active:scale-[0.99] shadow-[0_1px_2px_rgba(0,0,0,0.05)]"
                >
                  Retry Analysis
                </button>
              </div>
            )}
          </div>

          {/* Right Column — Extracted Profile (editable) */}
          <div className="flex-1 bg-white border border-black/[0.08] shadow-[0_1px_2px_rgba(0,0,0,0.05)] rounded-xl flex flex-col overflow-hidden">

            <div className="px-6 py-5 border-b border-black/[0.08] flex-shrink-0">
              <h2 className="text-2xl font-semibold text-black">Extracted Profile</h2>
              <p className="text-sm text-[#45474C] mt-1">
                Review and refine the AI-extracted data before proceeding to analysis.
              </p>
            </div>

            {!allDone ? (
              <div className="flex flex-col gap-8 p-6 animate-pulse">
                {/* Personal Info Skeleton */}
                <div className="flex flex-col gap-4">
                  <div className="flex items-center gap-3 border-b border-black/[0.08] pb-2">
                    <div className="w-5 h-5 bg-slate-200 rounded-full" />
                    <div className="w-36 h-5 bg-slate-200 rounded" />
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-slate-50 border border-black/[0.08] rounded-lg p-4">
                    <div className="flex flex-col gap-2">
                      <div className="w-16 h-3 bg-slate-200 rounded" />
                      <div className="w-full h-10 bg-slate-200 rounded" />
                    </div>
                    <div className="flex flex-col gap-2">
                      <div className="w-16 h-3 bg-slate-200 rounded" />
                      <div className="w-full h-10 bg-slate-200 rounded" />
                    </div>
                    <div className="flex flex-col gap-2">
                      <div className="w-16 h-3 bg-slate-200 rounded" />
                      <div className="w-full h-10 bg-slate-200 rounded" />
                    </div>
                    <div className="flex flex-col gap-2">
                      <div className="w-16 h-3 bg-slate-200 rounded" />
                      <div className="w-full h-10 bg-slate-200 rounded" />
                    </div>
                    <div className="flex flex-col gap-2 col-span-1 sm:col-span-2">
                      <div className="w-28 h-3 bg-slate-200 rounded" />
                      <div className="w-full h-10 bg-slate-200 rounded" />
                    </div>
                  </div>
                </div>

                {/* Work Experience Skeleton */}
                <div className="flex flex-col gap-4">
                  <div className="flex items-center gap-3 border-b border-black/[0.08] pb-2">
                    <div className="w-5 h-5 bg-slate-200 rounded" />
                    <div className="w-32 h-5 bg-slate-200 rounded" />
                  </div>
                  <div className="bg-slate-50 border border-black/[0.08] rounded-lg p-4 flex flex-col gap-3">
                    <div className="w-24 h-3 bg-slate-200 rounded" />
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      <div className="h-10 bg-slate-200 rounded" />
                      <div className="h-10 bg-slate-200 rounded" />
                      <div className="h-10 bg-slate-200 rounded" />
                    </div>
                  </div>
                </div>

                {/* Skills Skeleton */}
                <div className="flex flex-col gap-4">
                  <div className="flex items-center gap-3 border-b border-black/[0.08] pb-2">
                    <div className="w-5 h-5 bg-slate-200 rounded-full" />
                    <div className="w-16 h-5 bg-slate-200 rounded" />
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <div className="w-24 h-8 bg-slate-200 rounded-full" />
                    <div className="w-20 h-8 bg-slate-200 rounded-full" />
                    <div className="w-28 h-8 bg-slate-200 rounded-full" />
                    <div className="w-16 h-8 bg-slate-200 rounded-full" />
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex flex-col gap-7 p-6">
                {/* Personal Information */}
                <div className="flex flex-col gap-3">
                  <SectionHeader icon={<User className="w-5 h-5" />} title="Personal Information" isExpanded={expanded.personal} onToggle={() => toggle('personal')} />
                  {expanded.personal && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-slate-50 border border-black/[0.08] rounded-lg p-4">
                      <EditableField label="Full Name" value={profile.name}
                        onChange={(e) => setProfile((p) => ({ ...p, name: e.target.value }))} />
                      <EditableField label="Email" value={profile.email}
                        onChange={(e) => setProfile((p) => ({ ...p, email: e.target.value }))} />
                      <EditableField label="Phone" value={profile.phone}
                        onChange={(e) => setProfile((p) => ({ ...p, phone: e.target.value }))} />
                      <EditableField label="Location" value={profile.location}
                        onChange={(e) => setProfile((p) => ({ ...p, location: e.target.value }))} />
                      <EditableField label="Total Experience (years)" value={profile.total_experience_years} type="number"
                        onChange={(e) => setProfile((p) => ({ ...p, total_experience_years: e.target.value }))} />
                    </div>
                  )}
                </div>

                {/* Work Experience */}
                <div className="flex flex-col gap-3">
                  <SectionHeader icon={<Briefcase className="w-5 h-5" />} title="Work Experience"
                    count={profile.work_experience?.length || 0}
                    isExpanded={expanded.work} onToggle={() => toggle('work')} />
                  {expanded.work && (
                    <div className="flex flex-col gap-3">
                      {(profile.work_experience || []).map((we, i) => (
                        <div key={i} className="bg-slate-50 border border-black/[0.08] rounded-lg p-4 flex flex-col gap-3">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-[#75777D] uppercase tracking-widest">Experience #{i + 1}</span>
                            <button type="button" onClick={() => removeWorkExp(i)}
                              className="text-[#75777D] hover:text-red-500 transition-colors">
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                            <EditableField label="Company" value={we.company}
                              onChange={(e) => updateWorkExp(i, 'company', e.target.value)} />
                            <EditableField label="Job Title" value={we.designation}
                              onChange={(e) => updateWorkExp(i, 'designation', e.target.value)} />
                            <EditableField label="Duration" value={we.duration}
                              onChange={(e) => updateWorkExp(i, 'duration', e.target.value)} />
                          </div>
                        </div>
                      ))}
                      <button type="button" onClick={addWorkExp}
                        className="flex items-center gap-2 px-4 py-2.5 border border-dashed border-[#C5C6CD] rounded-lg text-sm text-[#45474C] hover:border-[#2563EB] hover:text-[#2563EB] transition-colors w-fit">
                        <Plus className="w-4 h-4" /> Add Work Experience
                      </button>
                    </div>
                  )}
                </div>

                {/* Education */}
                <div className="flex flex-col gap-3">
                  <SectionHeader icon={<GraduationCap className="w-5 h-5" />} title="Education"
                    count={profile.education?.length || 0}
                    isExpanded={expanded.education} onToggle={() => toggle('education')} />
                  {expanded.education && (
                    <div className="flex flex-col gap-3">
                      {(profile.education || []).map((ed, i) => (
                        <div key={i} className="bg-slate-50 border border-black/[0.08] rounded-lg p-4 flex flex-col gap-3">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-[#75777D] uppercase tracking-widest">Education #{i + 1}</span>
                            <button type="button" onClick={() => removeEdu(i)}
                              className="text-[#75777D] hover:text-red-500 transition-colors">
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                            <EditableField label="Degree" value={ed.degree}
                              onChange={(e) => updateEdu(i, 'degree', e.target.value)} />
                            <EditableField label="Institution" value={ed.institution}
                              onChange={(e) => updateEdu(i, 'institution', e.target.value)} />
                            <EditableField label="Year" value={ed.year}
                              onChange={(e) => updateEdu(i, 'year', e.target.value)} />
                          </div>
                        </div>
                      ))}
                      <button type="button" onClick={addEdu}
                        className="flex items-center gap-2 px-4 py-2.5 border border-dashed border-[#C5C6CD] rounded-lg text-sm text-[#45474C] hover:border-[#2563EB] hover:text-[#2563EB] transition-colors w-fit">
                        <Plus className="w-4 h-4" /> Add Education
                      </button>
                    </div>
                  )}
                </div>

                {/* Skills */}
                <div className="flex flex-col gap-3">
                  <SectionHeader icon={<Brain className="w-5 h-5" />} title="Skills"
                    count={skills.length}
                    isExpanded={expanded.skills} onToggle={() => toggle('skills')} />
                  {expanded.skills && (
                    <div className="flex flex-wrap gap-2 items-center">
                      {skills.map((sk, i) => (
                        <SkillChip key={i}
                          label={typeof sk === 'string' ? sk : sk.surface || ''}
                          onRemove={() => removeSkill(i)} />
                      ))}
                      {showAddInput ? (
                        <div className="flex items-center gap-2">
                          <input autoFocus type="text" value={newSkill}
                            onChange={(e) => setNewSkill(e.target.value)}
                            onKeyDown={(e) => { if (e.key === 'Enter') addSkill(); if (e.key === 'Escape') setShowAddInput(false); }}
                            placeholder="e.g. Python"
                            className="px-3 py-1.5 border border-[#C5C6CD] rounded-full text-sm focus:outline-none focus:border-[#2563EB] w-32 transition-all" />
                          <button type="button" onClick={addSkill} className="text-xs text-[#2563EB] font-medium hover:underline">Add</button>
                          <button type="button" onClick={() => setShowAddInput(false)} className="text-xs text-[#75777D] hover:underline">Cancel</button>
                        </div>
                      ) : (
                        <button type="button" onClick={() => setShowAddInput(true)}
                          className="flex items-center gap-1.5 px-3 py-1.5 border border-dashed border-[#C5C6CD] rounded-full text-sm text-[#45474C] hover:border-[#2563EB] hover:text-[#2563EB] transition-colors">
                          <Plus className="w-3.5 h-3.5" /> Add skill
                        </button>
                      )}
                    </div>
                  )}
                </div>

                {/* Submit button */}
                {allDone && !error && (
                  <button
                    type="button"
                    onClick={handleAnalyze}
                    disabled={submitting || !analysisId}
                    className="w-full h-12 bg-[#2563EB] text-white text-base font-semibold rounded-xl hover:bg-[#1D4ED8] disabled:opacity-50 disabled:cursor-not-allowed transition-all active:scale-[0.99] flex items-center justify-center gap-2 mt-2"
                  >
                    {submitting && <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />}
                    Continue to Skill Gap Analysis →
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default AnalyzingPage;

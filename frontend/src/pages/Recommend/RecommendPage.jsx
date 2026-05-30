import { useState, useEffect, useRef } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { User, Plus, X, Brain, ChevronDown, ChevronUp, Check } from 'lucide-react';
import AppNavbar from '../../components/AppNavbar/AppNavbar';
import Footer from '../../components/Footer/Footer';

const ChevronIcon = ({ open }) => (
  open ? <ChevronUp className="w-4 h-4 text-[#75777D]" /> : <ChevronDown className="w-4 h-4 text-[#75777D]" />
);

const ANALYZE_STEPS = [
  'Processing your CV profile…',
  'AI model is analyzing the skill gap for this role…',
  'Searching for relevant course recommendations…',
  'Calculating your readiness score…',
];

const normaliseSkillsList = (skills) =>
  (skills || []).map((s) => (typeof s === 'string' ? s : s.surface || s.normalized_guess || '')).filter(Boolean);

const RecommendPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();

  // State seeded from navigation state (fast path) or fetched from DB (deep-link)
  const [profile, setProfile] = useState(location.state?.profile || null);
  const [skills, setSkills] = useState(() => normaliseSkillsList(location.state?.skills));
  const [targetRole, setTargetRole] = useState('');
  const [newSkill, setNewSkill] = useState('');
  const [showAddInput, setShowAddInput] = useState(false);
  const [fetching, setFetching] = useState(!location.state);
  const [submitting, setSubmitting] = useState(false);
  const [submitStep, setSubmitStep] = useState(0); // animasi progress saat submit
  const [error, setError] = useState('');
  const [rolesList, setRolesList] = useState([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [roleFilter, setRoleFilter] = useState('');
  const [analyzeMeta, setAnalyzeMeta] = useState(null);
  const dropdownRef = useRef(null);

  // Fetch analysis details if arrived via deep-link
  useEffect(() => {
    if (!location.state) {
      fetchAnalysisDetails();
    }
    fetchRoles();
  }, [id]);

  const fetchAnalysisDetails = async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${import.meta.env.VITE_API_URL}/api/cv/history/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const json = await res.json();
      if (res.status === 401) {
        localStorage.removeItem('token');
        navigate('/login');
        return;
      }
      if (res.ok && json.data) {
        const dbProfile = json.data.profile_entities || {};
        setProfile(dbProfile);
        const rawSkills = json.data.extracted_skills || dbProfile.skills || [];
        setSkills(normaliseSkillsList(rawSkills));
      } else {
        setError(json.message || 'Failed to load CV analysis data.');
      }
    } catch {
      setError('Unable to connect to the server to load details.');
    } finally {
      setFetching(false);
    }
  };

  const fetchRoles = async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${import.meta.env.VITE_API_URL}/api/cv/roles`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const json = await res.json();
      if (res.ok && json.data?.roles) {
        setRolesList(json.data.roles);
      }
    } catch {
      // roles list is optional, not blocking
    }
  };

  const removeSkill = (index) => setSkills((prev) => prev.filter((_, i) => i !== index));

  const addSkill = () => {
    const trimmed = newSkill.trim();
    if (!trimmed) return;
    setSkills((prev) => [...prev, trimmed]);
    setNewSkill('');
    setShowAddInput(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!targetRole.trim()) {
      setError('Target role must be selected from the list.');
      return;
    }
    setError('');
    setSubmitting(true);
    setSubmitStep(0);

    // Animasi progress steps
    const stepTimer = setInterval(() => {
      setSubmitStep((prev) => {
        if (prev < ANALYZE_STEPS.length - 1) return prev + 1;
        clearInterval(stepTimer);
        return prev;
      });
    }, 3000);

    try {
      const token = localStorage.getItem('token');
      const updatedProfile = { ...(profile || {}), skills };

      const res = await fetch(`${import.meta.env.VITE_API_URL}/api/cv/recommend/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ target_role: targetRole.trim(), profile: updatedProfile }),
      });

      const json = await res.json();
      clearInterval(stepTimer);

      if (res.status === 401) { localStorage.removeItem('token'); navigate('/login'); return; }
      if (!res.ok) { setError(json.message || 'Failed to analyze skill gap.'); setSubmitting(false); return; }

      setAnalyzeMeta(json.data?.analyze_metadata || null);

      navigate(`/history/${id}`, { state: { analysisResult: json.data, profile } });
    } catch {
      setError('Unable to connect to the server.');
      setSubmitting(false);
    }
  };

  const filteredRoles = rolesList.filter((r) =>
    r.toLowerCase().includes(roleFilter.toLowerCase())
  );

  if (fetching) {
    return (
      <div className="min-h-screen flex flex-col bg-[#F8F9FF]">
        <AppNavbar activeTab="analyze" />
        <main className="flex-1 flex flex-col items-center justify-center p-8">
          <div className="w-12 h-12 border-4 border-[#2563EB]/25 border-t-[#2563EB] rounded-full animate-spin" />
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-[#F8F9FF]">
      <AppNavbar activeTab="analyze" />

      <main className="flex-1 flex flex-col gap-8 px-8 py-8 pt-[104px] pb-[104px] max-w-[1280px] w-full mx-auto">
        <div className="flex flex-col gap-1">
          <h1 className="text-[40px] font-bold leading-[48px] tracking-[-0.8px] text-black">
            Define Target Career
          </h1>
          <p className="text-lg text-[#45474C]">
            Select your desired role to match your current profile skills against digital industry standards.
          </p>
        </div>

        <div className="flex flex-col lg:flex-row gap-8 items-start w-full">
          {/* Right – Profile Summary */}
          <div className="w-full lg:w-[360px] lg:flex-shrink-0 flex flex-col gap-6">
            <form onSubmit={handleSubmit} className="bg-white border border-black/[0.08] shadow-[0_1px_2px_rgba(0,0,0,0.05)] rounded-xl p-6 flex flex-col gap-6">
              <div className="flex flex-col gap-2 relative">
                <label className="text-sm font-semibold text-[#45474C]">Target Career Role</label>

                {/* Select-only dropdown — API_CONTRACT: do NOT allow free-text input */}
                <div className="relative" ref={dropdownRef}>
                  <button
                    type="button"
                    onClick={() => setShowDropdown((v) => !v)}
                    className="w-full px-4 py-3 h-[48px] border border-[#C5C6CD] rounded-lg text-base text-left flex items-center justify-between focus:outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-blue-100 transition-all"
                  >
                    <span className={targetRole ? 'text-[#0F172A]' : 'text-[#C5C6CD]'}>
                      {targetRole || 'Choose target role…'}
                    </span>
                    <ChevronIcon open={showDropdown} />
                  </button>

                  {showDropdown && (
                    <div className="absolute z-20 top-full left-0 right-0 mt-1 bg-white border border-[#C5C6CD] rounded-lg shadow-lg">
                      <div className="p-2 border-b border-black/[0.05]">
                        <input
                          autoFocus
                          type="text"
                          value={roleFilter}
                          onChange={(e) => setRoleFilter(e.target.value)}
                          placeholder="Search roles…"
                          className="w-full px-3 py-2 text-sm border border-[#C5C6CD] rounded-md focus:outline-none focus:border-[#2563EB]"
                        />
                      </div>
                      <div className="max-h-48 overflow-y-auto">
                        {filteredRoles.length > 0 ? filteredRoles.map((role) => (
                          <button
                            key={role}
                            type="button"
                            onClick={() => { setTargetRole(role); setRoleFilter(''); setShowDropdown(false); }}
                            className={`w-full text-left px-4 py-2.5 text-sm transition-colors ${
                              targetRole === role ? 'bg-[#EFF6FF] text-[#2563EB] font-semibold' : 'text-[#0D1C2D] hover:bg-[#F0F5FF]'
                            }`}
                          >
                            {role}
                          </button>
                        )) : (
                          <p className="px-4 py-3 text-sm text-[#75777D]">No matching roles found.</p>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {rolesList.length > 0 && (
                  <p className="text-xs text-[#75777D]">{rolesList.length} roles available — choose from the list</p>
                )}
              </div>

              {/* Progress steps saat submit */}
              {submitting && (
                <div className="flex flex-col gap-3.5 p-4.5 bg-white border border-black/[0.06] rounded-xl shadow-[0_2px_8px_rgba(0,0,0,0.03)]">
                  {ANALYZE_STEPS.map((msg, i) => {
                    const isDone = i < submitStep;
                    const isActive = i === submitStep;
                    return (
                      <div key={i} className="flex items-start gap-3.5 relative">
                        <div className="flex flex-col items-center flex-shrink-0 mt-0.5">
                          {isDone ? (
                            <div className="w-5 h-5 rounded-full bg-[#2563EB] flex items-center justify-center">
                              <Check className="w-3 h-3 text-white" />
                            </div>
                          ) : isActive ? (
                            <div className="w-5 h-5 rounded-full border-2 border-[#2563EB] flex items-center justify-center">
                              <div className="w-1.5 h-1.5 rounded-full bg-[#2563EB] animate-pulse" />
                            </div>
                          ) : (
                            <div className="w-5 h-5 rounded-full border-2 border-[#C5C6CD]" />
                          )}
                        </div>
                        <div>
                          <p className={`text-sm leading-5 font-medium ${isActive ? 'text-[#2563EB]' : isDone ? 'text-[#0D1C2D]' : 'text-[#75777D]'}`}>
                            {msg}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {error && (
                <div className="px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">{error}</div>
              )}

              <button
                type="submit"
                disabled={submitting || !targetRole}
                className="w-full h-11 bg-[#2563EB] text-white text-base font-semibold rounded-lg hover:bg-[#1D4ED8] disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 ease-out hover:scale-[1.02] active:scale-[0.97] shadow-[0_2px_4px_rgba(37,99,235,0.15)] hover:shadow-[0_4px_12px_rgba(37,99,235,0.25)] disabled:transform-none disabled:shadow-none flex items-center justify-center gap-2"
              >
                {submitting && <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />}
                {submitting ? ANALYZE_STEPS[submitStep] : 'Analyze Skill Gap'}
              </button>
            </form>

            {/* Profile summary card */}
            {profile && (profile.name || profile.email || profile.email_address) && (
              <div className="bg-white border border-black/[0.08] shadow-[0_1px_2px_rgba(0,0,0,0.05)] rounded-xl p-6 flex flex-col gap-4">
                <div className="flex items-center gap-2 border-b border-black/[0.05] pb-3">
                  <User className="w-5 h-5 text-[#45474C]" />
                  <span className="text-base font-bold text-[#0D1C2D]">Extracted Profile</span>
                </div>
                <div className="flex flex-col gap-3 text-sm">
                  {profile.name && (
                    <div>
                      <span className="text-[#75777D] font-medium block">Name</span>
                      <span className="text-[#0D1C2D] font-semibold break-words">{profile.name}</span>
                    </div>
                  )}
                  {(profile.email || profile.email_address) && (
                    <div>
                      <span className="text-[#75777D] font-medium block">Email</span>
                      <span className="text-[#0D1C2D] font-semibold break-all">{profile.email || profile.email_address}</span>
                    </div>
                  )}
                  {profile.phone && (
                    <div>
                      <span className="text-[#75777D] font-medium block">Phone</span>
                      <span className="text-[#0D1C2D] font-semibold break-words">{profile.phone}</span>
                    </div>
                  )}
                  {profile.location && (
                    <div>
                      <span className="text-[#75777D] font-medium block">Location</span>
                      <span className="text-[#0D1C2D] font-semibold break-words">{profile.location}</span>
                    </div>
                  )}
                  {profile.total_experience_years > 0 && (
                    <div>
                      <span className="text-[#75777D] font-medium block">Experience</span>
                      <span className="text-[#0D1C2D] font-semibold">{profile.total_experience_years} years</span>
                    </div>
                  )}
                </div>

                {/* Work Experience */}
                {profile.work_experience?.length > 0 && (
                  <div className="border-t border-black/[0.05] pt-3">
                    <p className="text-xs font-semibold text-[#75777D] uppercase tracking-wide mb-2">Work Experience</p>
                    <div className="flex flex-col gap-2">
                      {profile.work_experience.map((we, i) => (
                        <div key={i} className="text-sm">
                          <span className="font-semibold text-[#0D1C2D]">{we.designation || 'Position'}</span>
                          {we.company && <span className="text-[#75777D]"> at {we.company}</span>}
                          {we.duration && <span className="text-[#75777D]"> · {we.duration}</span>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Education */}
                {profile.education?.length > 0 && (
                  <div className="border-t border-black/[0.05] pt-3">
                    <p className="text-xs font-semibold text-[#75777D] uppercase tracking-wide mb-2">Education</p>
                    <div className="flex flex-col gap-2">
                      {profile.education.map((ed, i) => (
                        <div key={i} className="text-sm">
                          <span className="font-semibold text-[#0D1C2D]">{ed.degree || 'Degree/Study'}</span>
                          {ed.institution && <span className="text-[#75777D]"> · {ed.institution}</span>}
                          {ed.year && <span className="text-[#75777D]"> ({ed.year})</span>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Right – Editable Skills Panel */}
          <div className="w-full lg:flex-1 bg-white border border-black/[0.08] shadow-[0_1px_2px_rgba(0,0,0,0.05)] rounded-xl p-6 flex flex-col gap-4">
            <div className="flex items-center gap-2 border-b border-black/[0.05] pb-3">
              <Brain className="w-5 h-5 text-[#45474C]" />
              <span className="text-base font-bold text-[#0D1C2D]">Profile Skills</span>
              <span className="ml-auto text-xs text-[#75777D] font-medium">{skills.length} skills</span>
            </div>
            <p className="text-sm text-[#75777D]">
              These skills will be matched against the target role. Refine as needed.
            </p>

            <div className="flex flex-wrap gap-2 pt-2">
              {skills.map((sk, i) => (
                <div key={i} className="flex items-center gap-1 px-3 py-1.5 bg-[#EFF6FF] border border-[#2563EB]/20 rounded-full">
                  <span className="text-sm font-medium text-[#2563EB]">{sk}</span>
                  <button
                    type="button"
                    onClick={() => removeSkill(i)}
                    className="ml-1 text-[#2563EB] hover:text-[#1D4ED8] transition-colors"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}

              {showAddInput ? (
                <div className="flex items-center gap-2">
                  <input
                    autoFocus
                    type="text"
                    value={newSkill}
                    onChange={(e) => setNewSkill(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') { e.preventDefault(); addSkill(); }
                      if (e.key === 'Escape') setShowAddInput(false);
                    }}
                    placeholder="e.g. Python"
                    className="px-3 py-1.5 border border-[#C5C6CD] rounded-full text-sm focus:outline-none focus:border-[#2563EB] w-32 transition-all placeholder:text-[#C5C6CD]"
                  />
                  <button
                    type="button"
                    onClick={addSkill}
                    className="text-xs text-[#2563EB] font-bold hover:underline"
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
                  className="flex items-center gap-1.5 px-3 py-1.5 border border-dashed border-[#C5C6CD] rounded-full text-sm text-[#45474C] hover:border-[#2563EB] hover:text-[#2563EB] transition-colors"
                >
                  <Plus className="w-4 h-4" /> Add Skill
                </button>
              )}
            </div>

            {skills.length === 0 && !showAddInput && (
              <p className="text-sm text-[#75777D] italic">No skills found. Add some above.</p>
            )}
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default RecommendPage;
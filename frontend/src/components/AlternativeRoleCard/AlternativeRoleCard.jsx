import React from 'react';
import { Check, AlertTriangle } from 'lucide-react';
import SectionCard from '../SectionCard/SectionCard';
import { TransitionBadge } from '../Badges/Badges';

export const AlternativeRoleCard = ({ role }) => (
  <SectionCard className="flex flex-col gap-3">
    <div className="flex items-start justify-between gap-3">
      <div>
        <p className="text-base font-bold text-[#0D1C2D]">{role.role_name}</p>
        <p className="text-sm text-[#45474C] mt-1">{role.why_good_fit}</p>
      </div>
      <div className="flex flex-col items-end gap-1 flex-shrink-0">
        <span className="text-lg font-bold text-[#2563EB]">
          {Math.round(role.skill_overlap_pct ?? role.skill_readiness_pct ?? 0)}%
        </span>
        <TransitionBadge difficulty={role.transition_difficulty} />
      </div>
    </div>

    {role.transferable_skills && role.transferable_skills.length > 0 && (
      <div>
        <p className="text-xs font-semibold text-[#75777D] mb-1.5 uppercase tracking-wide">Transferable skills</p>
        <div className="flex flex-wrap gap-1.5">
          {(role.transferable_skills || []).slice(0, 6).map((sk, i) => (
            <span key={i} className="flex items-center gap-1 text-xs px-2 py-1 bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-full font-medium">
              <Check className="w-3 h-3" /> {typeof sk === 'string' ? sk : sk.skill}
            </span>
          ))}
        </div>
      </div>
    )}

    {role.gap_skills && role.gap_skills.length > 0 && (
      <div>
        <p className="text-xs font-semibold text-[#75777D] mb-1.5 uppercase tracking-wide">Skills to develop</p>
        <div className="flex flex-wrap gap-1.5">
          {(role.gap_skills || role.skills_to_develop || []).slice(0, 5).map((sk, i) => (
            <span key={i} className="flex items-center gap-1 text-xs px-2 py-1 bg-amber-50 border border-amber-200 text-amber-700 rounded-full font-medium">
              <AlertTriangle className="w-3 h-3" /> {sk}
            </span>
          ))}
        </div>
      </div>
    )}

    {role.first_step && (
      <p className="text-xs text-[#45474C] italic border-t border-black/[0.05] pt-2">
        <span className="font-semibold not-italic">First step: </span>{role.first_step}
      </p>
    )}

    <div className="flex items-center gap-3 text-xs text-[#75777D] border-t border-black/[0.05] pt-2">
      {role.estimated_transition_time && (
        <span>⏱ {role.estimated_transition_time}</span>
      )}
      {role.estimated_transition_months && (
        <span>⏱ ~{role.estimated_transition_months} months</span>
      )}
      {role.market_demand && (
        <span className={`font-semibold ${role.market_demand === 'high' ? 'text-emerald-600' : role.market_demand === 'medium' ? 'text-amber-600' : 'text-red-500'}`}>
          {role.market_demand} demand
        </span>
      )}
    </div>
  </SectionCard>
);

export default AlternativeRoleCard;

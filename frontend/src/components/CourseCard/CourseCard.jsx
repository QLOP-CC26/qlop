import React from 'react';
import { ExternalLink, Clock } from 'lucide-react';
import { DifficultyBadge } from '../Badges/Badges';

const FORMAT_DURATION = {
  LESS_THAN_TWO_HOURS: '< 2 hours',
  ONE_TO_FOUR_WEEKS: '1–4 weeks',
  ONE_TO_THREE_MONTHS: '1–3 months',
  THREE_TO_SIX_MONTHS: '3–6 months',
  SIX_TO_TWELVE_MONTHS: '6–12 months',
};

const fmtDuration = (d) => FORMAT_DURATION[d] || d;

export const CourseCard = ({ course }) => (
  <a
    href={course.url || '#'}
    target="_blank"
    rel="noopener noreferrer"
    className="flex flex-col gap-3 p-5 bg-white border border-black/[0.06] rounded-xl hover:border-[#2563EB]/30 hover:shadow-[0_4px_20px_rgba(37,99,235,0.08)] transition-all duration-200 group"
  >
    <div className="flex items-start justify-between gap-2">
      <p className="text-sm font-semibold text-[#0D1C2D] group-hover:text-[#2563EB] transition-colors leading-snug flex-1">
        {course.name}
      </p>
      <ExternalLink className="w-3.5 h-3.5 text-[#C5C6CD] group-hover:text-[#2563EB] transition-colors flex-shrink-0 mt-0.5" />
    </div>

    <div className="flex items-center gap-2 flex-wrap">
      {course.difficulty && <DifficultyBadge level={course.difficulty} />}
      {course.duration && (
        <span className="flex items-center gap-1 text-xs text-[#75777D]">
          <Clock className="w-3 h-3" />
          {fmtDuration(course.duration)}
        </span>
      )}
      {course.match_score != null && (
        <span className="ml-auto text-xs font-bold text-[#2563EB]">
          {Math.round(course.match_score * 100)}% match
        </span>
      )}
    </div>

    {course.covered_skills?.length > 0 && (
      <div className="flex flex-wrap gap-1.5">
        {course.covered_skills.slice(0, 4).map((sk, i) => (
          <span key={i} className="text-xs px-2 py-0.5 bg-[#F0F5FF] border border-[#2563EB]/15 rounded-full text-[#45474C]">
            {sk}
          </span>
        ))}
        {course.covered_skills.length > 4 && (
          <span className="text-xs text-[#75777D]">+{course.covered_skills.length - 4} more</span>
        )}
      </div>
    )}
  </a>
);

export default CourseCard;

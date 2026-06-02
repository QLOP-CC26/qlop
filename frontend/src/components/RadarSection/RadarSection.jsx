import React, { useState } from 'react';
import SectionCard from '../SectionCard/SectionCard';
import { PivotRadarChart, RADAR_COLORS } from '../PivotRadarChart/PivotRadarChart';

const RADAR_COLS = [
  { label: 'Skill Match',   fn: r => Math.min(100, r.skill_overlap_pct ?? r.skill_readiness_pct ?? 0) },
  { label: 'Market Demand', fn: r => ({ high: 100, medium: 65, low: 30 })[(r.market_demand||'').toLowerCase()] ?? 50 },
  { label: 'Ease',          fn: r => ({ easy: 100, moderate: 60, challenging: 25 })[(r.transition_difficulty||'').toLowerCase()] ?? 50 },
  { label: 'Speed',         fn: r => Math.round(Math.max(10, (1 - ((r.estimated_transition_months??12) - 1) / 24) * 100)) },
  { label: 'Overall Fit',   fn: r => { const v=[Math.min(100,r.skill_overlap_pct??r.skill_readiness_pct??0),({ high:100,medium:65,low:30 })[(r.market_demand||'').toLowerCase()]??50,({ easy:100,moderate:60,challenging:25 })[(r.transition_difficulty||'').toLowerCase()]??50,Math.round(Math.max(10,(1-((r.estimated_transition_months??12)-1)/24)*100))]; return Math.round(v.reduce((a,b)=>a+b,0)/v.length); }},
];

const cellCls = (v) => v >= 75 ? 'text-emerald-600 bg-emerald-50' : v >= 50 ? 'text-amber-600 bg-amber-50' : 'text-red-500 bg-red-50';

export const RadarSection = ({ alternativeRoles, aiDiscoveredRoles }) => {
  const allRoles = [...alternativeRoles, ...aiDiscoveredRoles];
  const colorOf = (roleName) => {
    const idx = allRoles.findIndex(r => r.role_name === roleName);
    return RADAR_COLORS[idx % RADAR_COLORS.length];
  };

  const [selected, setSelected] = useState(() => new Set(allRoles.map(r => r.role_name)));

  const toggle = (name) => {
    setSelected(prev => {
      if (prev.has(name) && prev.size === 1) return prev; 
      const next = new Set(prev);
      next.has(name) ? next.delete(name) : next.add(name);
      return next;
    });
  };

  const visibleRoles = allRoles.filter(r => selected.has(r.role_name));

  return (
    <SectionCard>
      <p className="text-xs font-semibold text-[#75777D] uppercase tracking-widest mb-4">Role Comparison Radar</p>

      <div className="flex flex-wrap gap-2 mb-5">
        {allRoles.map((role) => {
          const c      = colorOf(role.role_name);
          const active = selected.has(role.role_name);
          return (
            <button
              key={role.role_name}
              onClick={() => toggle(role.role_name)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-xs font-semibold transition-all duration-150
                ${active
                  ? 'border-current shadow-sm scale-100'
                  : 'border-black/[0.08] text-[#C5C6CD] bg-slate-50 scale-95 opacity-60'
                }`}
              style={active ? { color: c.stroke, borderColor: c.stroke, backgroundColor: c.fill } : {}}
            >
              <span className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                style={{ backgroundColor: active ? c.stroke : '#C5C6CD' }} />
              {role.role_name}
            </button>
          );
        })}
      </div>

      <PivotRadarChart roles={visibleRoles} />

      <div className="mt-5 pt-4 border-t border-black/[0.05] overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr>
              <th className="text-left text-xs font-bold text-[#75777D] uppercase tracking-wide pb-2 pr-4">Role</th>
              {RADAR_COLS.map(c => (
                <th key={c.label} className="text-center text-xs font-bold text-[#75777D] uppercase tracking-wide pb-2 px-2 whitespace-nowrap">{c.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {allRoles.map((role) => {
              const c      = colorOf(role.role_name);
              const active = selected.has(role.role_name);
              return (
                <tr
                  key={role.role_name}
                  className={`border-t border-black/[0.04] cursor-pointer transition-opacity ${active ? 'opacity-100' : 'opacity-40'}`}
                  onClick={() => toggle(role.role_name)}
                >
                  <td className="py-2 pr-4">
                    <div className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: c.stroke }} />
                      <span className="font-medium text-[#0D1C2D] truncate max-w-[140px]">{role.role_name}</span>
                    </div>
                  </td>
                  {RADAR_COLS.map(col => {
                    const val = Math.round(col.fn(role));
                    return (
                      <td key={col.label} className="text-center py-2 px-2">
                        <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${cellCls(val)}`}>{val}%</span>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
        <p className="text-[10px] text-[#C5C6CD] mt-2 text-right">Click role to toggle visibility</p>
      </div>
    </SectionCard>
  );
};

export default RadarSection;

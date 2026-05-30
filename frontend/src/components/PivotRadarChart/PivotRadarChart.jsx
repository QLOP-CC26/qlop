import React, { useMemo } from 'react';
import { Radar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend);

export const RADAR_COLORS = [
  { stroke: '#2563EB', fill: 'rgba(37,99,235,0.13)'   },
  { stroke: '#6366F1', fill: 'rgba(99,102,241,0.13)'  },
  { stroke: '#10B981', fill: 'rgba(16,185,129,0.13)'  },
  { stroke: '#F59E0B', fill: 'rgba(245,158,11,0.13)'  },
  { stroke: '#EF4444', fill: 'rgba(239,68,68,0.13)'   },
  { stroke: '#8B5CF6', fill: 'rgba(139,92,246,0.13)'  },
  { stroke: '#EC4899', fill: 'rgba(236,72,153,0.13)'  },
  { stroke: '#14B8A6', fill: 'rgba(20,184,166,0.13)'  },
  { stroke: '#F97316', fill: 'rgba(249,115,22,0.13)'  },
  { stroke: '#64748B', fill: 'rgba(100,116,139,0.13)' },
];

const _normalizeRole = (role) => {
  const skillMatch = Math.min(100, role.skill_overlap_pct ?? role.skill_readiness_pct ?? 0);
  const demandMap  = { high: 100, medium: 65, low: 30 };
  const demand     = demandMap[(role.market_demand || '').toLowerCase()] ?? 50;
  const easeMap    = { easy: 100, moderate: 60, challenging: 25 };
  const ease       = easeMap[(role.transition_difficulty || '').toLowerCase()] ?? 50;
  const months     = role.estimated_transition_months ?? 12;
  const speed      = Math.round(Math.max(10, (1 - (months - 1) / 24) * 100));
  const overall    = Math.round((skillMatch + demand + ease + speed) / 4);
  return [skillMatch, demand, ease, speed, overall];
};

export const PivotRadarChart = ({ roles }) => {
  const roleKey = roles.map(r => r.role_name).join(',');

  const chartData = useMemo(() => ({
    labels: ['Skill Match', 'Market Demand', 'Ease', 'Speed', 'Overall Fit'],
    datasets: roles.map((role, i) => {
      const c = RADAR_COLORS[i % RADAR_COLORS.length];
      return {
        label: role.role_name,
        data: _normalizeRole(role),
        borderColor: c.stroke,
        backgroundColor: c.fill,
        borderWidth: 2,
        pointBackgroundColor: c.stroke,
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
        pointRadius: 5,
        pointHoverRadius: 7,
        pointHoverBorderWidth: 2,
      };
    }),
  }), [roleKey]);

  const options = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: true,
    animation: false,          
    scales: {
      r: {
        min: 0,
        max: 100,
        ticks: {
          stepSize: 25,
          color: '#94A3B8',
          font: { size: 10, family: 'Inter, system-ui, sans-serif' },
          backdropColor: 'transparent',
          callback: (v) => `${v}%`,
        },
        grid: { color: '#E2E8F0' },
        angleLines: { color: '#CBD5E1' },
        pointLabels: {
          color: '#475569',
          font: { size: 11, weight: '600', family: 'Inter, system-ui, sans-serif' },
        },
      },
    },
    plugins: {
      legend: {
        position: 'bottom',
        labels: {
          boxWidth: 12,
          boxHeight: 12,
          borderRadius: 6,
          useBorderRadius: true,
          color: '#45474C',
          font: { size: 12, family: 'Inter, system-ui, sans-serif' },
          padding: 16,
        },
      },
      tooltip: {
        backgroundColor: '#fff',
        borderColor: 'rgba(0,0,0,0.08)',
        borderWidth: 1,
        titleColor: '#0D1C2D',
        bodyColor: '#45474C',
        titleFont: { size: 12, weight: '700', family: 'Inter, system-ui, sans-serif' },
        bodyFont: { size: 12, family: 'Inter, system-ui, sans-serif' },
        padding: 12,
        boxWidth: 10,
        boxHeight: 10,
        borderRadius: 10,
        callbacks: {
          label: (ctx) => `  ${ctx.dataset.label}: ${ctx.raw}%`,
        },
      },
    },
  }), []); 

  return (
    <div className="w-full flex justify-center" style={{ maxWidth: 480, margin: '0 auto' }}>
      <Radar data={chartData} options={options} />
    </div>
  );
};

export default PivotRadarChart;

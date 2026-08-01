/**
 * SkillRadar — Learner skill level radar / bar chart
 * ExcellStudy EdTech Platform
 *
 * Requires: React 18+ and ReactDOM loaded via CDN
 * <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
 * <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
 */

const { useState, useEffect, useRef, useCallback } = React;

/* ---- helpers ---- */
function getColorForLevel(level) {
  if (level <= 30) return '#E05252';
  if (level <= 60) return '#BA7517';
  if (level <= 80) return '#0A0A0A';
  return '#FFE000';
}

function getLabelForLevel(level) {
  if (level <= 30) return 'Beginner';
  if (level <= 60) return 'Intermediate';
  if (level <= 80) return 'Advanced';
  return 'Expert';
}

/* ---- styles (inline objects) ---- */
const S = {
  container: {
    fontFamily: "'Inter', sans-serif",
    background: '#FFFFFF',
    borderRadius: '12px',
    boxShadow: '0 2px 12px rgba(10, 10, 10,0.08)',
    padding: '24px',
    border: '1px solid #F0F0EE',
  },
  title: {
    fontSize: '18px', fontWeight: 700, color: '#0A0A0A', margin: 0,
  },
  subtitle: {
    fontSize: '13px', color: '#9CA3AF', marginTop: '4px', marginBottom: '20px',
  },
  row: {
    display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '14px',
  },
  skillName: {
    width: '130px', flexShrink: 0, fontSize: '13px', fontWeight: 500,
    color: '#0A0A0A', textAlign: 'right',
  },
  barTrack: {
    flex: 1, height: '12px', background: '#F0F0EE', borderRadius: '6px',
    overflow: 'hidden', position: 'relative',
  },
  pct: {
    width: '42px', textAlign: 'right', fontSize: '13px', fontWeight: 600,
  },
  badge: {
    fontSize: '11px', fontWeight: 600, padding: '2px 10px', borderRadius: '20px',
    whiteSpace: 'nowrap',
  },
  tooltip: {
    position: 'absolute', top: '-34px', padding: '4px 10px',
    background: '#0A0A0A', color: '#fff', borderRadius: '6px',
    fontSize: '11px', fontWeight: 600, whiteSpace: 'nowrap',
    transform: 'translateX(-50%)', pointerEvents: 'none', zIndex: 10,
  },
  summaryRow: {
    display: 'flex', justifyContent: 'space-between', gap: '12px',
    marginTop: '20px', paddingTop: '16px', borderTop: '1px solid #F0F0EE',
  },
  summaryCard: {
    flex: 1, textAlign: 'center', padding: '10px',
    background: '#FAFAF8', borderRadius: '8px',
  },
  summaryLabel: { fontSize: '11px', color: '#9CA3AF', marginBottom: '4px' },
  summaryValue: { fontSize: '16px', fontWeight: 700, color: '#0A0A0A' },
};

/* ---- component ---- */
function SkillRadar(props) {
  var skills = props.skills;
  var _useState = useState(false), animated = _useState[0], setAnimated = _useState[1];
  var _useHover = useState(null), hovered = _useHover[0], setHovered = _useHover[1];

  useEffect(function () {
    var t = setTimeout(function () { setAnimated(true); }, 80);
    return function () { clearTimeout(t); };
  }, []);

  var entries = Object.entries(skills || {});
  if (entries.length === 0) {
    return React.createElement('div', { style: S.container },
      React.createElement('p', { style: { color: '#9CA3AF', textAlign: 'center' } }, 'No skill data available.')
    );
  }

  var levels  = entries.map(function (e) { return e[1]; });
  var avg     = Math.round(levels.reduce(function (a, b) { return a + b; }, 0) / levels.length);
  var maxIdx  = levels.indexOf(Math.max.apply(null, levels));
  var minIdx  = levels.indexOf(Math.min.apply(null, levels));

  return React.createElement('div', { style: S.container },
    React.createElement('h3', { style: S.title }, 'Skill Proficiency'),
    React.createElement('p', { style: S.subtitle }, 'Your current skill levels across key areas'),

    /* skill rows */
    entries.map(function (entry, i) {
      var name  = entry[0];
      var level = entry[1];
      var color = getColorForLevel(level);
      var label = getLabelForLevel(level);
      var isHovered = hovered === i;

      return React.createElement('div', {
        key: name, style: S.row,
        onMouseEnter: function () { setHovered(i); },
        onMouseLeave: function () { setHovered(null); },
      },
        React.createElement('span', { style: S.skillName }, name),
        React.createElement('div', { style: S.barTrack },
          React.createElement('div', {
            style: {
              height: '100%', borderRadius: '6px', background: color,
              width: animated ? level + '%' : '0%',
              transition: 'width 0.8s cubic-bezier(.4,0,.2,1)',
              transitionDelay: (i * 0.1) + 's',
              position: 'relative',
            }
          },
            isHovered ? React.createElement('div', {
              style: Object.assign({}, S.tooltip, { left: '100%' })
            }, level + '% — ' + label) : null
          )
        ),
        React.createElement('span', { style: Object.assign({}, S.pct, { color: color }) }, level + '%'),
        React.createElement('span', {
          style: Object.assign({}, S.badge, {
            background: color + '1A', color: color,
          })
        }, label)
      );
    }),

    /* summary */
    React.createElement('div', { style: S.summaryRow },
      React.createElement('div', { style: S.summaryCard },
        React.createElement('div', { style: S.summaryLabel }, 'Average'),
        React.createElement('div', { style: Object.assign({}, S.summaryValue, { color: getColorForLevel(avg) }) }, avg + '%')
      ),
      React.createElement('div', { style: S.summaryCard },
        React.createElement('div', { style: S.summaryLabel }, 'Strongest'),
        React.createElement('div', { style: S.summaryValue }, entries[maxIdx][0])
      ),
      React.createElement('div', { style: S.summaryCard },
        React.createElement('div', { style: S.summaryLabel }, 'Needs Work'),
        React.createElement('div', { style: S.summaryValue }, entries[minIdx][0])
      )
    )
  );
}

/* ---- mount ---- */
var skillRadarRoot = document.getElementById('skill-radar-root');
if (skillRadarRoot) {
  var skills = JSON.parse(skillRadarRoot.dataset.skills || '{}');
  var root = ReactDOM.createRoot(skillRadarRoot);
  root.render(React.createElement(SkillRadar, { skills: skills }));
}

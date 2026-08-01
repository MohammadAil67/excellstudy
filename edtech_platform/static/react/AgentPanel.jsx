/**
 * AgentPanel — Live agent message stream component
 * ExcellStudy EdTech Platform
 *
 * WebSocket connection for real-time agent communication.
 * Loaded via React CDN, rendered into #agent-panel-root.
 *
 * Requires: React 18+ and ReactDOM loaded via CDN
 * <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
 * <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
 */

var useState    = React.useState;
var useEffect   = React.useEffect;
var useRef      = React.useRef;
var useCallback = React.useCallback;
var h           = React.createElement;

/* ---- colour palette ---- */
var C = {
  primary: '#0A0A0A', primaryLight: '#FFE000',
  accent: '#FFE000', accentLight: '#0A0A0A',
  highlight: '#BA7517', error: '#E05252', errorLight: '#F07070',
  bg: '#FAFAF8', card: '#FFFFFF', dark: '#0A0A0A',
  textPrimary: '#0A0A0A', textSecondary: '#6B7280', textMuted: '#9CA3AF',
  border: '#E5E5E2', borderLight: '#F0F0EE',
};

/* ---- TypingIndicator ---- */
function TypingIndicator() {
  return h('div', {
    style: {
      display: 'flex', alignItems: 'center', gap: '4px',
      padding: '8px 14px', alignSelf: 'flex-start',
    }
  },
    [0, 1, 2].map(function (i) {
      return h('span', {
        key: i,
        style: {
          width: '8px', height: '8px', borderRadius: '50%',
          background: C.primary, display: 'inline-block',
          animation: 'typing 1.2s infinite',
          animationDelay: (i * 0.15) + 's',
        }
      });
    })
  );
}

/* ---- AgentPanel ---- */
function AgentPanel(props) {
  var agentId   = props.agentId;
  var sessionId = props.sessionId;

  var _msgs      = useState([]);
  var messages    = _msgs[0];
  var setMessages = _msgs[1];

  var _conn      = useState(false);
  var isConnected = _conn[0];
  var setConnected = _conn[1];

  var _typing    = useState(false);
  var isTyping   = _typing[0];
  var setTyping  = _typing[1];

  var _input     = useState('');
  var inputText  = _input[0];
  var setInput   = _input[1];

  var wsRef      = useRef(null);
  var scrollRef  = useRef(null);
  var idRef      = useRef(0);

  function addMessage(type, content, sender) {
    setMessages(function (prev) {
      return prev.concat({
        id: ++idRef.current, type: type, content: content,
        timestamp: new Date(), sender: sender || type,
      });
    });
  }

  /* ---- WebSocket lifecycle ---- */
  useEffect(function () {
    var protocol = location.protocol === 'https:' ? 'wss' : 'ws';
    var url = protocol + '://' + location.host + '/ws/agent/' + agentId + '/session/' + sessionId + '/';
    var ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = function () {
      setConnected(true);
      addMessage('system', 'Connected to agent');
    };

    ws.onmessage = function (e) {
      try {
        var data = JSON.parse(e.data);
        switch (data.type) {
          case 'agent_message':
            setTyping(false);
            addMessage('agent', data.content, data.sender || 'Agent');
            break;
          case 'typing':
            setTyping(true);
            break;
          case 'tool_call':
            addMessage('tool_call', (data.tool || 'tool') + '(' + (data.args || '') + ')');
            break;
          case 'tool_result':
            addMessage('tool_result', data.content);
            break;
          case 'error':
            addMessage('error', data.content || 'An error occurred');
            break;
          default:
            addMessage('agent', data.content || JSON.stringify(data));
        }
      } catch (_) {
        addMessage('agent', e.data);
      }
    };

    ws.onclose = function () {
      setConnected(false);
      addMessage('system', 'Disconnected from agent');
    };

    ws.onerror = function () {
      addMessage('error', 'WebSocket connection error');
    };

    return function () { ws.close(); };
  }, [agentId, sessionId]);

  /* ---- auto-scroll ---- */
  useEffect(function () {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  /* ---- send handler ---- */
  function sendMessage() {
    if (!inputText.trim() || !wsRef.current || wsRef.current.readyState !== 1) return;
    wsRef.current.send(JSON.stringify({ type: 'user_message', content: inputText }));
    addMessage('user', inputText, 'You');
    setInput('');
  }

  function handleKeyPress(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  function formatTimestamp(d) {
    return ('0' + d.getHours()).slice(-2) + ':' + ('0' + d.getMinutes()).slice(-2);
  }

  /* ---- per-message renderer ---- */
  function renderMessage(msg) {
    var base = {
      maxWidth: '80%', padding: '10px 14px', borderRadius: '12px',
      fontSize: '13px', lineHeight: '1.5', wordBreak: 'break-word',
      position: 'relative',
    };

    var wrapper = { display: 'flex', marginBottom: '8px' };
    var time = { fontSize: '10px', color: C.textMuted, marginTop: '4px' };

    switch (msg.type) {
      case 'user':
        return h('div', { key: msg.id, style: Object.assign({}, wrapper, { justifyContent: 'flex-end' }) },
          h('div', null,
            h('div', { style: Object.assign({}, base, {
              background: C.primary, color: '#fff', borderBottomRightRadius: '4px',
            }) }, msg.content),
            h('div', { style: Object.assign({}, time, { textAlign: 'right' }) }, formatTimestamp(msg.timestamp))
          )
        );

      case 'agent':
        return h('div', { key: msg.id, style: wrapper },
          h('div', null,
            h('div', { style: Object.assign({}, base, {
              background: C.card, border: '1px solid ' + C.borderLight,
              color: C.textPrimary, borderBottomLeftRadius: '4px',
            }) }, msg.content),
            h('div', { style: time }, formatTimestamp(msg.timestamp))
          )
        );

      case 'system':
        return h('div', { key: msg.id, style: {
          textAlign: 'center', fontSize: '11px', color: C.textMuted,
          fontStyle: 'italic', margin: '12px 0',
        } }, msg.content);

      case 'error':
        return h('div', { key: msg.id, style: wrapper },
          h('div', { style: Object.assign({}, base, {
            background: '#FEF2F2', border: '1px solid #FECACA',
            color: C.error, borderBottomLeftRadius: '4px',
          }) }, '⚠ ' + msg.content)
        );

      case 'tool_call':
        return h('div', { key: msg.id, style: wrapper },
          h('div', { style: Object.assign({}, base, {
            background: C.dark, color: '#E0DEF4',
            fontFamily: "'JetBrains Mono', monospace", fontSize: '12px',
          }) },
            h('div', { style: { fontSize: '10px', color: C.textMuted, marginBottom: '4px' } }, '🔧 Tool Call'),
            msg.content
          )
        );

      case 'tool_result':
        return h('div', { key: msg.id, style: wrapper },
          h('div', { style: Object.assign({}, base, {
            background: 'rgba(186, 117, 23,0.08)', border: '1px solid rgba(186, 117, 23,0.2)',
            fontFamily: "'JetBrains Mono', monospace", fontSize: '12px', color: C.textPrimary,
          }) },
            h('div', { style: { fontSize: '10px', color: C.accent, marginBottom: '4px' } }, '✓ Tool Result'),
            msg.content
          )
        );

      default:
        return h('div', { key: msg.id, style: wrapper },
          h('div', { style: Object.assign({}, base, {
            background: C.borderLight, color: C.textSecondary,
          }) }, msg.content)
        );
    }
  }

  /* ---- main render ---- */
  return h('div', {
    style: {
      fontFamily: "'Inter', sans-serif",
      background: C.card, borderRadius: '12px',
      boxShadow: '0 2px 12px rgba(10, 10, 10,0.08)',
      border: '1px solid ' + C.borderLight,
      display: 'flex', flexDirection: 'column',
      height: '520px', overflow: 'hidden',
    }
  },
    /* header */
    h('div', {
      style: {
        padding: '14px 18px', borderBottom: '1px solid ' + C.borderLight,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }
    },
      h('div', { style: { display: 'flex', alignItems: 'center', gap: '10px' } },
        h('span', { style: { fontSize: '18px' } }, '🤖'),
        h('span', { style: { fontWeight: 600, fontSize: '14px', color: C.textPrimary } }, 'Agent Chat')
      ),
      h('div', { style: { display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px' } },
        h('span', {
          style: {
            width: '8px', height: '8px', borderRadius: '50%',
            background: isConnected ? C.accent : C.error,
            display: 'inline-block',
          }
        }),
        h('span', { style: { color: C.textMuted } }, isConnected ? 'Connected' : 'Disconnected')
      )
    ),

    /* messages */
    h('div', {
      ref: scrollRef,
      style: {
        flex: 1, overflowY: 'auto', padding: '16px',
        background: C.bg,
      }
    },
      messages.map(renderMessage),
      isTyping ? h(TypingIndicator) : null
    ),

    /* input area */
    h('div', {
      style: {
        padding: '12px 14px', borderTop: '1px solid ' + C.borderLight,
        display: 'flex', alignItems: 'center', gap: '8px',
      }
    },
      h('input', {
        type: 'text', value: inputText,
        placeholder: isConnected ? 'Type a message…' : 'Reconnecting…',
        disabled: !isConnected,
        onChange: function (e) { setInput(e.target.value); },
        onKeyDown: handleKeyPress,
        style: {
          flex: 1, padding: '10px 14px', border: '1.5px solid ' + C.border,
          borderRadius: '8px', fontSize: '13px',
          fontFamily: "'Inter', sans-serif",
          outline: 'none', background: C.card, color: C.textPrimary,
        }
      }),
      h('button', {
        onClick: sendMessage,
        disabled: !isConnected || !inputText.trim(),
        style: {
          padding: '10px 18px', borderRadius: '8px', border: 'none',
          background: (!isConnected || !inputText.trim()) ? C.borderLight : C.primary,
          color: (!isConnected || !inputText.trim()) ? C.textMuted : '#fff',
          fontWeight: 600, fontSize: '13px', cursor: 'pointer',
          fontFamily: "'Inter', sans-serif",
          transition: 'all 0.15s ease',
        }
      }, 'Send')
    )
  );
}

/* ---- mount ---- */
var agentPanelRoot = document.getElementById('agent-panel-root');
if (agentPanelRoot) {
  var root = ReactDOM.createRoot(agentPanelRoot);
  root.render(h(AgentPanel, {
    agentId:   agentPanelRoot.dataset.agentId,
    sessionId: agentPanelRoot.dataset.sessionId,
  }));
}

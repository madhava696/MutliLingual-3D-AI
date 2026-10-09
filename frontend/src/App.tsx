import { useState, useEffect, useCallback } from 'react';
import {
  Activity,
  CheckCircle2,
  Cpu,
  Database,
  Globe,
  KeyRound,
  Layers,
  RefreshCw,
  Server,
  ShieldCheck,
  Sparkles,
  Terminal,
} from 'lucide-react';

interface HealthData {
  status: string;
  version: string;
  name: string;
}

interface SessionData {
  session_id: string;
  session_token: string;
  language: string;
  private_mode: boolean;
  expires_at: string;
}

export default function App() {
  const [selectedLang, setSelectedLang] = useState<'te' | 'hi' | 'en'>('te');
  const [backendStatus, setBackendStatus] = useState<'checking' | 'connected' | 'disconnected'>('checking');
  const [healthData, setHealthData] = useState<HealthData | null>(null);
  const [pingMs, setPingMs] = useState<number | null>(null);
  const [session, setSession] = useState<SessionData | null>(null);
  const [sessionLoading, setSessionLoading] = useState(false);
  const [sessionError, setSessionError] = useState<string | null>(null);

  const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  const checkHealth = useCallback(async () => {
    setBackendStatus('checking');
    const start = performance.now();
    try {
      const res = await fetch(`${API_BASE}/api/v1/health`, { method: 'GET' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const elapsed = Math.round(performance.now() - start);
      setHealthData(data);
      setPingMs(elapsed);
      setBackendStatus('connected');
    } catch {
      setBackendStatus('disconnected');
      setHealthData(null);
      setPingMs(null);
    }
  }, [API_BASE]);

  const createSampleSession = async () => {
    setSessionLoading(true);
    setSessionError(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          language: selectedLang,
          private_mode: false,
        }),
      });
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const data = await res.json();
      setSession(data);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to connect to backend';
      setSessionError(message);
    } finally {
      setSessionLoading(false);
    }
  };

  useEffect(() => {
    let ignore = false;
    const fetchInitialHealth = async () => {
      const start = performance.now();
      try {
        const res = await fetch(`${API_BASE}/api/v1/health`, { method: 'GET' });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const elapsed = Math.round(performance.now() - start);
        if (!ignore) {
          setHealthData(data);
          setPingMs(elapsed);
          setBackendStatus('connected');
        }
      } catch {
        if (!ignore) {
          setBackendStatus('disconnected');
          setHealthData(null);
          setPingMs(null);
        }
      }
    };
    fetchInitialHealth();
    return () => {
      ignore = true;
    };
  }, [API_BASE]);

  return (
    <div style={{ maxWidth: 1240, margin: '0 auto', padding: '32px 24px' }}>
      {/* Top Header */}
      <header
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 40,
          paddingBottom: 20,
          borderBottom: '1px solid var(--border-subtle)',
          flexWrap: 'wrap',
          gap: 16,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div
            style={{
              width: 44,
              height: 44,
              borderRadius: 12,
              background: 'linear-gradient(135deg, #f97316 0%, #6366f1 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 20px rgba(99, 102, 241, 0.4)',
            }}
          >
            <Sparkles size={24} color="#ffffff" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.45rem', fontWeight: 700, margin: 0 }}>
              <span className="gradient-tricolor">India-first</span> 3D AI Companion
            </h1>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: 0 }}>
              hackFront India 2026 • Open Innovation Baseline
            </p>
          </div>
        </div>

        {/* Controls / Status Pill */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          {/* Language Selector */}
          <div
            style={{
              display: 'flex',
              background: 'rgba(255, 255, 255, 0.05)',
              padding: '4px',
              borderRadius: '10px',
              border: '1px solid var(--border-subtle)',
            }}
          >
            {(['te', 'hi', 'en'] as const).map((lang) => (
              <button
                key={lang}
                onClick={() => setSelectedLang(lang)}
                style={{
                  background: selectedLang === lang ? 'rgba(99, 102, 241, 0.35)' : 'transparent',
                  color: selectedLang === lang ? '#ffffff' : 'var(--text-muted)',
                  border: selectedLang === lang ? '1px solid rgba(99, 102, 241, 0.5)' : '1px solid transparent',
                  padding: '6px 14px',
                  borderRadius: 8,
                  fontSize: '0.82rem',
                  fontWeight: selectedLang === lang ? 600 : 400,
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                }}
              >
                {lang === 'te' ? 'తెలుగు' : lang === 'hi' ? 'हिन्दी' : 'English'}
              </button>
            ))}
          </div>

          {/* Backend Status Pill */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '6px 14px',
              borderRadius: 20,
              background:
                backendStatus === 'connected'
                  ? 'rgba(16, 185, 129, 0.12)'
                  : backendStatus === 'checking'
                  ? 'rgba(249, 115, 22, 0.12)'
                  : 'rgba(239, 68, 68, 0.12)',
              border: `1px solid ${
                backendStatus === 'connected'
                  ? 'rgba(16, 185, 129, 0.3)'
                  : backendStatus === 'checking'
                  ? 'rgba(249, 115, 22, 0.3)'
                  : 'rgba(239, 68, 68, 0.3)'
              }`,
              fontSize: '0.82rem',
              fontWeight: 500,
              color:
                backendStatus === 'connected'
                  ? '#34d399'
                  : backendStatus === 'checking'
                  ? '#fb923c'
                  : '#f87171',
            }}
          >
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                background:
                  backendStatus === 'connected'
                    ? '#10b981'
                    : backendStatus === 'checking'
                    ? '#f97316'
                    : '#ef4444',
                boxShadow:
                  backendStatus === 'connected'
                    ? '0 0 10px #10b981'
                    : backendStatus === 'checking'
                    ? '0 0 10px #f97316'
                    : '0 0 10px #ef4444',
              }}
            />
            {backendStatus === 'connected'
              ? `API Online (${pingMs}ms)`
              : backendStatus === 'checking'
              ? 'Checking API...'
              : 'API Offline (localhost:8000)'}
            <button
              onClick={checkHealth}
              title="Refresh connection"
              style={{
                background: 'none',
                border: 'none',
                color: 'inherit',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                padding: 0,
              }}
            >
              <RefreshCw size={13} />
            </button>
          </div>
        </div>
      </header>

      {/* Hero Banner */}
      <section
        className="glass-panel"
        style={{
          padding: '36px 32px',
          marginBottom: 32,
          position: 'relative',
          overflow: 'hidden',
          background: 'linear-gradient(135deg, rgba(20, 27, 45, 0.8) 0%, rgba(13, 18, 31, 0.9) 100%)',
        }}
      >
        <div
          style={{
            position: 'absolute',
            top: -60,
            right: -60,
            width: 200,
            height: 200,
            background: 'radial-gradient(circle, rgba(99, 102, 241, 0.25) 0%, transparent 70%)',
            borderRadius: '50%',
            filter: 'blur(30px)',
          }}
        />
        <div style={{ maxWidth: 780, position: 'relative', zIndex: 1 }}>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              padding: '4px 12px',
              borderRadius: 16,
              background: 'rgba(99, 102, 241, 0.15)',
              border: '1px solid rgba(99, 102, 241, 0.3)',
              color: '#818cf8',
              fontSize: '0.75rem',
              fontWeight: 600,
              marginBottom: 16,
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
            }}
          >
            <ShieldCheck size={14} /> Phase 0 Foundation Verified
          </div>
          <h2 style={{ fontSize: '2.1rem', fontWeight: 700, marginBottom: 12, lineHeight: 1.25 }}>
            Multilingual Voice & 3D Companion Backbone
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '1rem', lineHeight: 1.6, marginBottom: 24 }}>
            FastAPI async backend paired with Vite React 19 frontend, PostgreSQL async storage, and Redis ephemeral caching.
            Engineered with cryptographically isolated session tokens and intelligent cost-aware routing.
          </p>

          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '8px 14px',
                borderRadius: 8,
                background: 'rgba(255, 255, 255, 0.04)',
                border: '1px solid var(--border-subtle)',
                fontSize: '0.85rem',
              }}
            >
              <Cpu size={16} color="#6366f1" />
              <span>FastAPI 0.110 Async</span>
            </div>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '8px 14px',
                borderRadius: 8,
                background: 'rgba(255, 255, 255, 0.04)',
                border: '1px solid var(--border-subtle)',
                fontSize: '0.85rem',
              }}
            >
              <Database size={16} color="#10b981" />
              <span>PostgreSQL + Redis 7</span>
            </div>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '8px 14px',
                borderRadius: 8,
                background: 'rgba(255, 255, 255, 0.04)',
                border: '1px solid var(--border-subtle)',
                fontSize: '0.85rem',
              }}
            >
              <Globe size={16} color="#f97316" />
              <span>Telugu • Hindi • English</span>
            </div>
          </div>
        </div>
      </section>

      {/* Main Grid: Phase 0 Status & Architecture Verification */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 24, marginBottom: 32 }}>
        {/* Card 1: Live API Health & Metadata */}
        <div className="glass-panel" style={{ padding: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: 8,
                  background: 'rgba(16, 185, 129, 0.15)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Server size={20} color="#10b981" />
              </div>
              <h3 style={{ fontSize: '1.1rem', margin: 0 }}>API Health Check</h3>
            </div>
            <span
              style={{
                fontSize: '0.75rem',
                padding: '3px 8px',
                borderRadius: 6,
                background: 'rgba(255,255,255,0.06)',
                color: 'var(--text-muted)',
              }}
            >
              GET /api/v1/health
            </span>
          </div>

          <div style={{ background: 'rgba(0, 0, 0, 0.35)', borderRadius: 10, padding: 14, marginBottom: 16 }}>
            {healthData ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: '0.85rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-dim)' }}>Service Name:</span>
                  <span style={{ fontWeight: 600 }}>{healthData.name}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-dim)' }}>Version:</span>
                  <span style={{ color: '#38bdf8' }}>v{healthData.version}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-dim)' }}>Latency:</span>
                  <span style={{ color: '#34d399' }}>{pingMs} ms</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-dim)' }}>Status Code:</span>
                  <span style={{ color: '#10b981' }}>200 OK</span>
                </div>
              </div>
            ) : (
              <p style={{ color: 'var(--text-dim)', fontSize: '0.85rem', margin: 0 }}>
                {backendStatus === 'checking'
                  ? 'Connecting to backend...'
                  : 'Start the backend using `uvicorn app.main:app --reload` to test live endpoints.'}
              </p>
            )}
          </div>

          <button
            onClick={checkHealth}
            style={{
              width: '100%',
              padding: '10px 16px',
              borderRadius: 8,
              background: 'rgba(99, 102, 241, 0.2)',
              border: '1px solid rgba(99, 102, 241, 0.4)',
              color: '#ffffff',
              fontSize: '0.85rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8,
              transition: 'all 0.2s ease',
            }}
          >
            <Activity size={16} /> Re-test Health Endpoint
          </button>
        </div>

        {/* Card 2: Session Security Handshake Simulation */}
        <div className="glass-panel" style={{ padding: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: 8,
                  background: 'rgba(99, 102, 241, 0.15)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <KeyRound size={20} color="#818cf8" />
              </div>
              <h3 style={{ fontSize: '1.1rem', margin: 0 }}>Session Auth Architecture</h3>
            </div>
            <span
              style={{
                fontSize: '0.75rem',
                padding: '3px 8px',
                borderRadius: 6,
                background: 'rgba(255,255,255,0.06)',
                color: 'var(--text-muted)',
              }}
            >
              POST /api/v1/sessions
            </span>
          </div>

          <div style={{ background: 'rgba(0, 0, 0, 0.35)', borderRadius: 10, padding: 14, marginBottom: 16 }}>
            {session ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: '0.8rem' }}>
                <div>
                  <span style={{ color: 'var(--text-dim)', display: 'block' }}>Public Session ID:</span>
                  <code style={{ color: '#a5b4fc', fontSize: '0.75rem', wordBreak: 'break-all' }}>{session.session_id}</code>
                </div>
                <div>
                  <span style={{ color: 'var(--text-dim)', display: 'block' }}>Secret Session Token (X-Session-Token):</span>
                  <code style={{ color: '#34d399', fontSize: '0.72rem', wordBreak: 'break-all' }}>
                    {session.session_token.slice(0, 20)}...[crypto protected]
                  </code>
                </div>
              </div>
            ) : (
              <p style={{ color: 'var(--text-dim)', fontSize: '0.85rem', margin: 0 }}>
                {sessionError
                  ? `Error: ${sessionError}`
                  : 'Demonstrates public session_id vs secrets.token_urlsafe(48) authentication protocol.'}
              </p>
            )}
          </div>

          <button
            onClick={createSampleSession}
            disabled={sessionLoading || backendStatus !== 'connected'}
            style={{
              width: '100%',
              padding: '10px 16px',
              borderRadius: 8,
              background: backendStatus === 'connected' ? 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)' : 'rgba(255,255,255,0.05)',
              border: 'none',
              color: backendStatus === 'connected' ? '#ffffff' : 'var(--text-dim)',
              fontSize: '0.85rem',
              fontWeight: 600,
              cursor: backendStatus === 'connected' ? 'pointer' : 'not-allowed',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8,
            }}
          >
            <ShieldCheck size={16} />
            {sessionLoading ? 'Negotiating Credentials...' : 'Test Session Handshake'}
          </button>
        </div>

        {/* Card 3: Phase 0 Checklist Verification */}
        <div className="glass-panel" style={{ padding: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: 8,
                  background: 'rgba(249, 115, 22, 0.15)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Layers size={20} color="#f97316" />
              </div>
              <h3 style={{ fontSize: '1.1rem', margin: 0 }}>Phase 0 DoD Status</h3>
            </div>
            <span
              style={{
                fontSize: '0.75rem',
                padding: '3px 8px',
                borderRadius: 6,
                background: 'rgba(16, 185, 129, 0.12)',
                color: '#34d399',
                border: '1px solid rgba(16, 185, 129, 0.3)',
              }}
            >
              100% Ready
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {[
              { id: 'T-001', title: 'FastAPI Backend & /health Endpoint', ok: true },
              { id: 'T-002', title: 'Vite + React 19 + TypeScript Scaffold', ok: true },
              { id: 'T-003', title: 'Docker Compose (FastAPI, React, PG, Redis)', ok: true },
              { id: 'T-004', title: 'Environment Config (.env.example)', ok: true },
              { id: 'T-005', title: 'Tooling Config (Ruff & Pytest passed)', ok: true },
            ].map((task) => (
              <div
                key={task.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '8px 12px',
                  borderRadius: 8,
                  background: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid var(--border-subtle)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <CheckCircle2 size={16} color="#10b981" />
                  <span style={{ fontSize: '0.82rem', color: 'var(--text-main)' }}>{task.title}</span>
                </div>
                <code style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>{task.id}</code>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Developer Quick Reference Bar */}
      <footer
        className="glass-panel"
        style={{
          padding: '18px 24px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 16,
          fontSize: '0.85rem',
          color: 'var(--text-muted)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Terminal size={16} color="#6366f1" />
          <span>
            Backend:{' '}
            <code style={{ color: '#a5b4fc', background: 'rgba(0,0,0,0.3)', padding: '2px 6px', borderRadius: 4 }}>
              uvicorn app.main:app --reload
            </code>
          </span>
          <span style={{ margin: '0 8px' }}>•</span>
          <span>
            Frontend:{' '}
            <code style={{ color: '#a5b4fc', background: 'rgba(0,0,0,0.3)', padding: '2px 6px', borderRadius: 4 }}>
              npm run dev
            </code>
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <span>Code Freeze: <strong>Oct 23, 2026</strong></span>
          <span style={{ color: '#10b981', fontWeight: 600 }}>● Phase 0 Complete</span>
        </div>
      </footer>
    </div>
  );
}

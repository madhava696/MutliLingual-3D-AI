import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ArrowRight, AudioLines, BookOpen, Check, ChevronDown, CircleHelp, Clock3, FileText,
  Globe2, House, Languages, LockKeyhole, LogOut, Menu, MessageCircle, Mic,
  MoreHorizontal, PanelLeftClose, Pencil, Plus, Search, Send, Settings2,
  ShieldCheck, Sparkles, Trash2, UserRound, X,
} from 'lucide-react';

type Language = 'te' | 'hi' | 'en';
type SessionData = { session_id: string; session_token: string; language: string; private_mode: boolean; expires_at: string };
type Chat = { id: string; title: string; updatedAt: number; messages: { role: 'user' | 'assistant'; text: string }[] };
const API_BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');
const HISTORY_KEY = 'mann_local_chats_v1';
const SESSION_KEY = 'mann_session_v1';

function readChats(): Chat[] { try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]') as Chat[]; } catch { return []; } }
function shortDate(ts: number) { const d = new Date(ts); const now = new Date(); if (d.toDateString() === now.toDateString()) return 'Today'; const y = new Date(); y.setDate(y.getDate() - 1); if (d.toDateString() === y.toDateString()) return 'Yesterday'; return d.toLocaleDateString(); }

export default function App() {
  const [session, setSession] = useState<SessionData | null>(() => { try { return JSON.parse(localStorage.getItem(SESSION_KEY) || 'null'); } catch { return null; } });
  const [loginView, setLoginView] = useState(!session);
  const [language, setLanguage] = useState<Language>('en');
  const [avatar, setAvatar] = useState<'man' | 'woman'>(() => (localStorage.getItem('mann_avatar') as 'man' | 'woman') || 'man');
  const [backend, setBackend] = useState<'checking' | 'online' | 'offline'>('checking');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [chats, setChats] = useState<Chat[]>(readChats);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [message, setMessage] = useState('');
  const [page, setPage] = useState<'chat' | 'notes' | 'reminders' | 'pdf' | 'research' | 'settings'>('chat');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [menuId, setMenuId] = useState<string | null>(null);
  const [renameId, setRenameId] = useState<string | null>(null);
  const [renameText, setRenameText] = useState('');
  const [toast, setToast] = useState('');
  const [healthText, setHealthText] = useState('Checking backend…');

  const activeChat = chats.find(c => c.id === activeId) || null;
  const visibleChats = useMemo(() => chats.filter(c => c.title.toLowerCase().includes(search.toLowerCase())).sort((a,b) => b.updatedAt-a.updatedAt), [chats, search]);
  const persistChats = useCallback((next: Chat[]) => { setChats(next); localStorage.setItem(HISTORY_KEY, JSON.stringify(next)); }, []);

  const checkBackend = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/api/v1/health`); if (!r.ok) throw new Error(); const d = await r.json(); setBackend('online'); setHealthText(`${d.name || 'Mann API'} connected`); }
    catch { setBackend('offline'); setHealthText(`Backend unavailable at ${API_BASE}`); }
  }, []);
  useEffect(() => { void checkBackend(); }, [checkBackend]);

  const startSession = async () => {
    setBusy(true); setError('');
    try {
      const r = await fetch(`${API_BASE}/api/v1/sessions`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ language, private_mode: false }) });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.detail || `Backend returned HTTP ${r.status}`);
      const s = data as SessionData; localStorage.setItem(SESSION_KEY, JSON.stringify(s)); setSession(s); setLoginView(false); setToast('Your companion session is ready.');
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not connect. Start the backend and try again.'); }
    finally { setBusy(false); }
  };
  const newChat = () => { const c: Chat = { id: crypto.randomUUID(), title: 'New conversation', updatedAt: Date.now(), messages: [] }; persistChats([c, ...chats]); setActiveId(c.id); setPage('chat'); setSidebarOpen(true); };
  const openChat = (id: string) => { setActiveId(id); setPage('chat'); setMenuId(null); };
  const sendMessage = () => {
    const text = message.trim(); if (!text) return;
    let c = activeChat;
    if (!c) { c = { id: crypto.randomUUID(), title: text.slice(0, 42), updatedAt: Date.now(), messages: [] }; }
    const updated: Chat = { ...c, title: c.messages.length ? c.title : text.slice(0, 42), updatedAt: Date.now(), messages: [...c.messages, { role: 'user', text }, { role: 'assistant', text: 'Your message is saved in this browser. The repository backend does not currently expose a chat-response endpoint, so live AI replies still need backend support.' }] };
    persistChats([updated, ...chats.filter(x => x.id !== updated.id)]); setActiveId(updated.id); setMessage('');
  };
  const renameChat = (id: string) => { const title = renameText.trim(); if (!title) return; persistChats(chats.map(c => c.id === id ? { ...c, title, updatedAt: Date.now() } : c)); setRenameId(null); setMenuId(null); };
  const deleteChat = (id: string) => { const next = chats.filter(c => c.id !== id); persistChats(next); if (activeId === id) setActiveId(null); setMenuId(null); };
  const logout = () => { localStorage.removeItem(SESSION_KEY); setSession(null); setLoginView(true); setActiveId(null); };
  const chooseAvatar = (v: 'man' | 'woman') => { setAvatar(v); localStorage.setItem('mann_avatar', v); };

  if (loginView) return <main className="login-shell">
    <section className="login-left"><div className="brand"><span className="brand-mark"><Sparkles size={25}/></span><span><b>mann<span className="brand-dot">.</span></b><small>YOUR AI COMPANION</small></span></div>
      <div className="login-copy"><span className="eyebrow"><span className="eyebrow-dot"/> YOUR SPACE, YOUR LANGUAGE</span><h1>A little help.<br/><em>A lot more possible.</em></h1><p>A personal AI companion for learning, creating and getting things done—in the language that feels natural to you.</p>
      <div className="login-benefits"><div><span><Languages/></span><b>Made for your language</b><small>Telugu, Hindi and English</small></div><div><span><ShieldCheck/></span><b>Private by design</b><small>Session-based access</small></div></div></div>
      <div className="login-foot">A thoughtful companion for everyday life <span>✳</span></div>
    </section>
    <section className="login-right"><div className="login-card"><div className="mobile-brand brand"><span className="brand-mark"><Sparkles size={23}/></span><span><b>mann<span className="brand-dot">.</span></b><small>YOUR AI COMPANION</small></span></div>
      <div className="avatar-preview"><div className="avatar-orbit orbit-one"/><div className="avatar-orbit orbit-two"/><div className="avatar-person"><div className="avatar-hair"/><div className="avatar-face"><span className="eye eye-left"/><span className="eye eye-right"/><span className="nose"/><span className="mouth"/></div><div className="avatar-neck"/><div className="avatar-body"/></div><span className="avatar-chip"><span/> Your companion is ready</span></div>
      <span className="eyebrow">WELCOME TO MANN</span><h2>Let's get started.</h2><p className="muted">Create a private companion session to enter your space.</p>
      <label className="field-label" htmlFor="language">Choose your language</label><div className="select-wrap"><Languages size={19}/><select id="language" value={language} onChange={e => setLanguage(e.target.value as Language)}><option value="en">English</option><option value="te">తెలుగు (Telugu)</option><option value="hi">हिन्दी (Hindi)</option></select><ChevronDown size={17}/></div>
      <label className="field-label">Choose your companion</label><div className="avatar-choice"><button className={avatar === 'man' ? 'choice active' : 'choice'} onClick={() => chooseAvatar('man')}><span className="choice-icon man-icon"><UserRound/></span><span><b>Man</b><small>Male companion</small></span>{avatar === 'man' && <Check className="choice-check" size={18}/>}</button><button className={avatar === 'woman' ? 'choice active' : 'choice'} onClick={() => chooseAvatar('woman')}><span className="choice-icon woman-icon"><UserRound/></span><span><b>Woman</b><small>Female companion</small></span>{avatar === 'woman' && <Check className="choice-check" size={18}/>}</button></div>
      {error && <div className="error-box">{error}</div>}
      <button className="primary-btn login-btn" disabled={busy} onClick={() => void startSession()}>{busy ? 'Connecting…' : 'Continue to Mann'}{!busy && <ArrowRight size={19}/>}</button>
      <div className="login-secure"><LockKeyhole size={14}/> Connects to your Mann backend to create a session</div>
      <div className={'backend-note ' + backend}><span/> {backend === 'online' ? 'Backend connected' : backend === 'checking' ? 'Checking backend connection' : 'Backend offline — start it to continue'}</div>
      <p className="login-disclaimer">This uses the repository's session-based access, not an email/password account. Account registration is not available in the current backend.</p>
    </div></section>
  </main>;

  return <div className="app-shell">
    {sidebarOpen && <aside className="sidebar"><div className="sidebar-brand"><div className="brand"><span className="brand-mark"><Sparkles size={23}/></span><span><b>mann<span className="brand-dot">.</span></b><small>YOUR AI COMPANION</small></span></div><button className="icon-btn collapse-btn" title="Hide sidebar" onClick={() => setSidebarOpen(false)}><PanelLeftClose size={19}/></button></div>
      <button className="new-chat-btn" onClick={newChat}><Plus size={19}/> New conversation</button><div className="side-label">YOUR SPACE</div>
      <nav className="side-nav"><button className={page === 'chat' ? 'nav-item selected' : 'nav-item'} onClick={() => setPage('chat')}><House/>Chat</button><button className={page === 'notes' ? 'nav-item selected' : 'nav-item'} onClick={() => setPage('notes')}><FileText/>Notes</button><button className={page === 'reminders' ? 'nav-item selected' : 'nav-item'} onClick={() => setPage('reminders')}><Clock3/>Reminders</button><button className={page === 'pdf' ? 'nav-item selected' : 'nav-item'} onClick={() => setPage('pdf')}><BookOpen/>PDF Assistant</button><button className={page === 'research' ? 'nav-item selected' : 'nav-item'} onClick={() => setPage('research')}><Globe2/>Web Research</button></nav>
      <div className="recent-heading"><span>RECENTS</span><span className="count-pill">{chats.length}</span></div><div className="search-box"><Search size={17}/><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search chats" aria-label="Search chats"/>{search && <button onClick={() => setSearch('')}><X size={14}/></button>}</div>
      <div className="chat-list">{visibleChats.length ? visibleChats.map(c => <div key={c.id} className={'chat-row ' + (c.id === activeId ? 'current' : '')}><button className="chat-open" onClick={() => openChat(c.id)}><MessageCircle size={17}/><span className="chat-open-text"><span>{c.title}</span><small>{shortDate(c.updatedAt)}</small></span></button><button className="chat-more" onClick={() => setMenuId(menuId === c.id ? null : c.id)} aria-label="Conversation options"><MoreHorizontal size={18}/></button>{menuId === c.id && <div className="chat-menu"><button onClick={() => { setRenameId(c.id); setRenameText(c.title); setMenuId(null); }}><Pencil size={15}/>Rename</button><button className="danger" onClick={() => deleteChat(c.id)}><Trash2 size={15}/>Delete</button></div>}{renameId === c.id && <form className="rename-form" onSubmit={e => {e.preventDefault(); renameChat(c.id);}}><input autoFocus value={renameText} onChange={e => setRenameText(e.target.value)}/><button type="submit"><Check size={15}/></button></form>}</div>) : <p className="empty-recents">{search ? 'No matching conversations.' : 'Your chats will appear here.'}</p>}</div>
      <div className="sidebar-bottom"><button className={page === 'settings' ? 'nav-item selected' : 'nav-item'} onClick={() => setPage('settings')}><Settings2/>Profile & settings</button><button className="nav-item logout-nav" onClick={logout}><LogOut/>End session</button><div className="user-chip"><span className="user-avatar"><UserRound size={18}/></span><span><b>Guest session</b><small>{session?.session_id ? session.session_id.slice(0, 8) + '…' : 'Local session'}</small></span><ShieldCheck size={17} className="user-shield"/></div></div>
    </aside>}
    <main className="main-area"><header className="topbar"><div className="crumbs">{!sidebarOpen && <button className="icon-btn" onClick={() => setSidebarOpen(true)}><Menu size={20}/></button>}<span>Mann</span><span className="slash">/</span><b>{page === 'chat' ? 'Home' : page === 'settings' ? 'Profile & settings' : page === 'pdf' ? 'PDF Assistant' : page === 'research' ? 'Web Research' : page[0].toUpperCase()+page.slice(1)}</b></div><div className="top-actions"><span className={'connection-pill ' + backend}><span/>{backend === 'online' ? 'Connected' : backend === 'checking' ? 'Checking' : 'Offline'}</span><span className="top-language"><Languages size={17}/><select value={language} onChange={e => setLanguage(e.target.value as Language)}><option value="en">English</option><option value="te">తెలుగు</option><option value="hi">हिन्दी</option></select></span><button className="privacy-pill" title="Session privacy"><ShieldCheck size={16}/> Session mode</button><span className="top-avatar">{avatar === 'man' ? 'M' : 'W'}</span></div></header>
      <div className="content-wrap">{page === 'chat' && <>
        <div className="welcome-head"><span className="eyebrow">YOUR PERSONAL AI COMPANION</span><h1>{activeChat ? activeChat.title : <>Hey there, <em>friend</em> <span className="sunburst">✳</span></>}</h1><p>I'm here to help you think, learn, and get things done.</p></div>
        <section className="hero-card"><div className="hero-copy"><span className="ready-badge"><span/> YOUR COMPANION IS READY</span><h2>A little help.<br/><em>A lot more possible.</em></h2><p>Ask a question, explore an idea, or simply start talking. We'll figure it out together.</p><button className="primary-btn" onClick={() => { if (!activeChat) newChat(); document.getElementById('chat-input')?.focus(); }}><Mic size={18}/> Start a conversation</button><span className="voice-hint"><AudioLines size={18}/> Voice or text, your choice</span></div><div className="hero-avatar-panel"><span className="avatar-label"><span/> {avatar === 'man' ? 'MAN' : 'WOMAN'} COMPANION</span><div className={'illustration-human ' + avatar}><div className="human-hair"/><div className="human-head"><i className="human-eye left"/><i className="human-eye right"/><i className="human-nose"/><i className="human-mouth"/></div><div className="human-neck"/><div className="human-shirt"/></div><span className="model-note">Avatar preview · 3D model not installed</span><span className="avatar-caption"><span/> Mann <i>·</i> Your AI companion</span></div></section>
        {activeChat?.messages.length ? <section className="messages-panel">{activeChat.messages.map((m,i)=><div key={i} className={'message ' + m.role}><span className="message-icon">{m.role === 'user' ? <UserRound size={17}/> : <Sparkles size={17}/>}</span><div><b>{m.role === 'user' ? 'You' : 'Mann'}</b><p>{m.text}</p></div></div>)}</section> : <section className="suggestions"><div className="section-title"><div><h3>What can we do today?</h3><p>A few good places to start.</p></div><span className="suggestion-mark">✳</span></div><div className="suggestion-grid"><button onClick={() => setMessage('Help me understand a difficult topic')}><span className="suggestion-icon purple"><BookOpen/></span><b>Learn something</b><small>Explain a topic simply</small><ArrowRight/></button><button onClick={() => setMessage('Help me organize my day')}><span className="suggestion-icon green"><FileText/></span><b>Get organized</b><small>Plan your next steps</small><ArrowRight/></button><button onClick={() => setPage('research')}><span className="suggestion-icon orange"><Globe2/></span><b>Explore an idea</b><small>Research a question</small><ArrowRight/></button></div></section>}
        <form className="composer" onSubmit={e => {e.preventDefault(); sendMessage();}}><button type="button" className="composer-add" title="Attach a file" onClick={() => setPage('pdf')}><Plus size={21}/></button><input id="chat-input" value={message} onChange={e => setMessage(e.target.value)} placeholder="Message Mann…"/><button type="button" className="mic-btn" title="Voice input is not connected yet" onClick={() => setToast('Voice input is not connected in this frontend yet.')}><Mic size={19}/></button><button className="send-btn" type="submit" disabled={!message.trim()} aria-label="Send message"><Send size={18}/></button></form><p className="composer-note">Mann can make mistakes. Check important information.</p>
      </>}
      {page !== 'chat' && <section className="simple-page"><span className="eyebrow">MANN AI COMPANION</span><h1>{page === 'settings' ? 'Your preferences' : page === 'notes' ? 'Your notes' : page === 'reminders' ? 'Your reminders' : page === 'pdf' ? 'Ask your documents' : 'Explore the web'}</h1><p>{page === 'settings' ? 'Personalize your companion experience.' : page === 'notes' ? 'Keep useful thoughts in one place.' : page === 'reminders' ? 'Keep track of what matters.' : page === 'pdf' ? 'Choose a PDF to get started.' : 'Explore a topic you are curious about.'}</p>
        {page === 'settings' ? <div className="settings-card"><h3>Companion appearance</h3><p>Choose the companion shown in your interface.</p><div className="avatar-choice settings-choices"><button className={avatar === 'man' ? 'choice active' : 'choice'} onClick={() => chooseAvatar('man')}><span className="choice-icon man-icon"><UserRound/></span><span><b>Man</b><small>Male companion</small></span>{avatar === 'man' && <Check className="choice-check" size={18}/>}</button><button className={avatar === 'woman' ? 'choice active' : 'choice'} onClick={() => chooseAvatar('woman')}><span className="choice-icon woman-icon"><UserRound/></span><span><b>Woman</b><small>Female companion</small></span>{avatar === 'woman' && <Check className="choice-check" size={18}/>}</button></div><h3>Backend connection</h3><p>{healthText}</p><button className="secondary-btn" onClick={() => void checkBackend()}>Check connection</button><h3>Session</h3><p>This backend supports session-based access. It does not currently provide email/password account login.</p><button className="secondary-btn" onClick={logout}><LogOut size={17}/> End session</button></div> : page === 'pdf' ? <div className="upload-card"><FileText size={35}/><h3>Choose a PDF file</h3><p>File selection UI only. Document parsing needs a connected backend feature.</p><label className="secondary-btn file-button">Choose PDF<input type="file" accept="application/pdf,.pdf" onChange={e => setToast(e.target.files?.[0] ? `${e.target.files[0].name} selected. PDF analysis is not connected yet.` : '')}/></label></div> : <div className="upload-card"><div className="upload-symbol">{page === 'notes' ? <FileText/> : page === 'reminders' ? <Clock3/> : <Globe2/>}</div><h3>{page === 'notes' ? 'Notes API available' : page === 'reminders' ? 'Reminders API available' : 'Research integration needed'}</h3><p>{page === 'research' ? 'Live web research is not connected to this frontend yet.' : `The existing backend has ${page} routes, but this page needs its full data workflow connected.`}</p><button className="secondary-btn" onClick={() => setToast('This feature is not fully connected yet.')}>Learn more <CircleHelp size={16}/></button></div>}</section>}
      <footer className="page-footer"><span><Sparkles size={14}/> Made for you, in your language</span><span>Session data · Local chat history</span></footer></div>
    </main>{toast && <div className="toast"><Check size={17}/>{toast}<button onClick={() => setToast('')}><X size={15}/></button></div>}
  </div>;
}

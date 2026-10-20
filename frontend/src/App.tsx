import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ArrowRight, AudioLines, BookOpen, Check, CheckCircle2, ChevronDown, Clock3,
  Copy, FileText, Globe2, House, Languages, Loader2, LockKeyhole, LogOut,
  Menu, MessageCircle, Mic, MicOff, MoreHorizontal, PanelLeftClose, Pencil,
  Plus, Search, Send, Settings2, ShieldCheck, Sparkles, Trash2,
  Upload, UserRound, Volume2, VolumeX, X
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

type Language = 'te' | 'hi' | 'en';
type SessionData = { session_id: string; session_token: string; language: string; private_mode: boolean; expires_at: string };
type ChatMessage = { role: 'user' | 'assistant'; text: string; model?: string; latency?: number; isTool?: boolean };
type Chat = { id: string; title: string; updatedAt: number; messages: ChatMessage[] };
type NoteItem = { id: string; session_id: string; title: string; content: string; language?: string; source_type?: string; created_at?: string; updated_at?: string };
type ReminderItem = { id: string; session_id: string; title: string; remind_at: string; description?: string; status: 'pending' | 'completed' | 'cancelled'; language?: string; created_at?: string };
type FileItem = { id: string; session_id: string; filename: string; content_type: string; size_bytes: number; created_at: string; page_count?: number; extracted_text_preview?: string };

const API_BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');
const HISTORY_KEY = 'mann_local_chats_v1';
const SESSION_KEY = 'mann_session_v1';

function readChats(): Chat[] {
  try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]') as Chat[]; }
  catch { return []; }
}

function shortDate(ts: number | string) {
  const d = new Date(ts);
  const now = new Date();
  if (d.toDateString() === now.toDateString()) return 'Today ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const y = new Date(); y.setDate(y.getDate() - 1);
  if (d.toDateString() === y.toDateString()) return 'Yesterday';
  return d.toLocaleDateString();
}

export default function App() {
  const [session, setSession] = useState<SessionData | null>(() => {
    try { return JSON.parse(localStorage.getItem(SESSION_KEY) || 'null'); } catch { return null; }
  });
  const [loginView, setLoginView] = useState(!session);
  const [language, setLanguage] = useState<Language>(() => (session?.language as Language) || 'en');
  const [avatar, setAvatar] = useState<'man' | 'woman'>(() => (localStorage.getItem('mann_avatar') as 'man' | 'woman') || 'man');
  const [backend, setBackend] = useState<'checking' | 'online' | 'offline'>('checking');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [toast, setToast] = useState('');
  const [healthText, setHealthText] = useState('Checking backend…');

  // Navigation & Chat state
  const [page, setPage] = useState<'chat' | 'notes' | 'reminders' | 'pdf' | 'research' | 'settings'>('chat');
  const [chats, setChats] = useState<Chat[]>(readChats);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [message, setMessage] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [menuId, setMenuId] = useState<string | null>(null);
  const [renameId, setRenameId] = useState<string | null>(null);
  const [renameText, setRenameText] = useState('');

  // Audio / Voice state
  const [ttsEnabled, setTtsEnabled] = useState(true);
  const [isRecording, setIsRecording] = useState(false);
  const [speakingText, setSpeakingText] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  // Notes state
  const [notes, setNotes] = useState<NoteItem[]>([]);
  const [notesLoading, setNotesLoading] = useState(false);
  const [showNoteForm, setShowNoteForm] = useState(false);
  const [noteTitle, setNoteTitle] = useState('');
  const [noteContent, setNoteContent] = useState('');

  // Reminders state
  const [reminders, setReminders] = useState<ReminderItem[]>([]);
  const [remindersLoading, setRemindersLoading] = useState(false);
  const [showReminderForm, setShowReminderForm] = useState(false);
  const [reminderTitle, setReminderTitle] = useState('');
  const [reminderDate, setReminderDate] = useState('');
  const [reminderDesc, setReminderDesc] = useState('');
  const [reminderFilter, setReminderFilter] = useState<'all' | 'pending' | 'completed'>('all');

  // Files / PDF state
  const [files, setFiles] = useState<FileItem[]>([]);
  const [filesLoading, setFilesLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<FileItem | null>(null);
  const [uploadingPdf, setUploadingPdf] = useState(false);
  const [pdfQuestion, setPdfQuestion] = useState('Summarize the key points of this document.');
  const [saveAsNote, setSaveAsNote] = useState(true);
  const [pdfAnalysis, setPdfAnalysis] = useState<string | null>(null);
  const [pdfAnalyzing, setPdfAnalyzing] = useState(false);

  // Web Research state
  const [researchTopic, setResearchTopic] = useState('');
  const [researching, setResearching] = useState(false);
  const [researchResult, setResearchResult] = useState<string | null>(null);

  const activeChat = chats.find(c => c.id === activeId) || null;
  const visibleChats = useMemo(() =>
    chats.filter(c => c.title.toLowerCase().includes(search.toLowerCase())).sort((a,b) => b.updatedAt - a.updatedAt),
    [chats, search]
  );

  const persistChats = useCallback((next: Chat[]) => {
    setChats(next);
    localStorage.setItem(HISTORY_KEY, JSON.stringify(next));
  }, []);

  const showNotification = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(prev => prev === msg ? '' : prev), 5000);
  };

  // Helper auth headers
  const getAuthHeaders = useCallback(() => {
    return {
      'Content-Type': 'application/json',
      'X-Session-Token': session?.session_token || '',
    };
  }, [session]);

  const checkBackend = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/api/v1/health`);
      if (!r.ok) throw new Error();
      const d = await r.json();
      setBackend('online');
      setHealthText(`${d.name || 'Mann API'} connected`);
    } catch {
      setBackend('offline');
      setHealthText(`Backend unavailable at ${API_BASE}`);
    }
  }, []);

  useEffect(() => { void checkBackend(); }, [checkBackend]);

  // Voice TTS helper
  const speakText = useCallback((text: string, lang: Language) => {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    if (!text.trim()) { setSpeakingText(null); return; }

    const utterance = new SpeechSynthesisUtterance(text);
    const langMap: Record<Language, string> = { en: 'en-US', hi: 'hi-IN', te: 'te-IN' };
    utterance.lang = langMap[lang] || 'en-US';
    utterance.rate = 1.0;

    const voices = window.speechSynthesis.getVoices();
    const matchingVoice = voices.find(v => v.lang.startsWith(lang)) || voices.find(v => v.lang.startsWith('en'));
    if (matchingVoice) utterance.voice = matchingVoice;

    setSpeakingText(text);
    utterance.onend = () => setSpeakingText(null);
    utterance.onerror = () => setSpeakingText(null);
    window.speechSynthesis.speak(utterance);
  }, []);

  const toggleSpeak = (text: string) => {
    if (speakingText === text) {
      window.speechSynthesis.cancel();
      setSpeakingText(null);
    } else {
      speakText(text, language);
    }
  };

  // Start Session
  const startSession = async () => {
    setBusy(true); setError('');
    try {
      const r = await fetch(`${API_BASE}/api/v1/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language, private_mode: false })
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.detail || `Backend returned HTTP ${r.status}`);
      const s = data as SessionData;
      localStorage.setItem(SESSION_KEY, JSON.stringify(s));
      setSession(s);
      setLoginView(false);
      showNotification('Your companion session is ready.');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not connect. Make sure backend is running.');
    } finally {
      setBusy(false);
    }
  };

  const logout = () => {
    localStorage.removeItem(SESSION_KEY);
    setSession(null);
    setLoginView(true);
    setActiveId(null);
  };

  const chooseAvatar = (v: 'man' | 'woman') => {
    setAvatar(v);
    localStorage.setItem('mann_avatar', v);
  };

  const newChat = () => {
    const c: Chat = { id: crypto.randomUUID(), title: 'New conversation', updatedAt: Date.now(), messages: [] };
    persistChats([c, ...chats]);
    setActiveId(c.id);
    setPage('chat');
    setSidebarOpen(true);
  };

  const openChat = (id: string) => {
    setActiveId(id);
    setPage('chat');
    setMenuId(null);
  };

  // ------------------ Data Loaders ------------------
  const loadNotes = useCallback(async () => {
    if (!session?.session_id || !session?.session_token) return;
    setNotesLoading(true);
    try {
      const r = await fetch(`${API_BASE}/api/v1/notes?session_id=${session.session_id}`, {
        headers: { 'X-Session-Token': session.session_token }
      });
      if (r.ok) {
        const data = await r.json();
        setNotes(data.notes || []);
      }
    } catch {
      // offline/error handling
    } finally {
      setNotesLoading(false);
    }
  }, [session]);

  const loadReminders = useCallback(async () => {
    if (!session?.session_id || !session?.session_token) return;
    setRemindersLoading(true);
    try {
      const r = await fetch(`${API_BASE}/api/v1/tasks/reminders?session_id=${session.session_id}`, {
        headers: { 'X-Session-Token': session.session_token }
      });
      if (r.ok) {
        const data = await r.json();
        setReminders(data.reminders || []);
      }
    } catch {
      // error handled
    } finally {
      setRemindersLoading(false);
    }
  }, [session]);

  const loadFiles = useCallback(async () => {
    if (!session?.session_id || !session?.session_token) return;
    setFilesLoading(true);
    try {
      const r = await fetch(`${API_BASE}/api/v1/files?session_id=${session.session_id}`, {
        headers: { 'X-Session-Token': session.session_token }
      });
      if (r.ok) {
        const data = await r.json();
        setFiles(data || []);
        if (data.length > 0 && !selectedFile) {
          setSelectedFile(data[0]);
        }
      }
    } catch {
      // error handled
    } finally {
      setFilesLoading(false);
    }
  }, [session, selectedFile]);

  useEffect(() => {
    if (page === 'notes') void loadNotes();
    if (page === 'reminders') void loadReminders();
    if (page === 'pdf') void loadFiles();
  }, [page, loadNotes, loadReminders, loadFiles]);

  // ------------------ Send Chat Message ------------------
  const sendMessage = async (overrideText?: string) => {
    const text = (overrideText ?? message).trim();
    if (!text || !session) return;

    let targetChat = activeChat;
    if (!targetChat) {
      targetChat = { id: crypto.randomUUID(), title: text.slice(0, 36), updatedAt: Date.now(), messages: [] };
      setActiveId(targetChat.id);
    }

    const userMsg: ChatMessage = { role: 'user', text };
    const chatWithUser: Chat = {
      ...targetChat,
      title: targetChat.messages.length ? targetChat.title : text.slice(0, 36),
      updatedAt: Date.now(),
      messages: [...targetChat.messages, userMsg],
    };

    persistChats([chatWithUser, ...chats.filter(x => x.id !== chatWithUser.id)]);
    setMessage('');
    setChatLoading(true);

    try {
      const historyPayload = chatWithUser.messages.slice(-8).map(m => ({
        role: m.role,
        content: m.text,
      }));

      const r = await fetch(`${API_BASE}/api/v1/sessions/${session.session_id}/chat`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          message: text,
          language,
          conversation_history: historyPayload,
        }),
      });

      const data = await r.json().catch(() => ({}));
      if (!r.ok) {
        throw new Error(data.detail || `Chat request failed with HTTP ${r.status}`);
      }

      const replyText = data.response || 'I processed your request.';
      const assistantMsg: ChatMessage = {
        role: 'assistant',
        text: replyText,
        model: data.model_used,
        latency: data.latency_ms,
        isTool: data.is_tool_result,
      };

      const finalChat: Chat = {
        ...chatWithUser,
        updatedAt: Date.now(),
        messages: [...chatWithUser.messages, assistantMsg],
      };
      persistChats([finalChat, ...chats.filter(x => x.id !== finalChat.id)]);

      // If voice enabled, speak the answer
      if (ttsEnabled) {
        speakText(replyText, language);
      }

      // If a tool executed (like reminder or note created), refresh state
      if (data.is_tool_result) {
        void loadNotes();
        void loadReminders();
      }
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : 'Error communicating with assistant';
      const failMsg: ChatMessage = {
        role: 'assistant',
        text: `⚠️ ${errMsg}. Please verify that the backend and model key are configured.`,
      };
      const finalChat: Chat = {
        ...chatWithUser,
        updatedAt: Date.now(),
        messages: [...chatWithUser.messages, failMsg],
      };
      persistChats([finalChat, ...chats.filter(x => x.id !== finalChat.id)]);
    } finally {
      setChatLoading(false);
    }
  };

  // ------------------ Voice Recording & Transcription ------------------
  const startRecording = async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      showNotification('Audio recording is not supported in this browser.');
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const recorder = new MediaRecorder(stream);

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        await uploadAndTranscribe(audioBlob);
      };

      recorder.start();
      mediaRecorderRef.current = recorder;
      setIsRecording(true);
      showNotification('Listening… Click mic again to send.');
    } catch {
      showNotification('Microphone access denied or unavailable.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const uploadAndTranscribe = async (audioBlob: Blob) => {
    if (!session) return;
    setChatLoading(true);
    showNotification('Transcribing speech with Whisper…');
    try {
      const formData = new FormData();
      formData.append('file', audioBlob, 'recording.webm');
      formData.append('language', language);

      const r = await fetch(`${API_BASE}/api/v1/audio/transcribe`, {
        method: 'POST',
        headers: { 'X-Session-Token': session.session_token },
        body: formData,
      });

      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.detail || 'Speech transcription failed');

      const transcribed = data.text?.trim();
      if (transcribed) {
        showNotification(`Heard: "${transcribed}"`);
        void sendMessage(transcribed);
      } else {
        showNotification('No speech recognized. Please try again.');
      }
    } catch (e) {
      showNotification(e instanceof Error ? e.message : 'Speech transcription failed');
    } finally {
      setChatLoading(false);
    }
  };

  // ------------------ Notes Operations ------------------
  const handleCreateNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!noteTitle.trim() || !session) return;
    try {
      const r = await fetch(`${API_BASE}/api/v1/notes`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          session_id: session.session_id,
          title: noteTitle.trim(),
          content: noteContent.trim(),
          source_type: 'manual',
        }),
      });
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        throw new Error(err.detail || 'Could not save note');
      }
      setNoteTitle('');
      setNoteContent('');
      setShowNoteForm(false);
      showNotification('Note saved successfully!');
      void loadNotes();
    } catch (err) {
      showNotification(err instanceof Error ? err.message : 'Failed to save note');
    }
  };

  const handleDeleteNote = async (noteId: string) => {
    if (!session) return;
    try {
      const r = await fetch(`${API_BASE}/api/v1/notes/${noteId}`, {
        method: 'DELETE',
        headers: { 'X-Session-Token': session.session_token },
      });
      if (r.ok) {
        setNotes(prev => prev.filter(n => n.id !== noteId));
        showNotification('Note deleted.');
      }
    } catch {
      showNotification('Failed to delete note.');
    }
  };

  // ------------------ Reminders Operations ------------------
  const handleCreateReminder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reminderTitle.trim() || !reminderDate || !session) return;
    try {
      const r = await fetch(`${API_BASE}/api/v1/tasks/reminders`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          session_id: session.session_id,
          title: reminderTitle.trim(),
          remind_at: new Date(reminderDate).toISOString(),
          description: reminderDesc.trim() || null,
        }),
      });
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        throw new Error(err.detail || 'Could not set reminder');
      }
      setReminderTitle('');
      setReminderDate('');
      setReminderDesc('');
      setShowReminderForm(false);
      showNotification('Reminder scheduled!');
      void loadReminders();
    } catch (err) {
      showNotification(err instanceof Error ? err.message : 'Failed to set reminder');
    }
  };

  const handleToggleReminder = async (reminder: ReminderItem) => {
    if (!session) return;
    const nextStatus = reminder.status === 'completed' ? 'pending' : 'completed';
    try {
      const r = await fetch(`${API_BASE}/api/v1/tasks/reminders/${reminder.id}`, {
        method: 'PATCH',
        headers: getAuthHeaders(),
        body: JSON.stringify({ status: nextStatus }),
      });
      if (r.ok) {
        setReminders(prev => prev.map(rem => rem.id === reminder.id ? { ...rem, status: nextStatus } : rem));
        showNotification(nextStatus === 'completed' ? 'Marked reminder as done!' : 'Reminder pending');
      }
    } catch {
      showNotification('Failed to update reminder status');
    }
  };

  const handleDeleteReminder = async (reminderId: string) => {
    if (!session) return;
    try {
      const r = await fetch(`${API_BASE}/api/v1/tasks/reminders/${reminderId}`, {
        method: 'DELETE',
        headers: { 'X-Session-Token': session.session_token },
      });
      if (r.ok) {
        setReminders(prev => prev.filter(r => r.id !== reminderId));
        showNotification('Reminder deleted.');
      }
    } catch {
      showNotification('Failed to delete reminder.');
    }
  };

  // ------------------ PDF Operations ------------------
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !session) return;
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      showNotification('Please choose a valid PDF file.');
      return;
    }

    setUploadingPdf(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('session_id', session.session_id);

      const r = await fetch(`${API_BASE}/api/v1/files/upload`, {
        method: 'POST',
        headers: { 'X-Session-Token': session.session_token },
        body: formData,
      });

      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.detail || 'PDF upload failed');

      showNotification(`"${file.name}" uploaded successfully!`);
      setSelectedFile(data);
      void loadFiles();
    } catch (err) {
      showNotification(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploadingPdf(false);
      e.target.value = '';
    }
  };

  const handleAnalyzePdf = async () => {
    if (!selectedFile || !session) return;
    setPdfAnalyzing(true);
    setPdfAnalysis(null);
    try {
      const r = await fetch(`${API_BASE}/api/v1/files/${selectedFile.id}/analyze`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          question: pdfQuestion.trim() || 'Summarize the key points of this document.',
          save_as_note: saveAsNote,
        }),
      });

      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.detail || 'Analysis failed');

      setPdfAnalysis(data.analysis);
      if (data.note_id) {
        showNotification('Analysis saved to Notes!');
        void loadNotes();
      }
    } catch (err) {
      showNotification(err instanceof Error ? err.message : 'PDF analysis failed');
    } finally {
      setPdfAnalyzing(false);
    }
  };

  const handleDeleteFile = async (fileId: string) => {
    if (!session) return;
    try {
      const r = await fetch(`${API_BASE}/api/v1/files/${fileId}`, {
        method: 'DELETE',
        headers: { 'X-Session-Token': session.session_token },
      });
      if (r.ok) {
        setFiles(prev => prev.filter(f => f.id !== fileId));
        if (selectedFile?.id === fileId) {
          setSelectedFile(null);
          setPdfAnalysis(null);
        }
        showNotification('File deleted.');
      }
    } catch {
      showNotification('Failed to delete file.');
    }
  };

  // ------------------ Web Research Operations ------------------
  const handleResearch = async (topic: string) => {
    const q = topic.trim();
    if (!q || !session) return;
    setResearching(true);
    setResearchResult(null);
    try {
      const prompt = `Conduct an informative, well-structured research brief on the following topic:\n"${q}".\nInclude key takeaways, current landscape, and practical insights.`;
      const r = await fetch(`${API_BASE}/api/v1/sessions/${session.session_id}/chat`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          message: prompt,
          language,
          conversation_history: [],
        }),
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.detail || 'Research request failed');
      setResearchResult(data.response || 'No findings available.');
    } catch (e) {
      showNotification(e instanceof Error ? e.message : 'Research query failed');
    } finally {
      setResearching(false);
    }
  };

  const saveResearchToNotes = async () => {
    if (!researchResult || !researchTopic.trim() || !session) return;
    try {
      const r = await fetch(`${API_BASE}/api/v1/notes`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          session_id: session.session_id,
          title: `Research: ${researchTopic.trim()}`,
          content: researchResult,
          source_type: 'research',
        }),
      });
      if (r.ok) {
        showNotification('Research findings saved to Notes!');
        void loadNotes();
      }
    } catch {
      showNotification('Could not save note');
    }
  };

  // ------------------ Login Screen ------------------
  if (loginView) {
    return (
      <main className="login-shell">
        <section className="login-left">
          <div className="brand">
            <span className="brand-mark"><Sparkles size={25} /></span>
            <span><b>mann<span className="brand-dot">.</span></b><small>YOUR AI COMPANION</small></span>
          </div>
          <div className="login-copy">
            <span className="eyebrow"><span className="eyebrow-dot" /> YOUR SPACE, YOUR LANGUAGE</span>
            <h1>A little help.<br /><em>A lot more possible.</em></h1>
            <p>A personal multilingual companion for chat, notes, reminders, PDF reading, and voice interaction.</p>
            <div className="login-benefits">
              <div>
                <span><Languages /></span>
                <b>Made for your language</b>
                <small>Telugu, Hindi and English</small>
              </div>
              <div>
                <span><ShieldCheck /></span>
                <b>Private by design</b>
                <small>Session-based security</small>
              </div>
            </div>
          </div>
          <div className="login-foot">A thoughtful companion for everyday life <span>✳</span></div>
        </section>

        <section className="login-right">
          <div className="login-card">
            <div className="mobile-brand brand">
              <span className="brand-mark"><Sparkles size={23} /></span>
              <span><b>mann<span className="brand-dot">.</span></b><small>YOUR AI COMPANION</small></span>
            </div>
            <div className="avatar-preview">
              <div className="avatar-orbit orbit-one" />
              <div className="avatar-orbit orbit-two" />
              <div className="avatar-person">
                <div className="avatar-hair" />
                <div className="avatar-face">
                  <span className="eye eye-left" />
                  <span className="eye eye-right" />
                  <span className="nose" />
                  <span className="mouth" />
                </div>
                <div className="avatar-neck" />
                <div className="avatar-body" />
              </div>
              <span className="avatar-chip"><span /> Companion Ready</span>
            </div>

            <span className="eyebrow">WELCOME TO MANN</span>
            <h2>Let's get started.</h2>
            <p className="muted">Create a private companion session to enter your space.</p>

            <label className="field-label" htmlFor="language">Choose your language</label>
            <div className="select-wrap">
              <Languages size={19} />
              <select id="language" value={language} onChange={e => setLanguage(e.target.value as Language)}>
                <option value="en">English</option>
                <option value="te">తెలుగు (Telugu)</option>
                <option value="hi">हिन्दी (Hindi)</option>
              </select>
              <ChevronDown size={17} />
            </div>

            <label className="field-label">Choose your companion</label>
            <div className="avatar-choice">
              <button className={avatar === 'man' ? 'choice active' : 'choice'} onClick={() => chooseAvatar('man')}>
                <span className="choice-icon man-icon"><UserRound /></span>
                <span><b>Man</b><small>Male companion</small></span>
                {avatar === 'man' && <Check className="choice-check" size={18} />}
              </button>
              <button className={avatar === 'woman' ? 'choice active' : 'choice'} onClick={() => chooseAvatar('woman')}>
                <span className="choice-icon woman-icon"><UserRound /></span>
                <span><b>Woman</b><small>Female companion</small></span>
                {avatar === 'woman' && <Check className="choice-check" size={18} />}
              </button>
            </div>

            {error && <div className="error-box">{error}</div>}

            <button className="primary-btn login-btn" disabled={busy} onClick={() => void startSession()}>
              {busy ? 'Connecting…' : 'Continue to Mann'}
              {!busy && <ArrowRight size={19} />}
            </button>

            <div className="login-secure"><LockKeyhole size={14} /> Connects to your Mann backend session</div>
            <div className={'backend-note ' + backend}>
              <span /> {backend === 'online' ? 'Backend connected' : backend === 'checking' ? 'Checking backend connection' : 'Backend offline — ensure backend server is running'}
            </div>
          </div>
        </section>
      </main>
    );
  }

  // ------------------ Main Application ------------------
  return (
    <div className="app-shell">
      {sidebarOpen && (
        <aside className="sidebar">
          <div className="sidebar-brand">
            <div className="brand">
              <span className="brand-mark"><Sparkles size={23} /></span>
              <span><b>mann<span className="brand-dot">.</span></b><small>YOUR AI COMPANION</small></span>
            </div>
            <button className="icon-btn collapse-btn" title="Hide sidebar" onClick={() => setSidebarOpen(false)}>
              <PanelLeftClose size={19} />
            </button>
          </div>

          <button className="new-chat-btn" onClick={newChat}><Plus size={19} /> New conversation</button>

          <div className="side-label">YOUR SPACE</div>
          <nav className="side-nav">
            <button className={page === 'chat' ? 'nav-item selected' : 'nav-item'} onClick={() => setPage('chat')}>
              <House />Chat
            </button>
            <button className={page === 'notes' ? 'nav-item selected' : 'nav-item'} onClick={() => setPage('notes')}>
              <FileText />Notes {notes.length > 0 && <span className="count-pill">{notes.length}</span>}
            </button>
            <button className={page === 'reminders' ? 'nav-item selected' : 'nav-item'} onClick={() => setPage('reminders')}>
              <Clock3 />Reminders {reminders.filter(r => r.status === 'pending').length > 0 && <span className="count-pill">{reminders.filter(r => r.status === 'pending').length}</span>}
            </button>
            <button className={page === 'pdf' ? 'nav-item selected' : 'nav-item'} onClick={() => setPage('pdf')}>
              <BookOpen />PDF Assistant {files.length > 0 && <span className="count-pill">{files.length}</span>}
            </button>
            <button className={page === 'research' ? 'nav-item selected' : 'nav-item'} onClick={() => setPage('research')}>
              <Globe2 />Web Research
            </button>
          </nav>

          <div className="recent-heading">
            <span>CONVERSATIONS</span>
            <span className="count-pill">{chats.length}</span>
          </div>

          <div className="search-box">
            <Search size={17} />
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search chats" aria-label="Search chats" />
            {search && <button onClick={() => setSearch('')}><X size={14} /></button>}
          </div>

          <div className="chat-list">
            {visibleChats.length ? visibleChats.map(c => (
              <div key={c.id} className={'chat-row ' + (c.id === activeId ? 'current' : '')}>
                <button className="chat-open" onClick={() => openChat(c.id)}>
                  <MessageCircle size={17} />
                  <span className="chat-open-text">
                    <span>{c.title}</span>
                    <small>{shortDate(c.updatedAt)}</small>
                  </span>
                </button>
                <button className="chat-more" onClick={() => setMenuId(menuId === c.id ? null : c.id)} aria-label="Options">
                  <MoreHorizontal size={18} />
                </button>
                {menuId === c.id && (
                  <div className="chat-menu">
                    <button onClick={() => { setRenameId(c.id); setRenameText(c.title); setMenuId(null); }}>
                      <Pencil size={15} />Rename
                    </button>
                    <button className="danger" onClick={() => {
                      const next = chats.filter(x => x.id !== c.id);
                      persistChats(next);
                      if (activeId === c.id) setActiveId(null);
                      setMenuId(null);
                    }}>
                      <Trash2 size={15} />Delete
                    </button>
                  </div>
                )}
                {renameId === c.id && (
                  <form className="rename-form" onSubmit={e => {
                    e.preventDefault();
                    if (renameText.trim()) {
                      persistChats(chats.map(item => item.id === c.id ? { ...item, title: renameText.trim(), updatedAt: Date.now() } : item));
                    }
                    setRenameId(null);
                  }}>
                    <input autoFocus value={renameText} onChange={e => setRenameText(e.target.value)} />
                    <button type="submit"><Check size={15} /></button>
                  </form>
                )}
              </div>
            )) : <p className="empty-recents">{search ? 'No matching conversations.' : 'Your chats will appear here.'}</p>}
          </div>

          <div className="sidebar-bottom">
            <button className={page === 'settings' ? 'nav-item selected' : 'nav-item'} onClick={() => setPage('settings')}>
              <Settings2 />Profile & settings
            </button>
            <button className="nav-item logout-nav" onClick={logout}>
              <LogOut />End session
            </button>
            <div className="user-chip">
              <span className="user-avatar"><UserRound size={18} /></span>
              <span>
                <b>Active Session</b>
                <small>{session?.session_id ? session.session_id.slice(0, 8) + '…' : 'Local'}</small>
              </span>
              <ShieldCheck size={17} className="user-shield" />
            </div>
          </div>
        </aside>
      )}

      <main className="main-area">
        <header className="topbar">
          <div className="crumbs">
            {!sidebarOpen && (
              <button className="icon-btn" onClick={() => setSidebarOpen(true)}>
                <Menu size={20} />
              </button>
            )}
            <span>Mann</span>
            <span className="slash">/</span>
            <b>{page === 'chat' ? 'Home' : page === 'settings' ? 'Profile & Settings' : page === 'pdf' ? 'PDF Assistant' : page === 'research' ? 'Web Research' : page[0].toUpperCase() + page.slice(1)}</b>
          </div>

          <div className="top-actions">
            <button
              className={`top-toggle-btn ${ttsEnabled ? 'active' : ''}`}
              title="Toggle automatic speech synthesis"
              onClick={() => {
                setTtsEnabled(!ttsEnabled);
                if (ttsEnabled) window.speechSynthesis.cancel();
              }}
            >
              {ttsEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
              <span>Voice Reply {ttsEnabled ? 'ON' : 'OFF'}</span>
            </button>

            <span className={'connection-pill ' + backend}>
              <span />{backend === 'online' ? 'Connected' : backend === 'checking' ? 'Checking' : 'Offline'}
            </span>

            <span className="top-language">
              <Languages size={17} />
              <select value={language} onChange={e => setLanguage(e.target.value as Language)}>
                <option value="en">English</option>
                <option value="te">తెలుగు</option>
                <option value="hi">हिन्दी</option>
              </select>
            </span>

            <span className="top-avatar">{avatar === 'man' ? 'M' : 'W'}</span>
          </div>
        </header>

        <div className="content-wrap">
          {/* ===================== PAGE: CHAT ===================== */}
          {page === 'chat' && (
            <>
              <div className="welcome-head">
                <span className="eyebrow">YOUR PERSONAL AI COMPANION</span>
                <h1>{activeChat ? activeChat.title : <>Hey there, <em>friend</em> <span className="sunburst">✳</span></>}</h1>
                <p>I'm here to chat, manage your reminders, keep notes, read PDFs, and talk in your preferred language.</p>
              </div>

              {!activeChat?.messages.length && (
                <section className="hero-card">
                  <div className="hero-copy">
                    <span className="ready-badge"><span /> YOUR COMPANION IS READY</span>
                    <h2>A little help.<br /><em>A lot more possible.</em></h2>
                    <p>Ask a question, speak your thoughts, create a reminder, or drop in a PDF document. We'll do it together.</p>
                    <button className="primary-btn" onClick={() => { if (!activeChat) newChat(); document.getElementById('chat-input')?.focus(); }}>
                      <Mic size={18} /> Start a conversation
                    </button>
                    <span className="voice-hint"><AudioLines size={18} /> Voice transcription enabled with Whisper</span>
                  </div>

                  <div className="hero-avatar-panel">
                    <span className="avatar-label"><span /> {avatar === 'man' ? 'MAN' : 'WOMAN'} COMPANION</span>
                    <div className={'illustration-human ' + avatar}>
                      <div className="human-hair" />
                      <div className="human-head">
                        <i className="human-eye left" /><i className="human-eye right" /><i className="human-nose" /><i className="human-mouth" />
                      </div>
                      <div className="human-neck" />
                      <div className="human-shirt" />
                    </div>
                    <span className="avatar-caption"><span /> Mann <i>·</i> Ready to speak in {language === 'te' ? 'తెలుగు' : language === 'hi' ? 'हिन्दी' : 'English'}</span>
                  </div>
                </section>
              )}

              {/* Chat Messages */}
              {activeChat && activeChat.messages.length > 0 ? (
                <section className="messages-panel">
                  {activeChat.messages.map((m, i) => (
                    <div key={i} className={'message ' + m.role}>
                      <span className="message-icon">
                        {m.role === 'user' ? <UserRound size={17} /> : <Sparkles size={17} />}
                      </span>
                      <div style={{ width: '100%' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <b>{m.role === 'user' ? 'You' : 'Mann'}</b>
                          {m.model && <span className="model-pill">{m.model} {m.latency ? `(${m.latency}ms)` : ''}</span>}
                        </div>
                        <div className="markdown-content">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {m.text}
                          </ReactMarkdown>
                        </div>
                        {m.role === 'assistant' && (
                          <div className="message-actions">
                            <button
                              className={`msg-speak-btn ${speakingText === m.text ? 'playing' : ''}`}
                              onClick={() => toggleSpeak(m.text)}
                              title="Listen to this reply"
                            >
                              <Volume2 size={13} /> {speakingText === m.text ? 'Stop Audio' : 'Listen'}
                            </button>
                            <button
                              className="msg-speak-btn"
                              title="Copy response"
                              onClick={() => {
                                navigator.clipboard.writeText(m.text);
                                showNotification('Copied to clipboard!');
                              }}
                            >
                              <Copy size={13} /> Copy
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}

                  {chatLoading && (
                    <div className="message assistant">
                      <span className="message-icon"><Sparkles size={17} /></span>
                      <div>
                        <b>Mann is thinking…</b>
                        <div className="typing-dots"><span /><span /><span /></div>
                      </div>
                    </div>
                  )}
                </section>
              ) : (
                <section className="suggestions">
                  <div className="section-title">
                    <div>
                      <h3>What can we do today?</h3>
                      <p>Try any of these prompts or speak directly.</p>
                    </div>
                    <span className="suggestion-mark">✳</span>
                  </div>
                  <div className="suggestion-grid">
                    <button onClick={() => void sendMessage('Remind me to call the doctor tomorrow at 10 AM')}>
                      <span className="suggestion-icon green"><Clock3 /></span>
                      <b>Schedule a reminder</b>
                      <small>"Remind me to call the doctor tomorrow"</small>
                      <ArrowRight />
                    </button>
                    <button onClick={() => void sendMessage('Save a note: Remember to buy organic spices and olive oil')}>
                      <span className="suggestion-icon purple"><FileText /></span>
                      <b>Save a note</b>
                      <small>"Save a note: Remember to buy groceries"</small>
                      <ArrowRight />
                    </button>
                    <button onClick={() => setPage('pdf')}>
                      <span className="suggestion-icon orange"><BookOpen /></span>
                      <b>Analyze a PDF</b>
                      <small>Upload and ask questions about documents</small>
                      <ArrowRight />
                    </button>
                  </div>
                </section>
              )}

              {/* Voice active recording bar */}
              {isRecording && (
                <div className="voice-active-bar">
                  <div className="voice-pulse">
                    <div className="pulse-circle" />
                    <span>Recording speech (Groq Whisper)... Click mic to send</span>
                  </div>
                  <button className="secondary-btn" onClick={stopRecording}>
                    <MicOff size={15} /> Finish & Send
                  </button>
                </div>
              )}

              {/* Chat Composer */}
              <form className="composer" onSubmit={e => { e.preventDefault(); void sendMessage(); }}>
                <button type="button" className="composer-add" title="Upload a PDF file" onClick={() => setPage('pdf')}>
                  <Plus size={21} />
                </button>
                <input
                  id="chat-input"
                  value={message}
                  onChange={e => setMessage(e.target.value)}
                  placeholder="Message Mann (or click mic to talk)..."
                  disabled={chatLoading}
                />
                <button
                  type="button"
                  className={`mic-btn ${isRecording ? 'recording' : ''}`}
                  title={isRecording ? 'Stop recording' : 'Speak with your companion'}
                  onClick={isRecording ? stopRecording : () => void startRecording()}
                >
                  <Mic size={19} />
                </button>
                <button className="send-btn" type="submit" disabled={!message.trim() || chatLoading} aria-label="Send message">
                  {chatLoading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
                </button>
              </form>
              <p className="composer-note">Mann is powered by high-speed Groq inference and multilingual speech recognition.</p>
            </>
          )}

          {/* ===================== PAGE: NOTES ===================== */}
          {page === 'notes' && (
            <section className="simple-page">
              <div className="section-header-row">
                <div>
                  <span className="eyebrow">KNOWLEDGE BASE</span>
                  <h1 style={{ margin: '6px 0' }}>Your Notes</h1>
                  <p className="muted">Thoughts, summaries, and notes captured across your companion sessions.</p>
                </div>
                <button className="primary-btn" onClick={() => setShowNoteForm(!showNoteForm)}>
                  <Plus size={18} /> {showNoteForm ? 'Close form' : 'Create Note'}
                </button>
              </div>

              {showNoteForm && (
                <div className="feature-form-panel">
                  <h3><FileText size={20} /> New Note</h3>
                  <form onSubmit={handleCreateNote} className="form-grid">
                    <input
                      className="form-input"
                      placeholder="Note Title (e.g., Weekly Plan, Meeting Summary)..."
                      value={noteTitle}
                      onChange={e => setNoteTitle(e.target.value)}
                      required
                    />
                    <textarea
                      className="form-textarea"
                      placeholder="Write your note content here..."
                      value={noteContent}
                      onChange={e => setNoteContent(e.target.value)}
                      required
                    />
                    <div className="form-actions">
                      <button type="button" className="secondary-btn" onClick={() => setShowNoteForm(false)}>Cancel</button>
                      <button type="submit" className="primary-btn">Save Note</button>
                    </div>
                  </form>
                </div>
              )}

              {notesLoading ? (
                <div style={{ textAlign: 'center', padding: '40px', color: '#8898b0' }}>
                  <Loader2 className="animate-spin" size={30} style={{ margin: '0 auto 10px' }} />
                  <p>Loading your notes…</p>
                </div>
              ) : notes.length > 0 ? (
                <div className="item-grid">
                  {notes.map(note => (
                    <div key={note.id} className="card-item">
                      <div>
                        <div className="card-item-head">
                          <h4 className="card-item-title">{note.title}</h4>
                          <span className={`card-item-badge ${note.source_type === 'pdf_summary' ? 'pdf' : ''}`}>
                            {note.source_type === 'pdf_summary' ? 'PDF Summary' : note.source_type || 'Note'}
                          </span>
                        </div>
                        <p className="card-item-content">{note.content}</p>
                      </div>
                      <div className="card-item-foot">
                        <span>{note.created_at ? shortDate(note.created_at) : 'Saved'}</span>
                        <div className="card-actions">
                          <button
                            className="card-action-btn"
                            title="Listen"
                            onClick={() => toggleSpeak(`${note.title}. ${note.content}`)}
                          >
                            <Volume2 size={16} />
                          </button>
                          <button
                            className="card-action-btn"
                            title="Copy text"
                            onClick={() => {
                              navigator.clipboard.writeText(`${note.title}\n\n${note.content}`);
                              showNotification('Note copied!');
                            }}
                          >
                            <Copy size={16} />
                          </button>
                          <button
                            className="card-action-btn danger"
                            title="Delete note"
                            onClick={() => void handleDeleteNote(note.id)}
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="upload-card">
                  <div className="upload-symbol"><FileText /></div>
                  <h3>No notes saved yet</h3>
                  <p>You can create a note using the button above or simply tell Mann: "Save a note: [your text]".</p>
                  <button className="secondary-btn" onClick={() => setShowNoteForm(true)}>
                    <Plus size={16} /> Add your first note
                  </button>
                </div>
              )}
            </section>
          )}

          {/* ===================== PAGE: REMINDERS ===================== */}
          {page === 'reminders' && (
            <section className="simple-page">
              <div className="section-header-row">
                <div>
                  <span className="eyebrow">TASKS & SCHEDULE</span>
                  <h1 style={{ margin: '6px 0' }}>Your Reminders</h1>
                  <p className="muted">Stay organized with timely notifications in your preferred language.</p>
                </div>
                <div style={{ display: 'flex', gap: '10px' }}>
                  <button className="primary-btn" onClick={() => setShowReminderForm(!showReminderForm)}>
                    <Plus size={18} /> {showReminderForm ? 'Close form' : 'Set Reminder'}
                  </button>
                </div>
              </div>

              {showReminderForm && (
                <div className="feature-form-panel">
                  <h3><Clock3 size={20} /> Schedule a Reminder</h3>
                  <form onSubmit={handleCreateReminder} className="form-grid">
                    <input
                      className="form-input"
                      placeholder="Reminder title (e.g., Doctor appointment, Call parents)..."
                      value={reminderTitle}
                      onChange={e => setReminderTitle(e.target.value)}
                      required
                    />
                    <div className="form-row">
                      <input
                        className="form-input"
                        type="datetime-local"
                        value={reminderDate}
                        onChange={e => setReminderDate(e.target.value)}
                        required
                      />
                      <input
                        className="form-input"
                        placeholder="Optional description / details"
                        value={reminderDesc}
                        onChange={e => setReminderDesc(e.target.value)}
                      />
                    </div>
                    <div className="form-actions">
                      <button type="button" className="secondary-btn" onClick={() => setShowReminderForm(false)}>Cancel</button>
                      <button type="submit" className="primary-btn">Save Reminder</button>
                    </div>
                  </form>
                </div>
              )}

              {/* Status filter tabs */}
              <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
                {(['all', 'pending', 'completed'] as const).map(tab => (
                  <button
                    key={tab}
                    className={`preset-btn ${reminderFilter === tab ? 'selected' : ''}`}
                    style={reminderFilter === tab ? { background: '#6074e5', color: '#fff' } : {}}
                    onClick={() => setReminderFilter(tab)}
                  >
                    {tab[0].toUpperCase() + tab.slice(1)} ({tab === 'all' ? reminders.length : reminders.filter(r => r.status === tab).length})
                  </button>
                ))}
              </div>

              {remindersLoading ? (
                <div style={{ textAlign: 'center', padding: '40px', color: '#8898b0' }}>
                  <Loader2 className="animate-spin" size={30} style={{ margin: '0 auto 10px' }} />
                  <p>Loading your reminders…</p>
                </div>
              ) : reminders.length > 0 ? (
                <div className="item-grid">
                  {reminders
                    .filter(r => reminderFilter === 'all' || r.status === reminderFilter)
                    .map(rem => (
                      <div key={rem.id} className="card-item">
                        <div>
                          <div className="card-item-head">
                            <h4 className="card-item-title" style={{ textDecoration: rem.status === 'completed' ? 'line-through' : 'none' }}>
                              {rem.title}
                            </h4>
                            <span className={`card-item-badge ${rem.status}`}>
                              {rem.status}
                            </span>
                          </div>
                          {rem.description && <p className="card-item-content">{rem.description}</p>}
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: '#5f7190', marginTop: '8px' }}>
                            <Clock3 size={14} />
                            <span>Remind at: {new Date(rem.remind_at).toLocaleString()}</span>
                          </div>
                        </div>

                        <div className="card-item-foot" style={{ marginTop: '16px' }}>
                          <button
                            className="secondary-btn"
                            style={{ padding: '6px 10px', fontSize: '12px' }}
                            onClick={() => void handleToggleReminder(rem)}
                          >
                            <CheckCircle2 size={14} /> {rem.status === 'completed' ? 'Mark Pending' : 'Mark Done'}
                          </button>
                          <button
                            className="card-action-btn danger"
                            title="Delete reminder"
                            onClick={() => void handleDeleteReminder(rem.id)}
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </div>
                    ))}
                </div>
              ) : (
                <div className="upload-card">
                  <div className="upload-symbol"><Clock3 /></div>
                  <h3>No reminders set</h3>
                  <p>Keep track of what matters. Say "Remind me to [task] at [time]" in chat, or create one manually.</p>
                  <button className="secondary-btn" onClick={() => setShowReminderForm(true)}>
                    <Plus size={16} /> Create a reminder
                  </button>
                </div>
              )}
            </section>
          )}

          {/* ===================== PAGE: PDF ASSISTANT ===================== */}
          {page === 'pdf' && (
            <section className="simple-page" style={{ maxWidth: '100%' }}>
              <div className="section-header-row">
                <div>
                  <span className="eyebrow">DOCUMENT INTELLIGENCE</span>
                  <h1 style={{ margin: '6px 0' }}>PDF Assistant</h1>
                  <p className="muted">Upload PDF documents, extract text, and ask questions with AI in your language.</p>
                </div>
              </div>

              <div className="pdf-layout">
                {/* Left column: Upload & Files list */}
                <div>
                  <label className="pdf-upload-drop" style={{ display: 'block' }}>
                    <input
                      type="file"
                      accept="application/pdf,.pdf"
                      onChange={handleFileUpload}
                      style={{ display: 'none' }}
                      disabled={uploadingPdf}
                    />
                    <Upload size={34} />
                    <b style={{ display: 'block', fontSize: '14px', color: '#273852', marginBottom: '4px' }}>
                      {uploadingPdf ? 'Uploading & parsing PDF…' : 'Choose or drop a PDF'}
                    </b>
                    <small style={{ color: '#8b97ae' }}>Up to 10MB PDF documents</small>
                  </label>

                  <div style={{ marginTop: '20px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                      <b style={{ fontSize: '13px', color: '#4a5b78' }}>UPLOADED DOCUMENTS</b>
                      <span className="count-pill">{files.length}</span>
                    </div>

                    {filesLoading ? (
                      <div style={{ textAlign: 'center', padding: '20px', color: '#8898b0' }}>
                        <Loader2 className="animate-spin" size={24} style={{ margin: '0 auto' }} />
                      </div>
                    ) : files.length > 0 ? (
                      <div className="pdf-file-list">
                        {files.map(f => (
                          <div
                            key={f.id}
                            className={`pdf-file-card ${selectedFile?.id === f.id ? 'selected' : ''}`}
                            onClick={() => { setSelectedFile(f); setPdfAnalysis(null); }}
                          >
                            <div className="pdf-file-info">
                              <BookOpen size={20} color="#657be8" />
                              <div>
                                <b>{f.filename}</b>
                                <small>{f.page_count ? `${f.page_count} pages · ` : ''}{(f.size_bytes / 1024).toFixed(0)} KB</small>
                              </div>
                            </div>
                            <button
                              className="card-action-btn danger"
                              title="Delete file"
                              onClick={(e) => { e.stopPropagation(); void handleDeleteFile(f.id); }}
                            >
                              <Trash2 size={16} />
                            </button>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p style={{ fontSize: '12px', color: '#97a4bb' }}>No PDFs uploaded yet.</p>
                    )}
                  </div>
                </div>

                {/* Right column: Document details & Analysis */}
                <div>
                  {selectedFile ? (
                    <div className="pdf-analysis-view">
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <div>
                          <h3 style={{ margin: '0 0 6px', font: '800 20px Manrope, sans-serif', color: '#253651' }}>
                            {selectedFile.filename}
                          </h3>
                          <div className="pdf-meta-pills">
                            <span className="pdf-pill"><BookOpen size={13} /> {selectedFile.page_count || 1} Pages</span>
                            <span className="pdf-pill"><FileText size={13} /> {(selectedFile.size_bytes / 1024).toFixed(1)} KB</span>
                            <span className="pdf-pill"><Clock3 size={13} /> Uploaded {shortDate(selectedFile.created_at)}</span>
                          </div>
                        </div>
                      </div>

                      {selectedFile.extracted_text_preview && (
                        <div style={{ background: '#f8fafc', border: '1px solid #e7ecf5', borderRadius: '12px', padding: '14px', marginBottom: '16px' }}>
                          <small style={{ fontWeight: 700, color: '#7a8ba8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Document Preview</small>
                          <p style={{ fontSize: '12px', color: '#566682', margin: '6px 0 0', lineHeight: 1.6, maxHeight: '80px', overflow: 'hidden' }}>
                            {selectedFile.extracted_text_preview}
                          </p>
                        </div>
                      )}

                      <div className="pdf-qa-box">
                        <label style={{ display: 'block', fontSize: '13px', fontWeight: 700, color: '#283955', marginBottom: '8px' }}>
                          Ask anything about this document:
                        </label>
                        <div className="pdf-qa-presets">
                          <button className="preset-btn" onClick={() => setPdfQuestion('Summarize the key points of this document.')}>
                            Summarize document
                          </button>
                          <button className="preset-btn" onClick={() => setPdfQuestion('What are the key action items and conclusions?')}>
                            Action items
                          </button>
                          <button className="preset-btn" onClick={() => setPdfQuestion('Explain the main topic in simple terms in my preferred language.')}>
                            Simple explanation
                          </button>
                        </div>

                        <div style={{ display: 'flex', gap: '8px', marginTop: '10px' }}>
                          <input
                            className="form-input"
                            value={pdfQuestion}
                            onChange={e => setPdfQuestion(e.target.value)}
                            placeholder="Type a question about this PDF..."
                          />
                          <button
                            className="primary-btn"
                            disabled={pdfAnalyzing}
                            onClick={() => void handleAnalyzePdf()}
                            style={{ flexShrink: 0 }}
                          >
                            {pdfAnalyzing ? <Loader2 size={17} className="animate-spin" /> : <Sparkles size={17} />}
                            {pdfAnalyzing ? 'Analyzing…' : 'Analyze'}
                          </button>
                        </div>

                        <label className="save-note-toggle">
                          <input
                            type="checkbox"
                            checked={saveAsNote}
                            onChange={e => setSaveAsNote(e.target.checked)}
                          />
                          <span>Save summary/answer automatically to Notes</span>
                        </label>
                      </div>

                      {pdfAnalysis && (
                        <div className="analysis-result-card">
                          <h4>
                            <span>AI Analysis Result</span>
                            <div style={{ display: 'flex', gap: '6px' }}>
                              <button
                                className="card-action-btn"
                                title="Listen"
                                onClick={() => toggleSpeak(pdfAnalysis)}
                              >
                                <Volume2 size={16} />
                              </button>
                              <button
                                className="card-action-btn"
                                title="Copy"
                                onClick={() => {
                                  navigator.clipboard.writeText(pdfAnalysis);
                                  showNotification('Analysis copied!');
                                }}
                              >
                                <Copy size={16} />
                              </button>
                            </div>
                          </h4>
                          <div className="analysis-body markdown-content">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                              {pdfAnalysis}
                            </ReactMarkdown>
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="upload-card" style={{ height: '100%', justifyContent: 'center', alignItems: 'center', textAlign: 'center' }}>
                      <BookOpen size={45} color="#8a9fe8" />
                      <h3>Select or upload a PDF</h3>
                      <p>Choose an uploaded file from the left column or drop a new document to start querying it.</p>
                    </div>
                  )}
                </div>
              </div>
            </section>
          )}

          {/* ===================== PAGE: WEB RESEARCH ===================== */}
          {page === 'research' && (
            <section className="simple-page">
              <span className="eyebrow">EXPLORE & LEARN</span>
              <h1 style={{ margin: '6px 0' }}>Web Research</h1>
              <p className="muted">Investigate concepts, gather insights, and create comprehensive briefs in your language.</p>

              <div className="pdf-qa-box" style={{ background: '#fff', marginTop: '20px' }}>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 700, color: '#273852', marginBottom: '8px' }}>
                  What topic would you like to explore?
                </label>
                <div className="pdf-qa-presets">
                  <button className="preset-btn" onClick={() => { setResearchTopic('Artificial Intelligence trends in India 2026'); void handleResearch('Artificial Intelligence trends in India 2026'); }}>
                    AI in India 2026
                  </button>
                  <button className="preset-btn" onClick={() => { setResearchTopic('Renewable energy and solar adoption in rural areas'); void handleResearch('Renewable energy and solar adoption in rural areas'); }}>
                    Solar & Renewable Tech
                  </button>
                  <button className="preset-btn" onClick={() => { setResearchTopic('Effective habit building and time management'); void handleResearch('Effective habit building and time management'); }}>
                    Time Management Science
                  </button>
                </div>

                <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
                  <input
                    className="form-input"
                    value={researchTopic}
                    onChange={e => setResearchTopic(e.target.value)}
                    placeholder="Enter research topic or question..."
                  />
                  <button
                    className="primary-btn"
                    disabled={researching || !researchTopic.trim()}
                    onClick={() => void handleResearch(researchTopic)}
                    style={{ flexShrink: 0 }}
                  >
                    {researching ? <Loader2 size={17} className="animate-spin" /> : <Globe2 size={17} />}
                    {researching ? 'Researching…' : 'Explore'}
                  </button>
                </div>
              </div>

              {researchResult && (
                <div className="analysis-result-card" style={{ marginTop: '24px' }}>
                  <h4>
                    <span>Research Findings: {researchTopic}</span>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button className="secondary-btn" onClick={() => void saveResearchToNotes()} style={{ padding: '6px 12px', fontSize: '12px' }}>
                        <FileText size={14} /> Save to Notes
                      </button>
                      <button className="card-action-btn" onClick={() => toggleSpeak(researchResult)}>
                        <Volume2 size={16} />
                      </button>
                      <button className="card-action-btn" onClick={() => { navigator.clipboard.writeText(researchResult); showNotification('Copied!'); }}>
                        <Copy size={16} />
                      </button>
                    </div>
                  </h4>
                  <div className="analysis-body markdown-content">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {researchResult}
                    </ReactMarkdown>
                  </div>
                </div>
              )}
            </section>
          )}

          {/* ===================== PAGE: SETTINGS ===================== */}
          {page === 'settings' && (
            <section className="simple-page">
              <span className="eyebrow">PREFERENCES</span>
              <h1 style={{ margin: '6px 0' }}>Companion Preferences</h1>
              <p className="muted">Customize companion appearance, language, and backend status.</p>

              <div className="settings-card">
                <h3>Companion Appearance</h3>
                <p>Choose the companion avatar displayed across your interface.</p>
                <div className="avatar-choice settings-choices">
                  <button className={avatar === 'man' ? 'choice active' : 'choice'} onClick={() => chooseAvatar('man')}>
                    <span className="choice-icon man-icon"><UserRound /></span>
                    <span><b>Man</b><small>Male companion</small></span>
                    {avatar === 'man' && <Check className="choice-check" size={18} />}
                  </button>
                  <button className={avatar === 'woman' ? 'choice active' : 'choice'} onClick={() => chooseAvatar('woman')}>
                    <span className="choice-icon woman-icon"><UserRound /></span>
                    <span><b>Woman</b><small>Female companion</small></span>
                    {avatar === 'woman' && <Check className="choice-check" size={18} />}
                  </button>
                </div>

                <h3>Preferred Language</h3>
                <p>Current language for conversations, notes, and audio.</p>
                <div className="select-wrap" style={{ maxWidth: '300px', marginBottom: '20px' }}>
                  <Languages size={18} />
                  <select value={language} onChange={e => setLanguage(e.target.value as Language)}>
                    <option value="en">English</option>
                    <option value="te">తెలుగు (Telugu)</option>
                    <option value="hi">हिन्दी (Hindi)</option>
                  </select>
                </div>

                <h3>Backend Connection</h3>
                <p>{healthText}</p>
                <button className="secondary-btn" onClick={() => void checkBackend()}>
                  Check Connection Status
                </button>

                <h3 style={{ marginTop: '24px' }}>Session Management</h3>
                <p>Session ID: <code style={{ background: '#eef2fb', padding: '2px 6px', borderRadius: '4px' }}>{session?.session_id}</code></p>
                <button className="secondary-btn" onClick={logout} style={{ color: '#d24747' }}>
                  <LogOut size={16} /> End & Exit Session
                </button>
              </div>
            </section>
          )}

          <footer className="page-footer">
            <span><Sparkles size={14} /> Multilingual 3D AI Companion · Fast Groq & Whisper Integration</span>
            <span>Session ID: {session?.session_id ? session.session_id.slice(0, 8) + '…' : 'Active'}</span>
          </footer>
        </div>
      </main>

      {/* Floating Toast Notification */}
      {toast && (
        <div className="toast">
          <Check size={17} />
          <span>{toast}</span>
          <button onClick={() => setToast('')}><X size={15} /></button>
        </div>
      )}
    </div>
  );
}

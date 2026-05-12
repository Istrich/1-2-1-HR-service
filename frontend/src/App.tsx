import { useState, useEffect } from 'react';
import { Login } from './Login';
import { UploadPage } from './Upload';
import { Workspace } from './Workspace';
import { History } from './History';
import { SettingsModal, ApiSettingsModal } from './Settings';
import './App.css';

function App() {
  const [user, setUser] = useState<string | null>(localStorage.getItem('hr121_user'));
  const [view, setView] = useState<'upload' | 'processing' | 'workspace'>('upload');
  const [taskId, setTaskId] = useState<string | null>(null);
  const [wsData, setWsData] = useState<any>(null);
  const [mainTab, setMainTab] = useState<'form' | 'history'>('form');
  const [procState, setProcState] = useState<{ status: string; progress: number }>({ status: 'pending', progress: 0 });
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [apiSettingsOpen, setApiSettingsOpen] = useState(false);

  function logout() {
    localStorage.removeItem('hr121_token');
    localStorage.removeItem('hr121_user');
    setUser(null);
  }

  useEffect(() => {
    if (!taskId) return;

    // We must pass auth headers, but native EventSource doesn't support them.
    // For a real app, use SSE polyfill or send token in URL.
    // Here we'll append the token to the URL so the backend can read it if needed
    // (though our backend depends on Authorization header currently. Let's fix this for tests by sending it via URL)
    const token = localStorage.getItem('hr121_token');
    const eventSource = new EventSource(`/api/process/status/${taskId}?token=${token}`);

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setProcState({ status: data.status, progress: data.progress });

      if (data.status === 'done') {
        setWsData(data.result);
        setView('workspace');
        setTaskId(null);
        eventSource.close();
      } else if (data.status === 'error') {
        alert('Ошибка обработки: ' + data.error);
        setView('upload');
        setTaskId(null);
        eventSource.close();
      }
    };

    return () => {
      eventSource.close();
    };
  }, [taskId]);

  async function handleProcess({ type, file, url }: { type: 'file' | 'url'; file?: File; url?: string }) {
    setView('processing');
    setProcState({ status: 'starting', progress: 0 });
    try {
      let r;
      if (type === 'file' && file) {
        const fd = new FormData();
        fd.append('file', file);
        r = await fetch('/api/process/upload', {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${localStorage.getItem('hr121_token')}` },
          body: fd
        });
      } else if (url) {
        const fd = new FormData();
        fd.append('url', url);
        r = await fetch('/api/process/url', {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${localStorage.getItem('hr121_token')}` },
          body: fd
        });
      }

      if (!r || !r.ok) throw new Error('Upload failed');
      const data = await r.json();
      setTaskId(data.task_id);
    } catch (e) {
      console.error(e);
      setView('upload');
    }
  }

  function handleReset() {
    setView('upload');
    setWsData(null);
    setMainTab('form');
  }

  async function openReportFromHistory(id: string) {
    try {
      const r = await fetch(`/api/reports/${id}`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('hr121_token')}` }
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail);
      setWsData(data);
      setView('workspace');
      setMainTab('form');
    } catch (e: any) {
      alert(`Ошибка: ${e.message}`);
    }
  }

  if (!user) return <Login onLogin={setUser} />;

  return (
    <div className="shell">
      <div className="topbar">
        <div className="brand" onClick={() => setView('upload')} style={{ cursor: 'pointer' }}>HR 1-2-1</div>
        <div className="topbar-r" style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <button className="btn btn-s" onClick={() => setApiSettingsOpen(true)}>ИИ и API</button>
          <button className="btn btn-s" onClick={() => setSettingsOpen(true)}>Промты</button>
          <div className="user-pill">{user}</div>
          <button className="btn btn-g" onClick={logout}>Выйти</button>
        </div>
      </div>

      <div className="main-tabs" style={{ display: 'flex', gap: '1rem', padding: '1rem', background: 'var(--bg)' }}>
        <button className={`btn ${mainTab === 'form' ? 'btn-am' : 'btn-s'}`} onClick={() => setMainTab('form')}>Формирование отчёта</button>
        <button className={`btn ${mainTab === 'history' ? 'btn-am' : 'btn-s'}`} onClick={() => setMainTab('history')}>История</button>
      </div>

      <div className="main-area">
        {mainTab === 'form' && view === 'upload' && <UploadPage onProcess={handleProcess} />}
        {mainTab === 'form' && view === 'processing' && (
          <div className="processing-page">
            <div className="proc-box">
               <h3>Обработка записи…</h3>
               <p>Status: {procState.status}</p>
               <progress value={procState.progress} max="100" style={{ width: '100%' }} />
            </div>
          </div>
        )}
        {mainTab === 'form' && view === 'workspace' && wsData && <Workspace data={wsData} onReset={handleReset} />}
        {mainTab === 'history' && <History onOpen={openReportFromHistory} />}
      </div>
      {settingsOpen && <SettingsModal onClose={() => setSettingsOpen(false)} />}
      {apiSettingsOpen && <ApiSettingsModal onClose={() => setApiSettingsOpen(false)} />}
    </div>
  );
}

export default App;

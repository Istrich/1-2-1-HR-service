import { useState, useEffect, useRef } from 'react';

// Minimal types for demonstration; in a real app, define strictly based on API
interface ReportSegment {
  start: number;
  end: number;
  start_fmt: string;
  end_fmt: string;
  text: string;
}

interface WorkspaceData {
  session_id?: string;
  report_id?: string;
  title?: string;
  report: string;
  segments?: ReportSegment[];
  audio_file?: string;
}

interface WorkspaceProps {
  data: WorkspaceData;
  onReset: () => void;
}

function renderMd(text: string | null) {
  if (!text) return null;
  return text.split('\n').map((line, i) => {
    let s = line.trimStart();
    if (s.startsWith('### ')) return <h3 key={i} style={{ color: 'var(--tx)', fontSize: '.92rem', fontWeight: 600, margin: '.8rem 0 .25rem' }}>{s.slice(4)}</h3>;
    if (s.startsWith('## ')) return <h2 key={i} style={{ color: 'var(--tx)', fontSize: '1rem', fontWeight: 600, margin: '1rem 0 .3rem' }}>{s.slice(3)}</h2>;
    if (s.startsWith('# ')) return <h2 key={i} style={{ color: 'var(--tx)', fontSize: '1.05rem', fontWeight: 700, margin: '1.1rem 0 .3rem' }}>{s.slice(2)}</h2>;
    if (s.startsWith('- ') || s.startsWith('• ')) return <div key={i} style={{ paddingLeft: '1rem', position: 'relative', margin: '.15rem 0' }}><span style={{ position: 'absolute', left: 0, color: 'var(--am)' }}>·</span>{s.slice(2)}</div>;
    if (s === '') return <div key={i} style={{ height: '.5rem' }} />;
    if (/^[-*_]{3,}$/.test(s)) return <hr key={i} style={{ border: 'none', borderTop: '1px solid var(--brd)', margin: '.6rem 0' }} />;
    return <div key={i} style={{ margin: '.1rem 0' }}>{s}</div>;
  });
}

function AudioPlayer({ src, audioRef }: { src?: string; audioRef: React.RefObject<HTMLAudioElement | null> }) {
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const a = audioRef.current;
    if (!a) return;
    const onPlay = () => setPlaying(true);
    const onPause = () => setPlaying(false);
    const onTime = () => {
      const d = a.duration;
      if (d && isFinite(d) && d > 0) {
        setProgress((a.currentTime / d) * 100);
      }
    };
    a.addEventListener('play', onPlay);
    a.addEventListener('pause', onPause);
    a.addEventListener('timeupdate', onTime);
    return () => {
      a.removeEventListener('play', onPlay);
      a.removeEventListener('pause', onPause);
      a.removeEventListener('timeupdate', onTime);
    };
  }, [src, audioRef]);

  function toggle() {
    const a = audioRef.current;
    if (!a) return;
    playing ? a.pause() : a.play();
  }

  return (
    <div className="ws-audio">
      <audio ref={audioRef} src={src} preload="auto" playsInline />
      <button type="button" className="audio-play" onClick={toggle}>{playing ? '||' : '>'}</button>
      <div className="audio-track" style={{ height: 12, background: 'var(--bg-e)', flex: 1, position: 'relative' }}>
        <div className="audio-fill" style={{ width: `${progress}%`, height: '100%', background: 'var(--am)' }} />
      </div>
    </div>
  );
}

export function Workspace({ data, onReset }: WorkspaceProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [activeSeg, setActiveSeg] = useState(-1);
  const segments = data.segments || [];

  function seekTo(sec: number, idx: number) {
    const a = audioRef.current;
    if (!a) return;
    setActiveSeg(idx);
    a.currentTime = sec;
    a.play().catch(() => {});
  }

  const [report, setReport] = useState(data.report || '');
  const [refineText, setRefineText] = useState('');
  const [refining, setRefining] = useState(false);
  const [emailText, setEmailText] = useState('');
  const [loadingEmail, setLoadingEmail] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportLink, setExportLink] = useState('');

  useEffect(() => { setReport(data.report || ''); }, [data.report]);

  async function doRefine() {
    if (!refineText.trim()) return;
    setRefining(true);
    try {
      const r = await fetch('/api/refine', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('hr121_token')}`
        },
        body: JSON.stringify({ comment: refineText.trim(), current_report: report })
      });
      const d = await r.json();
      setReport(d.report);
      setRefineText('');
      setExportLink('');
    } catch (e: any) {
      alert(e.message);
    } finally {
      setRefining(false);
    }
  }

  async function doExport() {
    setExporting(true);
    try {
      const r = await fetch('/api/export/docx', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('hr121_token')}`
        },
        body: JSON.stringify({ report_text: report })
      });
      const d = await r.json();
      setExportLink(d.file);
    } catch (e: any) {
      alert(e.message);
    } finally {
      setExporting(false);
    }
  }

  async function doEmail() {
    setLoadingEmail(true);
    try {
      const r = await fetch('/api/email', {
        method: 'POST',
        headers: { Authorization: `Bearer ${localStorage.getItem('hr121_token')}` }
      });
      const d = await r.json();
      setEmailText(d.email_text);
    } catch (e: any) {
      alert(e.message);
    } finally {
      setLoadingEmail(false);
    }
  }

  return (
    <div className="workspace">
      <AudioPlayer src={data.audio_file} audioRef={audioRef} />

      <div className="panel" style={{ borderRight: '1px solid var(--brd)' }}>
        <div className="panel-head">
          <h3>Транскрипт</h3>
          <span className="badge">{segments.length} сегм.</span>
        </div>
        <div className="panel-body">
          {segments.map((seg, i) => (
            <div key={i} className={`seg${i === activeSeg ? ' active' : ''}`} onClick={() => seekTo(seg.start || 0, i)}>
              <span className="seg-time">{seg.start_fmt}</span>
              <span className="seg-text">{seg.text}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="panel">
        <div className="panel-head" style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <h3>{emailText ? 'Письмо' : 'Отчёт'}</h3>
          {data.title && !emailText && <span className="badge">{data.title}</span>}
          <div style={{ marginLeft: 'auto', display: 'flex', gap: '0.5rem' }}>
            {!emailText && <button className="btn btn-s" onClick={doEmail} disabled={loadingEmail}>{loadingEmail ? 'Генерация...' : 'Сгенерировать письмо'}</button>}
            <button className="btn btn-g" onClick={onReset}>Новая запись</button>
          </div>
        </div>
        <div className="report-body" style={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden' }}>
          <div className="report-scroll" style={{ flex: 1, overflowY: 'auto', padding: '1rem' }}>
            {emailText ? (
              <>
                <button className="btn btn-s" onClick={() => setEmailText('')} style={{ marginBottom: '1rem' }}>К отчёту</button>
                <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>{emailText}</div>
              </>
            ) : (
              <div className="report-content">{renderMd(report)}</div>
            )}
          </div>
          {!emailText && (
            <div style={{ borderTop: '1px solid var(--brd)', padding: '1rem', background: 'var(--bg-s)' }}>
              <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
                <input
                  type="text"
                  placeholder="Доработать отчёт через ИИ (например: 'Добавь раздел про риски')"
                  value={refineText}
                  onChange={e => setRefineText(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') doRefine(); }}
                  style={{ flex: 1 }}
                />
                <button className="btn btn-am" onClick={doRefine} disabled={refining || !refineText.trim()}>
                  {refining ? 'Отправка...' : 'Отправить'}
                </button>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button className="btn btn-gn" onClick={doExport} disabled={exporting}>
                  {exporting ? 'Выгрузка...' : 'Выгрузить в Word'}
                </button>
                {exportLink && <a href={exportLink} className="btn btn-s" download>Скачать .docx</a>}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

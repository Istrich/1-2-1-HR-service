import { useState, useRef } from 'react';

interface UploadPageProps {
  onProcess: (data: { type: 'file' | 'url'; file?: File; url?: string }) => void;
}

export function UploadPage({ onProcess }: UploadPageProps) {
  const [over, setOver] = useState(false);
  const [url, setUrl] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);

  function handleFile(f?: File) {
    if (f) onProcess({ type: 'file', file: f });
  }

  function handleUrl() {
    if (url.trim()) onProcess({ type: 'url', url: url.trim() });
  }

  return (
    <div className="upload-page">
      <div className="upload-container">
        <h2>Загрузите запись</h2>
        <p className="sub">Аудио или видео 1-2-1 интервью — получите транскрипцию и аналитический отчёт</p>
        <div
          className={`drop-zone${over ? ' over' : ''}`}
          onDragOver={e => { e.preventDefault(); setOver(true); }}
          onDragLeave={() => setOver(false)}
          onDrop={e => { e.preventDefault(); setOver(false); handleFile(e.dataTransfer?.files?.[0]); }}
          onClick={() => fileRef.current?.click()}
        >
          <input ref={fileRef} type="file" accept="audio/*,video/*" onChange={e => { handleFile(e.target.files?.[0]); e.target.value = ''; }} />
          <h3>Перетащите файл или нажмите для выбора</h3>
          <p>mp3, wav, ogg, m4a, mp4, webm и др.</p>
        </div>
        <div className="divider">или по ссылке</div>
        <div className="url-row">
          <input type="text" placeholder="https://drive.google.com/..." value={url} onChange={e => setUrl(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleUrl()} />
          <button className="btn btn-am" onClick={handleUrl} disabled={!url.trim()}>Обработать</button>
        </div>
      </div>
    </div>
  );
}

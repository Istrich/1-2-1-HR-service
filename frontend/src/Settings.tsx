import { useState, useEffect } from 'react';

export function SettingsModal({ onClose }: { onClose: () => void }) {
  const [rp, setRp] = useState('');
  const [ep, setEp] = useState('');
  const [drp, setDrp] = useState('');
  const [dep, setDep] = useState('');
  const [saving, setSaving] = useState('');
  const [msg, setMsg] = useState('');

  useEffect(() => {
    fetch('/api/prompts', {
      headers: { Authorization: `Bearer ${localStorage.getItem('hr121_token')}` }
    })
      .then(r => r.json())
      .then(d => {
        setRp(d.report_prompt);
        setEp(d.email_prompt);
        setDrp(d.default_report_prompt);
        setDep(d.default_email_prompt);
      });
  }, []);

  async function save(type: string, text: string) {
    setSaving(type);
    await fetch('/api/prompts', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('hr121_token')}`
      },
      body: JSON.stringify({ prompt_type: type, text })
    });
    setSaving('');
    setMsg('Сохранено');
    setTimeout(() => setMsg(''), 2000);
  }

  async function reset(type: string) {
    const t = type === 'report' ? drp : dep;
    type === 'report' ? setRp(t) : setEp(t);
    await fetch('/api/prompts/reset', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('hr121_token')}`
      },
      body: JSON.stringify({ prompt_type: type, text: '' })
    });
    setMsg('Сброшено');
    setTimeout(() => setMsg(''), 2000);
  }

  return (
    <div className="overlay-bg" onClick={onClose} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.55)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 500 }}>
      <div className="overlay-box" onClick={e => e.stopPropagation()} style={{ background: 'var(--bg-s)', width: '100%', maxWidth: '640px', padding: '2rem', borderRadius: 'var(--r2)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <h2>Настройка промтов</h2>
          <button className="btn btn-g" onClick={onClose}>Закрыть</button>
        </div>
        {msg && <div style={{ color: 'var(--gn)', marginBottom: '1rem' }}>{msg}</div>}
        <div style={{ marginBottom: '1rem' }}>
          <h4>Промт для отчёта</h4>
          <textarea style={{ width: '100%', minHeight: '150px', background: 'var(--bg)', color: 'var(--tx)', padding: '0.5rem' }} value={rp} onChange={e => setRp(e.target.value)} />
          <button className="btn btn-am" onClick={() => save('report', rp)} disabled={saving === 'report'}>Сохранить</button>
          <button className="btn btn-s" onClick={() => reset('report')} style={{ marginLeft: '1rem' }}>Сбросить</button>
        </div>
        <div>
          <h4>Промт для письма</h4>
          <textarea style={{ width: '100%', minHeight: '100px', background: 'var(--bg)', color: 'var(--tx)', padding: '0.5rem' }} value={ep} onChange={e => setEp(e.target.value)} />
          <button className="btn btn-am" onClick={() => save('email', ep)} disabled={saving === 'email'}>Сохранить</button>
          <button className="btn btn-s" onClick={() => reset('email')} style={{ marginLeft: '1rem' }}>Сбросить</button>
        </div>
      </div>
    </div>
  );
}

export function ApiSettingsModal({ onClose }: { onClose: () => void }) {
  const [msg, setMsg] = useState('');
  const [reportAi, setReportAi] = useState('openai');
  const [whisperBack, setWhisperBack] = useState('local');
  const [whisperModel, setWhisperModel] = useState('small');
  const [openaiReportModel, setOpenaiReportModel] = useState('gpt-4o');
  const [openaiKey, setOpenaiKey] = useState('');
  const [deepseekKey, setDeepseekKey] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetch('/api/settings/runtime', {
      headers: { Authorization: `Bearer ${localStorage.getItem('hr121_token')}` }
    })
      .then(r => r.json())
      .then(d => {
        setReportAi(d.report_ai_provider || 'openai');
        setWhisperBack(d.whisper_backend || 'local');
        setWhisperModel(d.whisper_model || 'small');
        setOpenaiReportModel(d.openai_report_model || 'gpt-4o');
      });
  }, []);

  async function saveAll() {
    setSaving(true);
    try {
      const body: any = {
        report_ai_provider: reportAi,
        whisper_backend: whisperBack,
        whisper_model: whisperModel,
        openai_report_model: openaiReportModel,
      };
      if (openaiKey.trim()) body.openai_api_key = openaiKey.trim();
      if (deepseekKey.trim()) body.deepseek_api_key = deepseekKey.trim();

      const r = await fetch('/api/settings/runtime', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('hr121_token')}`
        },
        body: JSON.stringify(body)
      });
      if (!r.ok) throw new Error('Ошибка сохранения');
      setMsg('Сохранено');
      setTimeout(() => setMsg(''), 2500);
    } catch (e: any) {
      setMsg(e.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="overlay-bg" onClick={onClose} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.55)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 500 }}>
      <div className="overlay-box" onClick={e => e.stopPropagation()} style={{ background: 'var(--bg-s)', width: '100%', maxWidth: '520px', padding: '2rem', borderRadius: 'var(--r2)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <h2>ИИ и API</h2>
          <button className="btn btn-g" onClick={onClose}>Закрыть</button>
        </div>
        {msg && <div style={{ color: 'var(--gn)', marginBottom: '1rem' }}>{msg}</div>}

        <div style={{ marginBottom: '1rem' }}>
          <label style={{ display: 'block' }}>Транскрипция: {whisperBack}</label>
          <input type="text" value={whisperModel} onChange={e => setWhisperModel(e.target.value)} />
        </div>
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ display: 'block' }}>Модель OpenAI: {openaiReportModel}</label>
          <input type="text" value={openaiReportModel} onChange={e => setOpenaiReportModel(e.target.value)} />
        </div>
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ display: 'block' }}>OpenAI Key (Новый)</label>
          <input type="password" value={openaiKey} onChange={e => setOpenaiKey(e.target.value)} />
        </div>
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ display: 'block' }}>DeepSeek Key (Новый)</label>
          <input type="password" value={deepseekKey} onChange={e => setDeepseekKey(e.target.value)} />
        </div>

        <button className="btn btn-am" onClick={saveAll} disabled={saving}>Сохранить</button>
      </div>
    </div>
  );
}

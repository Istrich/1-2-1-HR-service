import { useState } from 'react';

interface LoginProps {
  onLogin: (username: string) => void;
}

export function Login({ onLogin }: LoginProps) {
  const [u, setU] = useState('');
  const [p, setP] = useState('');
  const [err, setErr] = useState('');
  const [ld, setLd] = useState(false);

  async function go(e: React.FormEvent) {
    e.preventDefault();
    setErr('');
    setLd(true);
    try {
      const r = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: u, password: p })
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || 'Ошибка авторизации');

      localStorage.setItem('hr121_token', data.token);
      localStorage.setItem('hr121_user', data.username);
      onLogin(data.username);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setLd(false);
    }
  }

  return (
    <div className="login-wrap">
      <form className="login-box" onSubmit={go}>
        <div className="logo">
          <h1>HR 1-2-1</h1>
          <p>аналитика интервью</p>
        </div>
        <div className="fld">
          <label>Логин</label>
          <input type="text" value={u} onChange={e => setU(e.target.value)} autoFocus />
        </div>
        <div className="fld">
          <label>Пароль</label>
          <input type="password" value={p} onChange={e => setP(e.target.value)} />
        </div>
        <button className="btn btn-am btn-full" disabled={ld}>
          {ld ? <span className="spinner" /> : 'Войти'}
        </button>
        {err && <div className="err">{err}</div>}
      </form>
    </div>
  );
}

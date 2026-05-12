import { useState, useEffect } from 'react';

export function History({ onOpen }: { onOpen: (id: string) => void }) {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch('/api/reports', {
          headers: { 'Authorization': `Bearer ${localStorage.getItem('hr121_token')}` }
        });
        const d = await r.json();
        setItems(d.items || []);
      } catch (e) {
        setItems([]);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <div className="history-page">
      <h2>История отчётов</h2>
      <div className="history-list">
        {!loading && items.length === 0 && <div className="history-empty">Нет сохранённых отчётов.</div>}
        {items.map((it) => (
          <div key={it.id} className="history-row" onClick={() => onOpen(it.id)}>
            <div className="history-row-main">
              <div className="history-row-title">{it.title || 'Без названия'}</div>
            </div>
            <div className="history-row-actions">
              <button type="button" className="btn btn-s">Открыть</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

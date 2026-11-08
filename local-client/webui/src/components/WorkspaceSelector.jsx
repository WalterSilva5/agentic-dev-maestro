import { useEffect, useState } from 'react';
import { getWorkspaces, setActiveWorkspace, createWorkspace } from '../api';
import { t } from '../i18n';

export default function WorkspaceSelector() {
  const [workspaces, setWorkspaces] = useState([]);
  const [active, setActive] = useState('');

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const data = await getWorkspaces();
        if (!mounted) return;
        setWorkspaces(data.workspaces || []);
        setActive(data.active || '');
      } catch (err) {
        console.error('Failed to load workspaces', err);
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const handleChange = async (e) => {
    const id = e.target.value;
    setActive(id);
    try {
      await setActiveWorkspace(id);
      window.location.reload();
    } catch (err) {
      console.error('Failed to set active workspace', err);
    }
  };

  const handleCreate = async () => {
    const name = window.prompt(t('Nome do novo workspace:'));
    if (!name || !name.trim()) return;
    const icon = window.prompt(t('Ícone (emoji, opcional):'), '📁') || '📁';
    try {
      const ws = await createWorkspace({ name: name.trim(), icon: icon.trim() || '📁' });
      // Torna o novo workspace ativo e recarrega
      await setActiveWorkspace(ws.id);
      window.location.reload();
    } catch (e) {
      window.alert(e.response?.data?.detail || String(e.message || e));
    }
  };

  return (
    <div style={{ padding: '8px 16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <label style={{ fontSize: '11px', color: 'var(--muted)' }}>{t('WORKSPACE')}</label>
        <button
          onClick={handleCreate}
          title={t('Novo workspace')}
          style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--muted)', borderRadius: 6, padding: '2px 6px', fontSize: 12, cursor: 'pointer' }}
        >
          +
        </button>
      </div>
      <select style={{ width: '100%' }} value={active} onChange={handleChange}>
        {workspaces.map((ws) => (
          <option key={ws.id} value={ws.id}>
            {ws.icon ? `${ws.icon} ${ws.name}` : ws.name}
          </option>
        ))}
      </select>
    </div>
  );
}

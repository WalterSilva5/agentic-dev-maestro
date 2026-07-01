import { useEffect, useState } from 'react';
import { getWorkspaces, setActiveWorkspace } from '../api';
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

  return (
    <div style={{ padding: '8px 16px' }}>
      <label
        style={{
          display: 'block',
          fontSize: '11px',
          color: 'var(--muted)',
          marginBottom: '4px',
        }}
      >
        {t('WORKSPACE')}
      </label>
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

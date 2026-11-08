import { useEffect, useState } from 'react';
import Swal from 'sweetalert2';
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
    const { value: name } = await Swal.fire({
      title: t('Novo workspace'),
      input: 'text',
      inputLabel: t('Nome do novo workspace:'),
      inputPlaceholder: 'Ex: Migração GX',
      showCancelButton: true,
      confirmButtonText: t('Criar'),
      cancelButtonText: t('Cancelar'),
      inputValidator: (v) => (!v || !v.trim() ? t('Informe um nome') : null),
    });
    if (!name) return;
    const { value: icon } = await Swal.fire({
      title: t('Ícone (emoji, opcional):'),
      input: 'text',
      inputPlaceholder: '📁',
      inputValue: '📁',
      showCancelButton: true,
      confirmButtonText: t('Criar'),
      cancelButtonText: t('Cancelar'),
    });
    try {
      const ws = await createWorkspace({ name: name.trim(), icon: (icon || '📁').trim() || '📁' });
      await setActiveWorkspace(ws.id);
      window.location.reload();
    } catch (e) {
      Swal.fire({ icon: 'error', title: t('Erro'), text: e.response?.data?.detail || String(e.message || e) });
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

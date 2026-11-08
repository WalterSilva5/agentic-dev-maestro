import { useEffect, useState } from 'react';
import Swal from 'sweetalert2';
import { getWorkspaces, setActiveWorkspace, createWorkspace } from '../api';
import MenuSelect from './MenuSelect.jsx';
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

  const handleChange = async (id) => {
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
    <MenuSelect
      label={t('WORKSPACE')}
      value={active}
      placeholder={t('Selecione um workspace')}
      options={workspaces.map((ws) => ({
        value: ws.id,
        label: ws.name,
        icon: ws.icon || '📁',
        hint: ws.description || '',
      }))}
      onChange={handleChange}
      onCreate={handleCreate}
      createTitle={t('Novo workspace')}
      emptyHint={t('Nenhum workspace')}
    />
  );
}

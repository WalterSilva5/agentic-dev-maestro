import { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import Swal from 'sweetalert2';
import { getProjects, createProject, getWorkspaces } from '../api';
import MenuSelect from './MenuSelect.jsx';
import { t } from '../i18n';

const STORAGE_KEY = 'maestro.activeProjectByWs';

function getActiveProjectId(wsId) {
  try {
    const map = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
    return map[wsId] || null;
  } catch { return null; }
}
function setActiveProjectId(wsId, projectId) {
  try {
    const map = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
    if (projectId) map[wsId] = String(projectId);
    else delete map[wsId];
    localStorage.setItem(STORAGE_KEY, JSON.stringify(map));
  } catch {}
}

export default function ProjectSelector() {
  const [projects, setProjects] = useState([]);
  const [workspaces, setWorkspaces] = useState([]);
  const [activeWs, setActiveWs] = useState('');
  const [activeProject, setActiveProject] = useState('');
  const nav = useNavigate();
  const location = useLocation();

  useEffect(() => {
    getWorkspaces().then((data) => {
      const ws = data.workspaces || [];
      const active = data.active || ws[0]?.id || '';
      setWorkspaces(ws);
      setActiveWs(active);
      const pid = getActiveProjectId(active);
      if (pid) setActiveProject(pid);
    }).catch(() => {});
    getProjects().then(setProjects).catch(() => {});
  }, []);

  // Quando navega para um board, atualiza o ativo
  useEffect(() => {
    const m = location.pathname.match(/\/board\/(\d+)/);
    if (m) {
      const pid = m[1];
      if (activeWs) setActiveProjectId(activeWs, pid);
      setActiveProject(pid);
    }
  }, [location.pathname, activeWs]);

  const handleChange = (pid) => {
    setActiveProject(pid);
    if (activeWs) setActiveProjectId(activeWs, pid);
    if (pid) nav(`/board/${pid}`);
  };

  const handleCreate = async () => {
    const { value: name } = await Swal.fire({
      title: t('Novo projeto'),
      input: 'text',
      inputLabel: t('Nome do novo projeto:'),
      inputPlaceholder: 'Ex: Migração GX',
      showCancelButton: true,
      confirmButtonText: t('Criar'),
      cancelButtonText: t('Cancelar'),
      inputValidator: (v) => (!v || !v.trim() ? t('Informe um nome') : null),
    });
    if (!name) return;
    const suggested = name.trim().slice(0,4).toUpperCase().replace(/[^A-Z0-9]/g,'');
    const { value: key } = await Swal.fire({
      title: t('Chave (ex: DEMO):'),
      input: 'text',
      inputValue: suggested,
      inputPlaceholder: 'DEMO',
      showCancelButton: true,
      confirmButtonText: t('Criar'),
      cancelButtonText: t('Cancelar'),
      inputValidator: (v) => (!v || !v.trim() ? t('Informe uma chave') : null),
    });
    if (!key) return;
    try {
      const p = await createProject({ name: name.trim(), key: key.trim().toUpperCase() });
      setProjects((prev) => [...prev, p]);
      if (activeWs) setActiveProjectId(activeWs, String(p.id));
      setActiveProject(String(p.id));
      nav(`/board/${p.id}`);
    } catch (e) {
      Swal.fire({ icon: 'error', title: t('Erro'), text: e.response?.data?.detail || String(e.message || e) });
    }
  };

  // O web só vê o workspace ativo, então todos os projetos listados são dele.
  return (
    <>
      <MenuSelect
        label={t('PROJETO ATUAL')}
        value={activeProject}
        placeholder={t('Selecione um projeto')}
        options={projects.map((p) => ({
          value: String(p.id),
          label: p.name,
          badge: p.key,
          hint: (p.description || '').trim(),
        }))}
        onChange={handleChange}
        onCreate={handleCreate}
        createTitle={t('Novo projeto')}
        emptyHint={t('Nenhum projeto neste workspace')}
      />
      {projects.length > 0 && !activeProject && (
        <div className="msel-dica">{t('Escolha um projeto para abrir o board em 1 clique.')}</div>
      )}
    </>
  );
}
export { getActiveProjectId, setActiveProjectId };

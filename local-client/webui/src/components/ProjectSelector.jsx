import { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { getProjects, createProject, getWorkspaces } from '../api';
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

  const handleChange = (e) => {
    const pid = e.target.value;
    setActiveProject(pid);
    if (activeWs) setActiveProjectId(activeWs, pid);
    if (pid) nav(`/board/${pid}`);
  };

  const handleCreate = async () => {
    const name = window.prompt(t('Nome do novo projeto:'));
    if (!name || !name.trim()) return;
    let key = window.prompt(t('Chave (ex: DEMO):'), name.trim().slice(0,4).toUpperCase().replace(/[^A-Z0-9]/g,''));
    if (!key || !key.trim()) return;
    key = key.trim().toUpperCase();
    try {
      const p = await createProject({ name: name.trim(), key });
      setProjects((prev) => [...prev, p]);
      if (activeWs) setActiveProjectId(activeWs, String(p.id));
      setActiveProject(String(p.id));
      nav(`/board/${p.id}`);
    } catch (e) {
      window.alert(e.response?.data?.detail || String(e.message || e));
    }
  };

  // Filtra projetos do workspace atual (todos os projetos pertencem ao workspace ativo no web, que é o DB do workspace)
  // Como o web só vê o workspace ativo, todos os projetos listados são do workspace atual
  return (
    <div style={{ padding: '8px 16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <label style={{ fontSize: '11px', color: 'var(--muted)' }}>{t('PROJETO ATUAL')}</label>
        <button
          onClick={handleCreate}
          title={t('Novo projeto')}
          style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--muted)', borderRadius: 6, padding: '2px 6px', fontSize: 12, cursor: 'pointer' }}
        >
          +
        </button>
      </div>
      <select style={{ width: '100%' }} value={activeProject} onChange={handleChange}>
        <option value="">{t('Selecione um projeto')}</option>
        {projects.map((p) => (
          <option key={p.id} value={p.id}>
            {p.key} · {p.name}
          </option>
        ))}
      </select>
      {projects.length > 0 && !activeProject && (
        <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 4 }}>{t('Escolha um projeto para abrir o board em 1 clique.')}</div>
      )}
    </div>
  );
}
export { getActiveProjectId, setActiveProjectId };

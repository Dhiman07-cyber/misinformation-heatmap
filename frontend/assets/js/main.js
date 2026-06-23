import { mountNavbar } from './components/navbar.js';
import { initDashboard } from './pages/dashboard.js';
import { initHeatmap } from './pages/heatmap.js';
import { initHome } from './pages/home.js';

const PAGE_INIT = {
  heatmap: initHeatmap,
  dashboard: initDashboard,
  home: initHome,
  contact: () => { console.log('[contact] initialized'); }
};

document.addEventListener('DOMContentLoaded', () => {
  const page = document.body?.dataset?.page || 'home';
  mountNavbar({
    page,
    statusId: `${page}-nav-status`,
    initialStatus: 'Checking'
  });

  const init = PAGE_INIT[page];
  if (!init) return;

  Promise.resolve()
    .then(() => init())
    .catch((error) => {
      console.error(`[${page}] initialization failed:`, error);
    });
});

(() => {
  const picker = document.querySelector('#theme');
  const root = document.documentElement;
  const key = 'amdl-pages-theme';
  const apply = (choice) => {
    const theme = choice === 'light' || choice === 'dark' ? choice : 'system';
    if (theme === 'system') delete root.dataset.theme;
    else root.dataset.theme = theme;
    picker.value = theme;
    return theme;
  };
  let saved;
  try { saved = localStorage.getItem(key); } catch { /* Depolama isteğe bağlıdır. */ }
  apply(saved);
  picker.closest('.theme').hidden = false;
  picker.addEventListener('change', () => {
    const theme = apply(picker.value);
    try { localStorage.setItem(key, theme); } catch { /* Tema bu sekmede çalışmaya devam eder. */ }
  });
})();

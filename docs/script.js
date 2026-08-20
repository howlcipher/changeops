/**
 * Howl Ecosystem Shared Client Script - ChangeOps
 */

document.addEventListener('DOMContentLoaded', () => {
  const themeToggleBtn = document.getElementById('theme-toggle');
  const root = document.documentElement;

  const getPreferredTheme = () => {
    const saved = localStorage.getItem('howl-theme');
    if (saved) return saved;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  };

  const applyTheme = (theme) => {
    if (theme === 'dark') {
      root.setAttribute('data-theme', 'dark');
      document.body.classList.remove('light-mode');
    } else {
      root.removeAttribute('data-theme');
      document.body.classList.add('light-mode');
    }

    if (themeToggleBtn) {
      themeToggleBtn.setAttribute('aria-pressed', String(theme === 'dark'));
      themeToggleBtn.innerHTML = theme === 'dark'
        ? '<span aria-hidden="true">☼</span> [LIGHT_MODE]'
        : '<span aria-hidden="true">☾</span> [DARK_MODE]';
    }
  };

  const initialTheme = getPreferredTheme();
  applyTheme(initialTheme);

  if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', () => {
      const current = root.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
      const next = current === 'dark' ? 'light' : 'dark';
      localStorage.setItem('howl-theme', next);
      applyTheme(next);
    });
  }

  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    if (!localStorage.getItem('howl-theme')) {
      applyTheme(e.matches ? 'dark' : 'light');
    }
  });

  // Code Copy Buttons
  document.querySelectorAll('.code-container').forEach((container) => {
    const copyBtn = container.querySelector('.btn-copy');
    const codeEl = container.querySelector('pre code') || container.querySelector('pre');
    
    if (copyBtn && codeEl) {
      copyBtn.addEventListener('click', async () => {
        try {
          const text = codeEl.innerText.trim();
          await navigator.clipboard.writeText(text);
          const originalText = copyBtn.textContent;
          copyBtn.textContent = '[COPIED!]';
          copyBtn.style.borderColor = 'var(--color-red)';
          copyBtn.style.color = 'var(--color-red)';
          setTimeout(() => {
            copyBtn.textContent = originalText;
            copyBtn.style.borderColor = '';
            copyBtn.style.color = '';
          }, 2000);
        } catch (err) {
          console.error('Failed to copy code snippet:', err);
        }
      });
    }
  });
});

document.addEventListener('DOMContentLoaded', () => {
    const themeToggleBtn = document.getElementById('theme-toggle');
    const body = document.body;

    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'light') {
        body.classList.add('light-mode');
    }

    const updateThemeControl = () => {
        const isLight = body.classList.contains('light-mode');
        themeToggleBtn.setAttribute('aria-pressed', String(isLight));
        themeToggleBtn.textContent = isLight
            ? 'Switch to dark theme'
            : 'Switch to light theme';
    };

    updateThemeControl();

    themeToggleBtn.addEventListener('click', () => {
        body.classList.toggle('light-mode');
        if (body.classList.contains('light-mode')) {
            localStorage.setItem('theme', 'light');
        } else {
            localStorage.setItem('theme', 'dark');
        }
        updateThemeControl();
    });

    const mainTitle = document.getElementById('main-title');
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (reducedMotion.matches) {
        return;
    }

    const originalText = mainTitle.innerText;
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%^&*()_+';
    let iterations = 0;

    const interval = setInterval(() => {
        mainTitle.innerText = originalText
            .split('')
            .map((letter, index) => {
                if (letter === ' ') return ' ';

                if (index < iterations) {
                    return originalText[index];
                }
                return chars[Math.floor(Math.random() * chars.length)];
            })
            .join('');

        if (iterations >= originalText.length) {
            clearInterval(interval);
        }

        iterations += 1 / 3;
    }, 30);
});

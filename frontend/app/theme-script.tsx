export function ThemeScript() {
    const themeScript = `
    try {
      const theme = localStorage.getItem('theme') || 'light';
      if (theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }
    } catch (e) {}
  `;

    return (
        <script
            dangerouslySetInnerHTML={{ __html: themeScript }}
            suppressHydrationWarning
        />
    );
}

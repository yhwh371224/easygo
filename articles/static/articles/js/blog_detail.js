  // Reading progress bar
  window.addEventListener('scroll', () => {
    const doc = document.documentElement;
    const scrollTop = doc.scrollTop || document.body.scrollTop;
    const scrollHeight = doc.scrollHeight - doc.clientHeight;
    const pct = scrollHeight > 0 ? (scrollTop / scrollHeight) * 100 : 0;
    document.getElementById('readProgress').style.width = pct + '%';
  });

  // Auto TOC from h2 tags
  (function buildTOC() {
    const body = document.getElementById('articleBody');
    const tocList = document.getElementById('tocList');
    const tocBox = document.getElementById('tocBox');
    if (!body || !tocList) return;
    const headings = body.querySelectorAll('h2');
    if (headings.length < 2) return;
    headings.forEach((h, i) => {
      const id = 'section-' + i;
      h.id = id;
      const li = document.createElement('li');
      const a = document.createElement('a');
      a.href = '#' + id;
      a.textContent = h.textContent;
      a.addEventListener('click', e => {
        e.preventDefault();
        document.getElementById(id).scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
      li.appendChild(a);
      tocList.appendChild(li);
    });
    tocBox.style.display = 'block';
  })();

  // Copy link
  function copyLink(btn) {
    navigator.clipboard.writeText(window.location.href).then(() => {
      btn.classList.add('copied');
      btn.textContent = '✅ Copied!';
      setTimeout(() => {
        btn.classList.remove('copied');
        btn.textContent = '🔗 Copy link';
      }, 2000);
    });
  }
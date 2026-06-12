/**
 * Documentation — Simulateur Capacité-Commande
 * Interactivité & Dynamisme (Vanilla JS)
 */

document.addEventListener('DOMContentLoaded', () => {
  // ─── TOC ACTIVE LINK ON SCROLL ──────────────────────────────────────────
  const sections = document.querySelectorAll('section.doc-section, div[id]');
  const tocLinks = document.querySelectorAll('.toc-link');

  const observerOptions = {
    root: null,
    rootMargin: '-20% 0px -60% 0px',
    threshold: 0
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const id = entry.target.getAttribute('id');
        if (!id) return;
        
        tocLinks.forEach(link => {
          if (link.getAttribute('href') === `#${id}`) {
            link.classList.add('active');
          } else {
            link.classList.remove('active');
          }
        });
      }
    });
  }, observerOptions);

  sections.forEach(section => observer.observe(section));


  // ─── NAVBAR SCROLL EFFECT ───────────────────────────────────────────────
  const navbar = document.getElementById('navbar');
  window.addEventListener('scroll', () => {
    if (window.scrollY > 50) {
      navbar.style.background = 'rgba(11, 15, 25, 0.95)';
      navbar.style.boxShadow = '0 10px 30px -10px rgba(0,0,0,0.5)';
      navbar.style.padding = '0.5rem 2rem';
      navbar.style.height = '60px';
    } else {
      navbar.style.background = 'rgba(11, 15, 25, 0.8)';
      navbar.style.boxShadow = 'none';
      navbar.style.padding = '0 2rem';
      navbar.style.height = '70px';
    }
  });


  // ─── INTERACTIVE MOCK ELEMENT INTERACTIONS ──────────────────────────────
  // Adding small tooltip or status message on clicking mockup components
  const mockCells = document.querySelectorAll('.hm-cell');
  mockCells.forEach(cell => {
    cell.addEventListener('click', () => {
      const parentLabel = cell.parentElement.querySelector('.hm-row-label').textContent;
      const colIndex = Array.from(cell.parentElement.children).indexOf(cell);
      const week = ['S1', 'S2', 'S3', 'S4'][colIndex - 1];
      const tonnage = cell.textContent;
      
      showNotification(`Ligne ${parentLabel} | ${week} : ${tonnage} Tonnes planifiées`);
    });
  });

  const barSegments = document.querySelectorAll('.bar-seg');
  barSegments.forEach(seg => {
    seg.addEventListener('click', () => {
      const family = seg.getAttribute('title') || 'Produit';
      showNotification(`Famille ${family} sélectionnée (détails filtrés dans l'application)`);
    });
  });


  // ─── NOTIFICATION UTILITY ──────────────────────────────────────────────
  function showNotification(message) {
    // Check if notification already exists
    let toast = document.getElementById('doc-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'doc-toast';
      Object.assign(toast.style, {
        position: 'fixed',
        bottom: '2rem',
        right: '2rem',
        background: 'rgba(30, 41, 59, 0.9)',
        border: '1px solid rgba(59, 130, 246, 0.3)',
        color: '#f8fafc',
        padding: '0.75rem 1.5rem',
        borderRadius: '8px',
        fontSize: '0.85rem',
        fontWeight: '500',
        zIndex: 10000,
        backdropFilter: 'blur(8px)',
        boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.3)',
        transition: 'opacity 0.3s, transform 0.3s',
        opacity: '0',
        transform: 'translateY(20px)'
      });
      document.body.appendChild(toast);
    }
    
    toast.textContent = message;
    toast.style.opacity = '1';
    toast.style.transform = 'translateY(0)';
    
    // Auto-hide after 3 seconds
    if (window.toastTimeout) clearTimeout(window.toastTimeout);
    window.toastTimeout = setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(20px)';
    }, 3000);
  }
});

/* Tiroir de filtres (tablette et téléphone).
   Au-dessus de 1024px le bouton est masqué en CSS et ce script ne sert à
   rien : c'est la media query qui décide, pas le JS.
   Chargé sur toutes les pages, d'où les gardes en tête. */
(function () {
    const page = document.querySelector('.vo-list');
    if (!page) return;

    const bouton = page.querySelector('.sb-toggle');
    const overlay = page.querySelector('.sb-overlay');
    if (!bouton) return;

    function basculer(ouvert) {
        page.classList.toggle('filtres-ouverts', ouvert);
        bouton.setAttribute('aria-expanded', ouvert ? 'true' : 'false');
    }

    bouton.addEventListener('click', function () {
        basculer(!page.classList.contains('filtres-ouverts'));
    });

    if (overlay) {
        overlay.addEventListener('click', function () { basculer(false); });
    }

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') basculer(false);
    });
})();

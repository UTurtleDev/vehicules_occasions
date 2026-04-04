document.addEventListener('DOMContentLoaded', function() {

    const champs = ['prix_vehicule', 'prix_enchere', 'prix_transport'];

    function calculer() {
        let total = 0;
        champs.forEach(function(champ) {
            let valeur = parseFloat(document.getElementById('id_' + champ).value) || 0;
            total += valeur;
        });
        document.querySelector('.field-prix_achat .readonly').textContent = total.toFixed(2) + ' €';
    }

    champs.forEach(function(champ) {
        document.getElementById('id_' + champ).addEventListener('input', calculer);
    });

});
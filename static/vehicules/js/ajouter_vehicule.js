const marqueSelect = document.getElementById('id_marque');
const modeleSelect = document.getElementById('id_modele');
const allModeleOptions = Array.from(modeleSelect.options);

function filtrerModeles() {
    const marqueId = marqueSelect.value;
    allModeleOptions.forEach(function(opt) {
        if (opt.value === '' || opt.value === '__nouveau__') return;
        opt.hidden = marqueId !== '' && opt.dataset.marque !== marqueId;
    });
    if (modeleSelect.selectedOptions[0] && modeleSelect.selectedOptions[0].hidden) {
        modeleSelect.value = '';
    }
}

marqueSelect.addEventListener('change', function() {
    if (marqueSelect.value === '__nouveau__') {
        document.getElementById('champ-nouvelle-marque').hidden = false;
        marqueSelect.value = '';
    } else {
        document.getElementById('champ-nouvelle-marque').hidden = true;
    }
    filtrerModeles();
});

modeleSelect.addEventListener('change', function() {
    if (modeleSelect.value === '__nouveau__') {
        document.getElementById('champ-nouveau-modele').hidden = false;
        modeleSelect.value = '';
    } else {
        document.getElementById('champ-nouveau-modele').hidden = true;
    }
});

filtrerModeles();

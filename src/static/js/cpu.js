function loadSubSectionData(section) {
    fetch(`/cpu/${section}`)
        .then(response => response.text())
        .then(data => {
            document.getElementById(`${section}-section`).innerHTML = data;
        })
        .catch(error => console.error('Erro ao carregar a subseção:', error));
}

let isRunning = false;

function sendDebugCommand(command) {
    if (isRunning) { 
        console.log(`Não foi possível executar o comando ${command} porque um outro comando já está rodando`); 
        return false
    }

    updateStatus(true); // Atualiza para "Running"

    const instanceId = getSessionCookie(); 

    fetch(`/recive_command/${instanceId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: `command=${encodeURIComponent(command)}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === "success") {
            console.log("Comando executado com sucesso:", data.output);
        } else if (data.status === "error") {
            console.error("Erro ao executar comando:", data.output);
        } else if (data.status === "running") {
            console.log("Comando em execução:", data.output);
        } else {
            console.warn("Status indefinido:", data.output);
        }

        updateStatus(false); // Atualiza para "Paused"
        activeSubsections.forEach((subsectionName) => {
            loadSectionData(actualSection, subsectionName);
        });
        return true
    })
    .catch(error => {
        console.error("Erro ao enviar comando:", error);
        updateStatus(false); // Atualiza para "Paused"
    });

}


function toggleBreakpoint(addressElement) {
  const address = addressElement.getAttribute('data-address');
  const action = addressElement.classList.contains('breakpoint') ? 'DELETE' : 'POST';

  sendBreakpointCommand(action, address, function(success) {
      if (success) {
          addressElement.classList.toggle('breakpoint');
      }
  });
}

function sendBreakpointCommand(action, address, callback) {
    const instanceId = getSessionCookie();
    fetch(`/breakpoints/${instanceId}`, {
        method: action,
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ breakpoint: address })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            console.log(`Breakpoint ${action === 'POST' ? 'added' : 'removed'} at address ${address}`);
            callback(true);
        } else {
            console.error(`Failed to ${action === 'POST' ? 'add' : 'remove'} breakpoint at address ${address}`);
            callback(false);
        }
    })
    .catch(error => {
        console.error('Error managing breakpoint:', error);
        callback(false);
    });
  }

function restartGDB() {
    const commansSuccess = sendDebugCommand('restart')
    if (commansSuccess) {
        window.location.reload()
    }
}

function updateStatus(newRunninngStatus) {
    const statusBox = document.getElementById('status-box');
    const statusText = document.getElementById('status-text');
    isRunning = newRunninngStatus
    if (isRunning) {
        statusBox.style.backgroundColor = '#dc3545'; // Vermelho para running
        statusText.textContent = 'Running';
    } else {
        statusBox.style.backgroundColor = '#28a745'; // Verde para pausado
        statusText.textContent = 'Paused';
    }
}

function loadDisassemblyForFunction(functionName) {
    const instanceId = getSessionCookie();
    const url = `/section/cpu/${instanceId}/disassembly?function=${encodeURIComponent(functionName)}`;

    fetch(url)
        .then(response => response.json())
        .then(data => {
            // Atualiza a seção CPU e o disassembly com a nova função
            renderSection('cpu');
            setTimeout(() => renderDisassembly(data), 500); // Pequeno delay para garantir que o HTML foi carregado
        })
        .catch(error => console.error('Erro ao carregar o disassembly:', error));
}

function goToAddress() {
    const address = document.getElementById('goto-address').value;
    const negativeLines = document.getElementById('negative-lines').value || 0;
    const positiveLines = document.getElementById('positive-lines').value || 0;

    if (!address.startsWith("0x") || isNaN(parseInt(address, 16))) {
        alert("Please enter a valid hexadecimal address (e.g., 0x400080).");
        return;
    }

    const instanceId = getSessionCookie();
    const url = `/section/cpu/${instanceId}/disassembly?address=${encodeURIComponent(address)}&neg=${negativeLines}&pos=${positiveLines}`;

    fetch(url)
        .then(response => response.json())
        .then(data => {
            renderDisassembly(data);
        })
        .catch(error => console.error('Erro ao carregar o disassembly:', error));
}
let isRunning = false;

function sendDebugCommand(command) {
    if (isRunning) {
        return console.log(`Não foi possível executar o comando ${command} porque outro comando já está em execução`);
    }
    isRunning = true;

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
        
        isRunning = false;
        actualSection = getCookie("section_name")
        activeSubsections.forEach((subsectionName) => {
            loadSectionData(actualSection, subsectionName);
        });
    })
    .catch(error => {
        console.error("Erro ao enviar comando:", error);
        isRunning = false;
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
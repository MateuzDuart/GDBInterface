document.addEventListener('keydown', function(event) {
    if (event.ctrlKey && event.key === 'F10') {
        // Ctrl + F10 para stepi
        sendDebugCommand('stepi');
        event.preventDefault(); // Previne o comportamento padrão, se houver
    } else if (event.key === 'F10') {
        // F10 para step
        sendDebugCommand('step');
        event.preventDefault(); // Previne o comportamento padrão, se houver
    } else if (event.ctrlKey && event.key === 'F11') {
        // Ctrl + F11 para nexti
        sendDebugCommand('nexti');
        event.preventDefault(); // Previne o comportamento padrão, se houver
    } else if (event.key === 'F11') {
        // F11 para next
        sendDebugCommand('next');
        event.preventDefault(); // Previne a entrada em tela cheia
    } else if (event.key === 'F9') {
        // F2 para continue
        sendDebugCommand('continue');
        event.preventDefault(); // Previne o comportamento padrão, se houver
    }
});
const activeSubsections = [];

function renderSection(section) {
    
    setCookie("section_name", section)
    const instanceId = getSessionCookie();
    const url = `/section/${section}/${instanceId}`;

    fetch(url)
        .then(response => {
            if (response.ok) {
                return response.text();
            }
            throw new Error('Seção não encontrada');
        })
        .then(data => {
            const renderArea = document.getElementById('render-area');
            renderArea.innerHTML = data;
            const subsections = renderArea.querySelectorAll(".main-layout > div");
            subsections.forEach((subsection) => {
                const subsectionName = subsection.getAttribute('subsectionname');
                loadSectionData(section, subsectionName);

                const headerElement = subsection.children[0];

                toggleSubsection(headerElement);
                headerElement.onclick = function () {
                    toggleSubsection(headerElement);
                };
            });
        })
        .catch(error => console.error('Erro ao carregar a seção:', error));
}

function loadSectionData(section, subsection) {
    const instanceId = getSessionCookie();
    const url = `/section/${section}/${instanceId}/${subsection}`;
    actualSection = section;
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            switch (subsection) {
                case 'disassembly':
                    renderDisassembly(data);
                    break;
                case 'registers':
                    renderRegisters(data);
                    break;
                case 'memory':
                    renderMemory(data);
                    break;
                case 'stack':
                    renderStack(data);
                    break;
                default:
                    console.warn('Subseção não identificada:', subsection);
                    break;
            }
        })
        .catch(error => console.error('Erro ao carregar a subseção:', error));
}

function toggleSubsection(headerElement) {
    headerElement.classList.toggle("active");

    const subsectionName = headerElement.parentElement.getAttribute('subsectionname');
    if (activeSubsections.includes(subsectionName)) {
        const index = activeSubsections.indexOf(subsectionName);
        activeSubsections.splice(index, 1);
    } else {
        activeSubsections.push(subsectionName);
    }
}

function setSessionCookie(sessionId) {
    setCookie("session_id", sessionId)    
}

function getCookie(cookieName) {
    cookieName += "=" 
    
    const decodedCookie = decodeURIComponent(document.cookie);
    const cookieArray = decodedCookie.split(';');
    for (let i = 0; i < cookieArray.length; i++) {
        let cookie = cookieArray[i].trim();
        if (cookie.indexOf(cookieName) === 0) {
            return cookie.substring(cookieName.length, cookie.length);
        }
    }
    return "";
}

function setCookie(cookieName, data) {
    const expirationDays = 2;
    
    const date = new Date();
    date.setTime(date.getTime() + (expirationDays * 24 * 60 * 60 * 1000));
    const expires = "expires=" + date.toUTCString();
    document.cookie = `${cookieName}=${data};${expires};path=/`;
}

function getSessionCookie() {
    return getCookie('session_id')    
}

// ------- render functions -----------

function renderDisassembly(data) {
    const disassemblyContent = document.querySelector('.disassembly-content');
    disassemblyContent.innerHTML = ''; // Limpa o conteúdo anterior
    
    data.forEach(line => {
        const div = document.createElement('div');
        div.className = 'disassembly-line';

        // Verifica se a linha é a linha atual ou se é um breakpoint
        const isCurrentLine = line[0];
        const isBreakpoint = line[1];
        
        div.innerHTML = `
            <span class="address ${isCurrentLine ? 'highlight' : ''} ${isBreakpoint ? 'breakpoint' : ''}" data-address="${line[2]}">${line[2]}</span>
            <span class="offset">${line[3]}</span>
            <span class="instruction">${line[4]}</span> 
            <span class="arguments">${line[5]}</span>
        `;
        
        disassemblyContent.appendChild(div);

        // Adicionar event listener ao endereço para gerenciar breakpoints
        const addressElement = div.querySelector('.address');
        addressElement.addEventListener('dblclick', function() {
            toggleBreakpoint(addressElement);
        });
    });
}

function renderRegisters(data) {
    const registersContent = document.querySelector('.registers-content tbody');
    registersContent.innerHTML = ''; // Limpa o conteúdo anterior
    data.forEach(register => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${register[0]}</td>
            <td>${register[1]}</td>
        `;
        registersContent.appendChild(tr);
    });
}

function renderMemory(data) {
    const memoryContent = document.querySelector('.memory-content tbody');
    memoryContent.innerHTML = ''; // Limpa o conteúdo anterior
    data.forEach(memory => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${memory[0]}</td>
            <td>${memory[1]}</td>
            <td>${memory[2]}</td>
        `;
        memoryContent.appendChild(tr);
    });
}

function renderStack(data) {
    const stackContent = document.querySelector('.stack-content ul');
    stackContent.innerHTML = ''; // Limpa o conteúdo anterior
    data.forEach(frame => {
        const li = document.createElement('li');
        li.textContent = frame;
        stackContent.appendChild(li);
    });
}

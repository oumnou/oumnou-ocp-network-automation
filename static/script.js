  const consoleOutput = document.getElementById('console-output');
  const statusConnection = document.getElementById('status-connection');
  const statusAction = document.getElementById('status-action');
  const sshPassword = document.getElementById('ssh-password');

  function logToConsole(message) {
    consoleOutput.innerHTML += message + "\n";
    consoleOutput.scrollTop = consoleOutput.scrollHeight;
  }

  function updateStatus(connection, action) {
    statusConnection.textContent = 'Statut : ' + connection;
    statusAction.textContent = 'Dernière action : ' + action;
  }

  document.getElementById('btn-show-ovs').addEventListener('click', () => {
    const password = sshPassword.value.trim();
    if (!password) {
      alert('Veuillez entrer le mot de passe SSH.');
      return;
    }

    updateStatus('Connecté', 'Récupération Open vSwitch');
    logToConsole('> Connexion SSH et récupération de la configuration...');

    fetch('/api/show_ovs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: password })
    })
    .then(response => response.json())
    .then(data => {
      if (data.error) {
        logToConsole(`Erreur : ${data.error}`);
      }
      if (data.output) {
        logToConsole(data.output);
      }
      updateStatus('Connecté', 'Configuration récupérée');
    })
    .catch(err => {
      logToConsole(`Erreur réseau : ${err}`);
      updateStatus('Erreur', 'Connexion échouée');
    });
  });


  document.getElementById('btn-generate-report').addEventListener('click', () => {
    const ip = document.getElementById('ip-address').value || '192.168.10.1';
    logToConsole(`> Génération du rapport pour le switch ${ip}...`);
    updateStatus('Connecté', 'Rapport généré');
  });

  document.getElementById('btn-save-config').addEventListener('click', () => {
    const ip = document.getElementById('ip-address').value || '192.168.10.1';
    logToConsole(`> Sauvegarde de la configuration pour le switch ${ip}...`);
    updateStatus('Connecté', 'Configuration sauvegardée');
  });

  document.getElementById('btn-upload-config').addEventListener('click', () => {
    const ip = document.getElementById('ip-address').value || '192.168.10.1';
    logToConsole(`> Chargement de la configuration vers le switch ${ip}...`);
    updateStatus('Connecté', 'Configuration chargée');
  });


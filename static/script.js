document.addEventListener('DOMContentLoaded', () => {
  const consoleOutput = document.getElementById('console-output');
  const statusConnection = document.getElementById('status-connection');
  const statusAction = document.getElementById('status-action');
  const sshPassword = document.getElementById('ssh-password');

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
    consoleOutput.value = '> Connexion SSH et récupération de la configuration...\n';

    fetch('/api/show_ovs_full', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: password })
    })
    .then(response => {
      if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
      return response.json();
    })
    .then(data => {
      consoleOutput.value = '';

      for (const [cmd, result] of Object.entries(data)) {
        consoleOutput.value += `\n> Command: ${cmd}\n`;
        if (result.error && result.error.trim() !== '') {
          consoleOutput.value += `[Erreur] : ${result.error}\n`;
        }
        if (result.output && result.output.trim() !== '') {
          consoleOutput.value += result.output + '\n';
        } else {
          consoleOutput.value += '[Aucune sortie]\n';
        }
      }
      consoleOutput.scrollTop = consoleOutput.scrollHeight;
      updateStatus('Connecté', 'Configuration récupérée');
    })
    .catch(err => {
      consoleOutput.value += `Erreur réseau : ${err}\n`;
      consoleOutput.scrollTop = consoleOutput.scrollHeight;
      updateStatus('Erreur', 'Connexion échouée');
    });
  });

  // You can add other button listeners here too

});

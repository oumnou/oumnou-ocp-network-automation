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

  if (!data.success) {
    consoleOutput.value = `[Erreur] : ${data.error || "Erreur inconnue"}`;
    return;
  }

  for (const [cmd, result] of Object.entries(data.results)) {
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


 document.getElementById('btn-backup').addEventListener('click', () => {
  const password = sshPassword.value.trim();
  const switchName = document.getElementById('switch-to-backup').value.trim();

  fetch('/api/backup_config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password: password, switch: switchName })
  })
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      const file = data.file;
      const a = document.createElement('a');
      a.href = `/download/${file}`;
      a.download = file;
      a.click();
      alert('Sauvegarde terminée !');
    } else {
      alert('Erreur lors de la sauvegarde : ' + (data.error || 'Erreur inconnue'));
    }
  })
  .catch(err => {
    console.error(err);
    alert("Erreur lors de la sauvegarde.");
  });
});


});
// On page load, fetch list of backups to populate dropdown
  document.addEventListener('DOMContentLoaded', () => {
    fetch('/api/list_backups')
      .then(res => res.json())
      .then(data => {
        const select = document.getElementById('backup-files');
        data.files.forEach(file => {
          const opt = document.createElement('option');
          opt.value = file;
          opt.textContent = file;
          select.appendChild(opt);
        });
      })
      .catch(err => {
        console.error('Erreur récupération fichiers backup:', err);
      });
  });


  document.addEventListener('DOMContentLoaded', () => {
  // Fetch backup files to populate the dropdown
  fetch('/api/list_backups')
    .then(res => res.json())
    .then(data => {
      const select = document.getElementById('backup-files');
      data.files.forEach(file => {
        const option = document.createElement('option');
        option.value = file;
        option.textContent = file;
        select.appendChild(option);
      });
    })
    .catch(err => {
      console.error('Erreur chargement fichiers de sauvegarde:', err);
    });
});

// Function to print to the console output area
function logToConsole(message, success = true) {
  const consoleOutput = document.getElementById('console-output');
  consoleOutput.value += `\n> ${message}`;
  consoleOutput.scrollTop = consoleOutput.scrollHeight;

  const statusAction = document.getElementById('status-action');
  statusAction.textContent = `Dernière action : ${message}`;
  statusAction.style.color = success ? 'green' : 'red';
}

// Handle "Charger Config" button click
document.getElementById('btn-upload-config').addEventListener('click', async () => {
  const backupFile = document.getElementById('backup-files').value;
  const switchName = document.getElementById('new-switch-name').value;
  const password = document.getElementById('ssh-password').value;

  if (!backupFile || !switchName || !password) {
    logToConsole('❌ Veuillez remplir tous les champs pour charger la configuration.', false);
    return;
  }

  try {
    const response = await fetch('/api/load_config', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        backup_file: backupFile,
        switch_name: switchName,
        password: password
      })
    });

    const result = await response.json();

    if (result.success) {
      logToConsole(`✅ Configuration "${backupFile}" appliquée à "${switchName}" avec succès.`);
    } else {
      logToConsole(`❌ Erreur lors du chargement : ${result.error}`, false);
    }
  } catch (error) {
    logToConsole(`❌ Erreur réseau ou serveur : ${error}`, false);
  }
});

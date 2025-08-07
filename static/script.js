document.addEventListener('DOMContentLoaded', () => {
  const consoleOutput = document.getElementById('console-output');
  const statusConnection = document.getElementById('status-connection');
  const statusAction = document.getElementById('status-action');
  const sshPassword = document.getElementById('ssh-password');

  function updateStatus(connection, action) {
    statusConnection.textContent = 'Statut : ' + connection;
    statusAction.textContent = 'Dernière action : ' + action;
  }

  // Function to print to the console output area
  function logToConsole(message, success = true) {
    consoleOutput.value += `\n> ${message}`;
    consoleOutput.scrollTop = consoleOutput.scrollHeight;
    statusAction.textContent = `Dernière action : ${message}`;
    statusAction.style.color = success ? 'green' : 'red';
  }

  // Fetch backup files to populate the dropdown on page load
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
      logToConsole('❌ Erreur lors du chargement des fichiers de sauvegarde', false);
    });

  // Show OVS button event listener
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

  // Backup button event listener
  document.getElementById('btn-backup').addEventListener('click', () => {
    const password = sshPassword.value.trim();
    const switchName = document.getElementById('switch-to-backup').value.trim();

    if (!password) {
      logToConsole('❌ Veuillez entrer le mot de passe SSH.', false);
      return;
    }

    if (!switchName) {
      logToConsole('❌ Veuillez entrer le nom du switch à sauvegarder.', false);
      return;
    }

    logToConsole('🔄 Sauvegarde en cours...');

    fetch('/api/backup_config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: password, switch: switchName })
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        logToConsole(`✅ Sauvegarde terminée ! Fichier: ${data.file}`);
        // Refresh the backup files dropdown
        location.reload();
      } else {
        logToConsole(`❌ Erreur lors de la sauvegarde : ${data.error || 'Erreur inconnue'}`, false);
      }
    })
    .catch(err => {
      console.error('Backup error:', err);
      logToConsole(`❌ Erreur réseau lors de la sauvegarde: ${err}`, false);
    });
  });

  // Load config button event listener
  document.getElementById('btn-upload-config').addEventListener('click', async () => {
    const backupFile = document.getElementById('backup-files').value;
    const switchIP = document.getElementById('new-switch-name').value.trim();
    const password = sshPassword.value.trim();

    if (!backupFile || !switchIP || !password) {
      logToConsole('❌ Veuillez remplir tous les champs pour charger la configuration.', false);
      return;
    }

    // Basic IP validation
    const ipRegex = /^(\d{1,3}\.){3}\d{1,3}$/;
    if (!ipRegex.test(switchIP)) {
      logToConsole('❌ Veuillez entrer une adresse IP valide (ex: 192.168.1.100)', false);
      return;
    }

    logToConsole(`🔄 Chargement de la configuration sur ${switchIP}...`);

    try {
      const response = await fetch('/api/load_config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          backup_file: backupFile,
          switch_name: switchIP,  // This is actually the IP address
          password: password
        })
      });

      // Check if the response is actually JSON
      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        const text = await response.text();
        console.error('Non-JSON response:', text);
        logToConsole(`❌ Erreur serveur: Réponse non-JSON reçue`, false);
        return;
      }

      const result = await response.json();

      if (result.success) {
        logToConsole(`✅ Configuration "${backupFile}" appliquée à ${switchIP} avec succès.`);
        
        // Display command results if available
        if (result.results && result.results.length > 0) {
          consoleOutput.value += '\n--- Détails des commandes exécutées ---\n';
          let successCount = 0;
          let errorCount = 0;
          
          result.results.forEach((cmdResult, index) => {
            const [command, output, error] = cmdResult;
            consoleOutput.value += `${index + 1}. ${command}\n`;
            
            if (error && error.trim()) {
              consoleOutput.value += `   ❌ Erreur: ${error}\n`;
              errorCount++;
            } else {
              successCount++;
              if (output && output.trim()) {
                consoleOutput.value += `   ✅ Sortie: ${output}\n`;
              } else {
                consoleOutput.value += `   ✅ Commande exécutée avec succès\n`;
              }
            }
          });
          
          consoleOutput.value += `\n📊 Résumé: ${successCount} succès, ${errorCount} erreurs\n`;
          consoleOutput.scrollTop = consoleOutput.scrollHeight;
        }
      } else {
        logToConsole(`❌ Erreur lors du chargement : ${result.error}`, false);
      }
    } catch (error) {
      console.error('Load config error:', error);
      logToConsole(`❌ Erreur réseau ou serveur : ${error.message}`, false);
    }
  });

  // Generate report button - now lists available bridges
  document.getElementById('btn-generate-report').addEventListener('click', () => {
    const password = sshPassword.value.trim();
    if (!password) {
      logToConsole('❌ Veuillez entrer le mot de passe SSH.', false);
      return;
    }

    logToConsole('🔄 Récupération de la liste des bridges...');

    fetch('/api/list_bridges', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: password })
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        if (data.bridges.length > 0) {
          logToConsole(`📋 Bridges disponibles: ${data.bridges.join(', ')}`);
        } else {
          logToConsole('📋 Aucun bridge trouvé sur le switch.');
        }
      } else {
        logToConsole(`❌ Erreur: ${data.error}`, false);
      }
    })
    .catch(err => {
      console.error('List bridges error:', err);
      logToConsole(`❌ Erreur réseau: ${err}`, false);
    });
  });
});
document.addEventListener('DOMContentLoaded', () => {
  const consoleOutput = document.getElementById('console-output');
  const statusConnection = document.getElementById('status-connection');
  const statusAction = document.getElementById('status-action');
  const sshPassword = document.getElementById('ssh-password');
  const backupSelect = document.getElementById('backup-files');
  const quickScanBtn = document.getElementById('btn-quick-scan');
  const scanNetworkBtn = document.getElementById('btn-scan-network');
  const clearResultsBtn = document.getElementById('btn-clear-results');
  const testConnectionBtn = document.getElementById('btn-test-connection');
  const listBridgesBtn = document.getElementById('btn-list-bridges');
  const loadConfigBtn = document.getElementById('btn-load-config');

  function updateStatus(connection, action) {
    if(statusConnection) statusConnection.textContent = 'Statut : ' + connection;
    if(statusAction) statusAction.textContent = 'Dernière action : ' + action;
  }

  function logToConsole(message, success = true) {
    if (!consoleOutput) return;
    if (consoleOutput.value && consoleOutput.value.trim() !== '') {
      consoleOutput.value += `\n> ${message}`;
    } else {
      consoleOutput.value = `> ${message}`;
    }
    consoleOutput.scrollTop = consoleOutput.scrollHeight;
    if (statusAction) {
      statusAction.textContent = `Dernière action : ${message}`;
      statusAction.style.color = success ? 'green' : 'red';
    }
  }

  // Load backup files into dropdown
  function loadBackupFiles() {
    if(!backupSelect) return;
    fetch('/api/list_backups')
      .then(res => {
        if (!res.ok) throw new Error(`HTTP error! Status: ${res.status}`);
        return res.json();
      })
      .then(data => {
        backupSelect.innerHTML = '<option value="">-- Sélectionner un fichier --</option>';
        data.files.forEach(file => {
          const option = document.createElement('option');
          option.value = file;
          option.textContent = file;
          backupSelect.appendChild(option);
        });
        logToConsole('✅ Liste des fichiers de sauvegarde chargée');
      })
      .catch(err => {
        console.error('Erreur chargement fichiers de sauvegarde:', err);
        logToConsole('❌ Erreur lors du chargement des fichiers de sauvegarde', false);
      });
  }

  // Helper function to display scan results in the hosts table
  function displayScanResults(hosts) {
    const tbody = document.getElementById('hosts-table-body');
    const scanResultsDiv = document.getElementById('scan-results');
    const scanSummary = document.getElementById('scan-summary');
    
    if (!tbody || !scanResultsDiv) return;

    tbody.innerHTML = '';

    if (hosts.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">Aucun hôte trouvé</td></tr>';
    } else {
      hosts.forEach(host => {
        const tr = document.createElement('tr');
        if (host.is_switch_candidate) tr.classList.add('switch-candidate');

        const portTags = host.open_ports.map(port => {
          let tagClass = '';
          if (port === 22) tagClass = 'ssh';
          else if (port === 80 || port === 443) tagClass = 'web';
          else if (port === 161) tagClass = 'snmp';
          return `<span class="tag ${tagClass}">${port}</span>`;
        }).join(' ');

        tr.innerHTML = `
          <td>${host.ip}</td>
          <td>${host.hostname || host.ip}</td>
          <td>${portTags}</td>
          <td>${host.device_type || 'Inconnu'}</td>
          <td>
            <button class="select-switch-btn" data-ip="${host.ip}">Sélectionner</button>
          </td>
        `;
        tbody.appendChild(tr);
      });
    }

    // Update scan summary
    if (scanSummary) {
      const switchCount = hosts.filter(h => h.is_switch_candidate).length;
      scanSummary.innerHTML = `
        <p><strong>Hôtes trouvés:</strong> ${hosts.length} | 
        <strong>Candidats switches:</strong> ${switchCount}</p>
      `;
    }

    scanResultsDiv.classList.remove('hidden');

    // Attach event listeners to select buttons
    document.querySelectorAll('.select-switch-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const ip = btn.getAttribute('data-ip');
        const selectedSwitchInput = document.getElementById('selected-switch');
        if (selectedSwitchInput) {
          selectedSwitchInput.value = ip;
          logToConsole(`✅ Switch sélectionné : ${ip}`);
        }
      });
    });
  }

  // Initialize
  loadBackupFiles();

  // Quick Scan button
  if (quickScanBtn) {
    quickScanBtn.addEventListener('click', () => {
      const baseIp = document.getElementById('selected-switch')?.value.trim() || '192.168.1.1';
      
      logToConsole(`⚡ Scan rapide lancé...`);
      updateStatus('En cours', 'Scan rapide');

      fetch('/api/quick_scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ base_ip: baseIp })
      })
      .then(res => {
        if (!res.ok) throw new Error(`HTTP error! Status: ${res.status}`);
        return res.json();
      })
      .then(data => {
        if (!data.success) {
          logToConsole(`❌ Erreur lors du scan : ${data.error}`, false);
          updateStatus('Erreur', 'Scan échoué');
          return;
        }

        logToConsole(`✅ Scan rapide terminé. Réseau scanné: ${data.network_scanned}`);
        logToConsole(`📊 Hôtes détectés: ${data.total_found} | Candidats switches: ${data.switch_candidates}`);
        updateStatus('Connecté', 'Scan terminé');

        displayScanResults(data.hosts || []);
      })
      .catch(err => {
        logToConsole(`❌ Erreur réseau pendant le scan: ${err.message || err}`, false);
        updateStatus('Erreur', 'Scan échoué');
      });
    });
  }

  // Network Scan button
  if (scanNetworkBtn) {
    scanNetworkBtn.addEventListener('click', () => {
      const networkRange = document.getElementById('network-range')?.value.trim();
      if (!networkRange) {
        alert('Veuillez entrer une plage réseau valide.');
        return;
      }

      logToConsole(`🔍 Scan réseau lancé sur ${networkRange}...`);
      updateStatus('En cours', 'Scan réseau');

      fetch('/api/scan_network', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ network_range: networkRange })
      })
      .then(res => {
        if (!res.ok) throw new Error(`HTTP error! Status: ${res.status}`);
        return res.json();
      })
      .then(data => {
        if (!data.success) {
          logToConsole(`❌ Erreur lors du scan : ${data.error}`, false);
          updateStatus('Erreur', 'Scan échoué');
          return;
        }

        logToConsole(`✅ Scan réseau terminé. Hôtes détectés: ${data.total_found}`);
        logToConsole(`📊 Candidats switches: ${data.switch_candidates}`);
        updateStatus('Connecté', 'Scan terminé');

        displayScanResults(data.hosts || []);
      })
      .catch(err => {
        logToConsole(`❌ Erreur réseau pendant le scan: ${err.message || err}`, false);
        updateStatus('Erreur', 'Scan échoué');
      });
    });
  }

  // Clear Results button
  if (clearResultsBtn) {
    clearResultsBtn.addEventListener('click', () => {
      const scanResultsDiv = document.getElementById('scan-results');
      const tbody = document.getElementById('hosts-table-body');
      
      if (tbody) tbody.innerHTML = '';
      if (scanResultsDiv) scanResultsDiv.classList.add('hidden');
      
      logToConsole('🗑️ Résultats effacés');
    });
  }

  // Test Connection button
  if (testConnectionBtn) {
    testConnectionBtn.addEventListener('click', () => {
      const selectedSwitch = document.getElementById('selected-switch')?.value.trim();
      const password = sshPassword?.value.trim();

      if (!selectedSwitch) {
        logToConsole('❌ Veuillez sélectionner un switch', false);
        return;
      }
      if (!password) {
        logToConsole('❌ Veuillez entrer le mot de passe SSH', false);
        return;
      }

      logToConsole(`🔌 Test de connexion vers ${selectedSwitch}...`);

      fetch('/api/test_switch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ip: selectedSwitch,
          username: 'kali',
          password: password
        })
      })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          logToConsole(`✅ ${data.message}`);
        } else {
          logToConsole(`❌ ${data.error}`, false);
        }
      })
      .catch(err => {
        logToConsole(`❌ Erreur lors du test: ${err.message}`, false);
      });
    });
  }

  // Show OVS button
  const showOvsBtn = document.getElementById('btn-show-ovs');
  if (showOvsBtn) {
    showOvsBtn.addEventListener('click', () => {
      const password = sshPassword?.value.trim();
      const selectedSwitch = document.getElementById('selected-switch')?.value.trim();
      
      if (!password) {
        alert('Veuillez entrer le mot de passe SSH.');
        return;
      }

      updateStatus('Connecté', 'Récupération Open vSwitch');
      if(consoleOutput) consoleOutput.value = '> Connexion SSH et récupération de la configuration...\n';

      const requestBody = { password };
      if (selectedSwitch) {
        requestBody.switch_name = selectedSwitch;
      }

      fetch('/api/show_ovs_full', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
      })
      .then(response => {
        if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
        return response.json();
      })
      .then(data => {
        if(consoleOutput) consoleOutput.value = '';

        if (!data.success) {
          if(consoleOutput) consoleOutput.value = `[Erreur] : ${data.error || "Erreur inconnue"}`;
          return;
        }

        for (const [cmd, result] of Object.entries(data.results)) {
          if(consoleOutput) {
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
        }
        if(consoleOutput) consoleOutput.scrollTop = consoleOutput.scrollHeight;
        updateStatus('Connecté', 'Configuration récupérée');
      })
      .catch(err => {
        if(consoleOutput) {
          consoleOutput.value += `Erreur réseau : ${err.message || err}\n`;
          consoleOutput.scrollTop = consoleOutput.scrollHeight;
        }
        updateStatus('Erreur', 'Connexion échouée');
      });
    });
  }

  // Backup button
  const backupBtn = document.getElementById('btn-backup');
  if (backupBtn) {
    backupBtn.addEventListener('click', () => {
      const password = sshPassword?.value.trim();
      const switchName = document.getElementById('switch-to-backup')?.value.trim();
      const selectedSwitch = document.getElementById('selected-switch')?.value.trim();

      if (!password) {
        logToConsole('❌ Veuillez entrer le mot de passe SSH.', false);
        return;
      }
      if (!switchName) {
        logToConsole('❌ Veuillez entrer le nom du switch à sauvegarder.', false);
        return;
      }

      logToConsole('🔄 Sauvegarde en cours...');

      const requestBody = { password, switch: switchName };
      if (selectedSwitch) {
        requestBody.target_host = selectedSwitch;
      }

      fetch('/api/backup_config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          logToConsole(`✅ Sauvegarde terminée ! Fichier: ${data.file}`);
          logToConsole(`📊 Ports trouvés: ${data.ports_found} | Source: ${data.source_host}`);
          loadBackupFiles();
        } else {
          logToConsole(`❌ Erreur lors de la sauvegarde : ${data.error || 'Erreur inconnue'}`, false);
        }
      })
      .catch(err => {
        console.error('Backup error:', err);
        logToConsole(`❌ Erreur réseau lors de la sauvegarde: ${err.message || err}`, false);
      });
    });
  }

  // List Bridges button
  if (listBridgesBtn) {
    listBridgesBtn.addEventListener('click', () => {
      const password = sshPassword?.value.trim();
      if (!password) {
        logToConsole('❌ Veuillez entrer le mot de passe SSH.', false);
        return;
      }

      logToConsole('🔄 Récupération de la liste des bridges...');

      fetch('/api/list_bridges', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password })
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
        logToConsole(`❌ Erreur réseau: ${err.message}`, false);
      });
    });
  }

  // Load Config button
  if (loadConfigBtn) {
    loadConfigBtn.addEventListener('click', async () => {
      const backupFile = backupSelect?.value;
      const switchIP = document.getElementById('selected-switch')?.value.trim();
      const password = sshPassword?.value.trim();

      if (!backupFile || !switchIP || !password) {
        logToConsole('❌ Veuillez remplir tous les champs pour charger la configuration.', false);
        return;
      }

      const ipRegex = /^(\d{1,3}\.){3}\d{1,3}$/;
      if (!ipRegex.test(switchIP)) {
        logToConsole('❌ Veuillez entrer une adresse IP valide (ex: 192.168.1.100)', false);
        return;
      }

      logToConsole(`🔄 Chargement de la configuration sur ${switchIP}...`);

      try {
        const response = await fetch('/api/load_config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            backup_file: backupFile,
            switch_name: switchIP,
            password
          })
        });

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
  }
});
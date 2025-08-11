Excellent decision! Before adding **Nmap**, you should validate that your existing automation workflow is fully functional. Here's a detailed **✅ Test Plan** for your **Network Automation Tool**, covering all key features:

---

## ✅ **Network Automation Tool — Test Plan**

### 🧪 Environment Preparation:

* Ensure **Open vSwitch** is running on the remote VM (`192.168.116.134`)
* The SSH key or password (`kali`) is working
* Flask backend is running (`flask run`)
* Frontend is reachable in browser

---

## 🧩 Module 1: Show OVS Configuration

### ✅ Test Case: `btn-show-ovs`

| Step              | Action                                                   |
| ----------------- | -------------------------------------------------------- |
| 1                 | Open the UI in browser                                   |
| 2                 | Verify IP and password fields                            |
| 3                 | Click **📋 Show Open vSwitch**                           |
| ✅ Expected Result | Console shows the OVS bridge (`vSwitchA`) and interfaces |

**Verify:**

* Cleaned output (no UUIDs or sudo prompts)
* No connection errors

---

## 🧩 Module 2: Backup Configuration

### ✅ Test Case: `btn-backup`

| Step              | Action                                                 |
| ----------------- | ------------------------------------------------------ |
| 1                 | Enter **"vSwitchA"** in “Nom du switch à sauvegarder”  |
| 2                 | Click **💾 Sauvegarder Config**                        |
| ✅ Expected Result | Message: `✅ Sauvegarde enregistrée sous vSwitchA.yaml` |

**Verify:**

* File is created under `backups/vSwitchA.yaml`
* YAML contains meaningful bridge/interface info

---

## 🧩 Module 3: Upload Configuration

### ✅ Test Case: `btn-upload-config`

| Step              | Action                                          |
| ----------------- | ----------------------------------------------- |
| 1                 | Select a saved config in dropdown               |
| 2                 | Provide new switch name (e.g., `vSwitchB`)      |
| 3                 | Click **⬆️ Charger Config**                     |
| ✅ Expected Result | Message: `✅ Configuration appliquée à vSwitchB` |

**Verify:**

* `ovs-vsctl` commands applied remotely
* New bridge created on the remote switch

---

## 🧩 Module 4: Generate Report

### ✅ Test Case: `btn-generate-report`

| Step              | Action                                                                             |
| ----------------- | ---------------------------------------------------------------------------------- |
| 1                 | Click **📝 Générer Rapport**                                                       |
| ✅ Expected Result | A downloadable PDF or text file is generated, summarizing the current switch state |

*(Optional — depends if implemented yet)*

---

## 🧩 Module 5: UI Consistency

### ✅ Test Case: Form fields

| Item             | Check                               |
| ---------------- | ----------------------------------- |
| IP Address field | Pre-filled and **disabled**         |
| SSH Password     | Accepts input, used correctly       |
| Switch names     | Mandatory validation on Save/Upload |

---

## ⚠️ Error Handling Tests

| Test                          | Action                                   | Expected                             |
| ----------------------------- | ---------------------------------------- | ------------------------------------ |
| Missing switch name on backup | Leave field blank, click **Sauvegarder** | Error: `Switch name is required.`    |
| SSH failure                   | Set wrong IP or password                 | Error popup with SSH failure details |
| Upload without selection      | Leave dropdown empty                     | Error: "No file selected"            |

---

## 📂 File System Check

* Ensure backup files go to: `backups/`
* File names follow: `vSwitchName.yaml`
* Content is clean YAML (not raw OVS output)

---

## 🧪 Bonus Manual Check (Optional)

* SSH manually into the switch to verify changes:

```bash
ssh -i ~/.ssh/id_rsa kali@192.168.116.134
sudo ovs-vsctl show
```

---

### ✅ After All Pass:

You're ready to integrate **Nmap** for discovery phase.

Do you want a printable test checklist PDF or want to start automating these test cases (with `pytest` or `Selenium`)?



git add .


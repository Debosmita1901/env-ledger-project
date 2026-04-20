# 🌿 EnviroLedger – University Campus Environmental Tracking System

A full-stack web application for recording, managing, and analyzing environmental resource consumption on a university campus.

---

## 📦 Setup & Run

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the App
```bash
python app.py
```

### 3. Open in Browser
```
http://localhost:5000
```

---

## 🔐 Default Login Credentials

| Username   | Password     | Role     |
|------------|-------------|----------|
| admin      | admin123     | Admin    |
| staff1     | staff123     | Staff    |
| analyst1   | analyst123   | Analyst  |

---

## 🏗 Project Structure

```
project-root/
├── app.py                  # Flask backend (routes, DB, logic)
├── requirements.txt        # Python dependencies
├── database.db             # Auto-created SQLite DB
├── templates/
│   ├── index.html          # Base layout (sidebar)
│   ├── login.html          # Login page
│   ├── dashboard.html      # Overview + charts
│   ├── electricity.html    # Electricity entry & ledger
│   ├── fuel.html           # Fuel entry & ledger
│   ├── water.html          # Water entry & ledger
│   ├── waste.html          # Waste entry & ledger
│   ├── emissions.html      # Emissions entry & ledger
│   ├── reports.html        # Filtered reports + chart
│   ├── audit.html          # Audit trail (admin)
│   └── users.html          # User management (admin)
├── static/
│   ├── style.css           # Dark theme CSS
│   └── script.js           # Shared JS
└── README.md
```

---

## ✨ Features

- **Role-Based Access Control** – Admin / Staff / Analyst with different permissions
- **5 Resource Modules** – Electricity (kWh), Fuel (L), Water (L), Waste (kg), Emissions (CO₂ kg)
- **Immutable Ledger** – Entries are never deleted; only flagged as updated
- **Carbon Footprint Calculator** – Auto-computed from emission factors
- **Audit Trail** – Every login, logout, and data action is logged
- **Charts** – Chart.js line and doughnut charts on dashboard; bar chart on reports
- **Filtering** – Reports can be filtered by type and date range
- **User Management** – Admin can create/delete users

---

## 🧮 Carbon Emission Factors

| Resource    | Factor               |
|-------------|----------------------|
| Electricity | 0.82 kg CO₂e / kWh   |
| Fuel        | 2.31 kg CO₂e / Liter |
| Water       | 0.001 kg CO₂e / Liter|
| Waste       | 0.50 kg CO₂e / kg    |
| Emissions   | 1.00 kg CO₂e / kg    |

# ⛽ FuelGuard Pro: Smart Fuel Management System

**FuelGuard Pro** is a digital solution designed to streamline fuel distribution and prevent resource waste in Bangladesh. By implementing a 72-hour lockout rule and sector-specific verification, it ensures that fuel is allocated fairly to those who need it most.

## 🚀 Live Application
**[Access FuelGuard Pro Here](https://fuelguard.streamlit.app)**

---

## 📖 Table of Contents
* [Features](#-features)
* [How it Works](#-how-it-works)
* [Tech Stack](#-tech-stack)
* [Local Setup](#-local-setup)
* [SEO & Accessibility](#-seo--accessibility)

---

## ✨ Features
- **72-Hour Lockout Logic:** Prevents multiple refills within a 3-day window for general users.
- **Categorized Portals:** - **Farmers:** NID-based registration and UNO certificate tracking.
  - **Government:** Priority tracking for official vehicles.
  - **General:** Bangladesh district-specific vehicle plate registration.
- **Operator Dashboard:** Secure portal for pump operators to log liters and fuel types (Octane/Petrol/Diesel).
- **Bilingual Support:** Full Bengali instructions for local accessibility.

## 🛠 How it Works
1. **Registration:** Users register their NID or Vehicle Plate.
2. **Verification:** The system checks the database (Supabase) to see if the ID has been used in the last 72 hours.
3. **Distribution:** If eligible, the operator records the transaction and the lockout timer resets.

## 💻 Tech Stack
- **Frontend:** [Streamlit](https://streamlit.io/) (Python Framework)
- **Database:** [Supabase](https://supabase.com/) (PostgreSQL)
- **Hosting:** Streamlit Cloud

## 🔧 Local Setup
To run this project locally:

1. **Clone the repo:**
   ```bash
   git clone [https://github.com/your-username/fuelguard.git](https://github.com/your-username/fuelguard.git)

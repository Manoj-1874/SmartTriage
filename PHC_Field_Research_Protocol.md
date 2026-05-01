# MASTER PHC FIELD RESEARCH PROTOCOL (DEEP DIVE)
*Targeting a 100% Digital, Real-Time Connected Health Ecosystem.*

---

## 🏗️ CORE RESEARCH OBJECTIVE
To identify the "Digital-to-Manual" gaps in the current Primary Health Center (PHC) ecosystem and design a centralized platform that connects Sub-Centres, PHCs, and the DDHS with real-time data, automated monitoring, and zero paperwork.

---

## 📋 SECTION 1: ATTENDANCE, PERSONNEL & MOVEMENT
*Goal: Identify how to automate absenteeism alerts for the DDHS.*

### Question 1.1: "How is your daily attendance recorded and verified?"
*   **Target:** All Staff (Doctors, Nurses, Pharmacists).
*   **The "Why":** Existing systems often use manual registers or non-geo-fenced biometrics. We need to know if a doctor can be marked "Present" while actually being away.
*   **Explanation:** We are looking for the **source of truth**. If it's a book, the data is "dead". If it's digital but not real-time, the DDHS cannot get "Automated Absenteeism Alerts."
*   **Watch For:** A physical signature book (The "Log Book") on a desk near the entrance.

### Question 1.2: "If you are sent on 'On-Duty' (OD) to another center, how does the DDHS track your location?"
*   **Target:** Medical Officer / Staff Nurse.
*   **The "Why":** Staff are often moved to fill gaps. If the system doesn't track "Movement," the DDHS loses sight of the district's human resources.
*   **Explanation:** We want to build a "Live Staff Map." Current systems usually mark them "Present" at their home PHC, which is inaccurate.

### Question 1.3: "What happens if you need to take a sudden emergency leave? How long does it take for the DDHS office to find out?"
*   **Target:** Medical Officer.
*   **The "Why":** Manual leave applications take days to reach the DDHS. 
*   **Explanation:** This justifies the need for an "Instant Leave/Absenteeism Notification" feature for the DDHS.

---

## 📋 SECTION 2: THE "ZERO PAPERWORK" & DUPLICATE ENTRY AUDIT
*Goal: Justify the replacement of physical registers with a unified dashboard.*

### Question 2.1: "After entering data into PICME or HIMIS, do you still write in a paper register?"
*   **Target:** ANC Nurse / Data Entry Operator.
*   **The "Why":** If they use both, the digital system is a **burden**. We need to identify every paper register that still exists so we can digitize it.
*   **Explanation:** True digital transformation means the computer *replaces* the paper, not adds to it.
*   **Watch For:** Large registers with handwritten columns (ANC, PNC, Immunization).

### Question 2.2: "When the internet goes down, what is your protocol for recording data?"
*   **Target:** Pharmacist / Lab Tech / Nurse.
*   **The "Why":** Rural PHCs have frequent outages. If the system isn't "Offline-First," it will fail.
*   **Explanation:** We need to justify local database caching (Offline-Mode).

### Question 2.3: "Do you have to submit a separate 'Monthly Progress Report' (MPR)? How many hours do you spend calculating the totals manually?"
*   **Target:** Block Health Statistician / Medical Officer.
*   **The "Why":** MPRs are usually manual summaries of the daily registers.
*   **Explanation:** Our system will "Auto-Generate" the MPR at midnight on the last day of the month, saving 10+ hours of staff time.

---

## 📋 SECTION 3: REFERRAL, EMERGENCY & INTER-FACILITY CONNECTIVITY
*Goal: Analyze the communication lag between PHC tiers.*

### Question 3.1: "How do you notify the Upgraded PHC or GH that a critical patient is coming?"
*   **Target:** Medical Officer / Ambulance Driver.
*   **The "Why":** Most referrals are done via paper slips. The receiving hospital has no "Real-Time" warning.
*   **Explanation:** We want to build an "Emergency Handshake" feature.
*   **Watch For:** The "Referral Slip" pad. Check if it's carbon-copy.

### Question 3.2: "Is there a dashboard where you can see the 'Live Bed Availability' of the nearby Upgraded PHC or District GH?"
*   **Target:** Medical Officer.
*   **The "Why":** Referrals often fail because the GH is full. 
*   **Explanation:** This justifies the "Centralized Platform" connecting all divisions.

### Question 3.3: "If an ambulance (108) is delayed, how do you track its live location? Do you have to call them repeatedly?"
*   **Target:** Nurse on Emergency Duty.
*   **The "Why":** Phone coordination is slow during emergencies.
*   **Explanation:** A "Live Ambulance Map" on the PHC dashboard reduces panic.

---

## 📋 SECTION 4: VACCINE COLD CHAIN & PHARMACY LOGISTICS
*Goal: Automate stock monitoring and temperature safety.*

### Question 4.1: "How do you monitor the vaccine fridge temperature at night?"
*   **Target:** Cold Chain Handler.
*   **The "Why":** Vaccines die if the temperature fluctuates. Manual logging only happens during the day.
*   **Explanation:** This justifies an "IoT-Temperature Alert" that notifies the MO if the fridge fails at 2 AM.

### Question 4.2: "When a medicine is about to expire, how do you find out? Do you check every box manually?"
*   **Target:** Pharmacist.
*   **The "Why":** Expired drugs are a massive liability.
*   **Explanation:** A "Smart Inventory" dashboard with "Expiry Alerts" (90 days/60 days/30 days) is needed.

### Question 4.3: "Can the DDHS see exactly how many tablets are in your stock *right now*?"
*   **Target:** Pharmacist.
*   **The "Why":** Stock-outs are often reported only once a month.
*   **Explanation:** Real-time inventory sync allows the DDHS to "Rebalance" stock across the district.

---

## 📋 SECTION 5: MATERNAL HEALTH (ANC/PNC) & PICME REALITY
*Goal: Identify why high-risk patients are still missed.*

### Question 5.1: "How do you track if a high-risk pregnant woman in a remote village actually went for her referral checkup?"
*   **Target:** Village Health Nurse (VHN).
*   **The "Why":** Many women are referred but never go. The system "loses" them.
*   **Explanation:** We need a "Referral Tracking" module that flags if the patient didn't arrive at the GH within 48 hours.

### Question 5.2: "What is the biggest challenge in tracking women who move to their 'Mother's house' for delivery?"
*   **Target:** VHN.
*   **The "Why":** Migrating patients break the data chain.
*   **Explanation:** This justifies a "Universal Patient ID" that works across all HUDs (Health Unit Districts).

---

## 📋 SECTION 6: INFRASTRUCTURE & BIOMEDICAL WASTE
*Goal: Broaden the "Health Services" monitoring scope.*

### Question 6.1: "If the PHC roof is leaking or a fan is broken, how do you request a repair from the DDHS?"
*   **Target:** Medical Officer.
*   **The "Why":** Infrastructure maintenance is often slow and paper-based.
*   **Explanation:** A "Maintenance Ticketing" system on the dashboard ensures the DDHS sees infrastructure issues immediately.

### Question 6.2: "How do you track the disposal of biomedical waste? Who collects it, and how is it recorded?"
*   **Target:** Sanitary Worker / Nurse.
*   **The "Why":** Waste tracking is a legal requirement but often poorly recorded.
*   **Explanation:** A "Waste Pickup Tracker" ensures environmental compliance.

---

## 📋 SECTION 7: VITAL STATISTICS (BIRTH & DEATH)
*Goal: Accelerate legal reporting.*

### Question 7.1: "How many days does it take for a birth/death occurring here to be reflected in the official legal records?"
*   **Target:** Admin Clerk.
*   **The "Why":** Legal delays affect families.
*   **Explanation:** Real-time notification from the PHC to the DDHS/Panchayat speeds up certificate issuance.

---

## 🔍 FIELD OBSERVATION GUIDE (THE "SILENT RESEARCH")
1.  **Register Audit:** Physically count the number of books on the Doctor's desk. (Count them: 5? 10? 20?).
2.  **Hardware Status:** Check the computer. Is it covered in a cloth? Is it on? Is the monitor screen dusty?
3.  **The "WhatsApp" Proof:** Watch if staff are using their personal WhatsApp groups for official patient discussion. (If yes, it means the current portal is useless for them).
4.  **Language:** Look at the handwritten notes. Are they in English or Tamil?
5.  **Connectivity:** Check your phone's signal strength in the Labor Ward and the Lab.

---
*Prepared by: SmartTriage Research Team for DDHS System Development*

# Project Analysis: SmartTriage Dashboard

## Core Architecture
The SmartTriage Dashboard is a full-stack Flask application designed for district-level healthcare orchestration. It employs a multi-role architecture that connects Patients, Doctors, PHC Nurses, DDHS Administrators, and Ambulance Drivers into a unified medical workflow.

## Key Subsystems
1. **AI Risk Assessment**: The "Dual-Brain" system (`integrated_dual_brain_risk.py`) combines semantic symptom analysis with quantitative vital signs to provide high-precision triage and risk scoring.
2. **Operations & Scheduling**: Automated appointment management and reminder scheduling ensure efficient patient flow between primary health centers and tertiary hospitals.
3. **Emergency Dispatch**: A real-time GPS-enabled ambulance tracking system using Leaflet Routing Machine coordinates emergency responses with road-aware pathing.
4. **Data Security**: Robust role-based access control (RBAC) and encrypted storage protect sensitive patient health information (PHI) across the SQLite database ecosystem.

## Project Abstract
SmartTriage Dashboard is an intelligent healthcare orchestration platform that integrates AI-driven "Dual-Brain" risk assessment with a comprehensive operational ecosystem for district health centers. The system leverages semantic symptom analysis and a universal medical knowledge base to provide real-time patient prioritization, supporting roles from patients and doctors to DDHS administrators and ambulance drivers. It features a sophisticated GPS-enabled dispatch system and real-road tracking to optimize emergency response times and resource allocation. Through dedicated secure portals and automated appointment scheduling, the platform ensures seamless coordination between primary health centers and specialized facilities. This unified solution transforms data-driven insights into actionable medical workflows, significantly enhancing public health management and emergency care efficiency.

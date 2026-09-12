# 💊 MediSavings — Generic Medicine Price Agent

> **Smart prescription parser & real-time medicine price comparator for Peru.**  
> Built by team **Hardcoders** during the *Agents, Everywhere* Global Hackathon.

---

## 📌 Overview & Problem Statement

In Peru, official medicine price data is publicly cataloged by **DIGEMID**, covering registered pharmacies across the country[cite: 1]. However, **patients rarely check government databases while standing at a pharmacy counter**[cite: 1].

- **Extreme Price Gaps:** Identical active ingredients and prescriptions can vary **up to 10x in price** between neighboring pharmacies[cite: 1].
- **Treatment Abandonment:** Approximately **33% of Peruvians fail to complete their medical treatments due to high medication costs**[cite: 1].
- **Friction in Access:** Navigating official portals or interpreting handwritten medical prescriptions is tedious and inaccessible for the average citizen.

---

## 💡 The Solution

**MediSavings** bridges the gap between public pricing datasets and citizens through an accessible, conversational AI agent on Telegram[cite: 1]:

1. **Send a Photo:** The patient snaps a photo of their handwritten or printed prescription directly in Telegram[cite: 1].
2. **Vision AI & Parsing:** An autonomous agent uses Multimodal Vision models to extract medications, dosages, and quantities[cite: 1].
3. **Real-time Price Intelligence:** The agent queries DIGEMID pricing data and finds the best generic and brand-name alternatives in nearby pharmacies for the specified district[cite: 1].
4. **Actionable Recommendations:** Delivers an instant, sorted comparison with exact addresses, pharmacy contact numbers, and direct navigation links within seconds[cite: 1].

---

## 🏗️ Architecture & CLI Pipeline

To keep the LLM context lean and avoid hallucination or high token latency, heavy arithmetic, data ingestion, and filtering are decoupled into an independent, lightweight CLI architecture:

- **Ingestion (`medisaving.ingest`):** Handles DIGEMID data retrieval, source normalization, and local caching.
- **Analytics (`medisaving.analytics`):** Compares unit prices, filters by district/ubigeo, and ranks full medication baskets.
- **UX (`medisaving.ux`):** Telegram bot engine, interactive message formatting, and actionable UI chips.

```bash
# Display CLI commands
python -m medisaving --help

# 1. Ingest & normalize pricing data
python -m medisaving ingest import examples/offers.synthetic.json

# 2. Rank & filter best offers by district
python -m medisaving analytics rank DATASET_ID --district 'Lince' --top 3

# 3. Render payload for Telegram UI
python -m medisaving ux telegram RESULT_ID

# Run test suite
python -m unittest discover -v
--------------------------------------------------------------------------------------------------------------------------------------------------
 
Below is a quick preview of MedSavings Bot in action: processing medical prescriptions, querying DIGEMID pricing and pharmacy availability, and delivering real-time, location-based options.

<img width="932" height="971" alt="image" src="https://github.com/user-attachments/assets/43377379-6eda-4d48-a472-d022e5dd69fb" />

<img width="912" height="966" alt="image" src="https://github.com/user-attachments/assets/2e01759f-7529-4f1c-8246-31a1cdd8427a" />

<img width="907" height="970" alt="image" src="https://github.com/user-attachments/assets/d072ef17-6af2-49ff-84d4-9f89f41ce4e4" />

  <img width="976" height="952" alt="image" src="https://github.com/user-attachments/assets/2dc54ac1-001e-4eb4-80d6-d631079f4321" />

  <img width="1878" height="1197" alt="image" src="https://github.com/user-attachments/assets/61159cd6-5a78-4949-80b4-a8f58131b5f0" />





## Prototype: Interactive Emotional Reflection System

Designed as the final project for Duke University's DESIGNTK 531: Technology Core II, this prototype explores how tactile interaction and adaptive AI can complement quantitative metrics with emotional insights. By combining physical input, computer vision detection, and dynamic conversational AI, the system aims to create a more human-centered approach to post-service feedback collection.

*This is a first-generation prototype focused on feasibility exploration and UX proof of concept.*

---

## Project Overview

This system enables users to select physical "emotion cards" (based on color), triggering an adaptive conversational flow that collects qualitative insights.

The system includes two main components:
- **Subscriber (survey hardware)**: Raspberry Pi + Pi Camera + Emotion card detection (via OpenCV)
- **Publisher (AI conversational logic)**: Gemini 1.5 Pro API prompts users through a warm, context-aware reflection conversation


**Example Use Case:**  
Post-car shopping reflection experience, where customers could quickly and comfortably share highlights and friction points after purchasing a vehicle.

---

## Demo

A full walk-through demo is available [here](https://drive.google.com/drive/folders/1XoOvR5sO3SuasVyCIttI-mE5872OwIRd?usp=sharing)


---

## Repository Structure

- `/project_files`
  - `subscriber.py`  — Handles card detection, onboarding message, user input sending
  - `publisher.py`  — Handles dynamic AI prompt generation, session flow management
  - `camera_preview.py`  — OpenCV utility to visualize card placements
  - `utils.py`  — Color mapping between detected colors and emotions
  - `hsv_ranges.json`  — Tuned HSV color ranges for accurate card detection
- `requirements-laptop.txt`: Dependencies if running on a laptop.
- `requirements-pi.txt`: Dependencies if running on Raspberry Pi.
- `Reflection_Survey_Presentation.pdf`  — Final presentation outlining:
  - Project Background
  - User Flow Chart
  - Systems Diagram (Software)
  - Circuit Diagram (Hardware)
  - Learnings from Prototyping
  - Ideal Product Ideation
  - Consumer Case Study
  
---

## Ethos

This project reimagines experience design by introducing a novel tactile interaction for post-service feedback — blending the immediacy of physical touchpoints with the adaptability of AI-driven prompts. Guided by core UXR and Product Strategy principles, it explores how emotional reflections can complement structured data to drive stronger, more empathetic product decisions. Rather than replacing traditional metrics, the system strengthens them — helping teams validate assumptions, uncover hidden friction points, and surface early signals of opportunity.

Thank you for visiting!

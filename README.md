# PreventiCare

Application web de prévention santé développée en Python (Flask) dans un contexte académique.

## Objectif

PreventiCare propose une évaluation pédagogique orientée :

- risque cardiovasculaire,
- risque colorectal,
- synthèse patient claire,
- plan d’actions personnalisé.

Le projet s’appuie sur une logique d’éducation thérapeutique et de sensibilisation.

## Contexte de stage

Ce projet a été motivé par mes stages à la Clinique de la Côte d’Opale :

- Stage de 3ème avec le Dr Doleh Wissam : découverte du système digestif, différence entre gastroscopie et coloscopie.
- Août 2025 : échanges avec des patients, observation d’endoscopies en direct, compréhension du lien diagnostic-traitement (maladie de Crohn).
- Février 2026 avec le Dr Fadi Katherin : analyse d’examens et résultats biologiques, importance du diagnostic précoce du cancer du côlon.

## Fonctionnalités

- Calcul IMC + catégorie pondérale
- Calcul WHtR (tour de taille / taille)
- Questionnaire clinique multi-étapes (wizard)
- Scoring cardiovasculaire détaillé
- Module de risque colorectal
- Alertes cliniques automatiques
- Plan d’actions personnalisé
- Historique local (navigateur)
- Fiche récapitulative imprimable
- Export PDF patient

## Stack technique

- Python 3
- Flask
- HTML/CSS/JavaScript
- Jinja2
- xhtml2pdf (export PDF)

## Installation

```bash
cd "/Users/khaledwalid/Documents/New project"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py

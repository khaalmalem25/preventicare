from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from typing import Dict, List

from flask import Flask, Response, render_template, request

app = Flask(__name__)


@dataclass
class AnalyseResultat:
    nom_patient: str
    age: int
    sexe: str
    date_analyse: str
    imc: float
    categorie_imc: str
    whtr: float
    categorie_whtr: str
    score_cardio: int
    niveau_cardio: str
    score_colon: int
    niveau_colon: str
    alertes: List[str]
    details_cardio: List[str]
    details_colon: List[str]
    plan_actions: List[str]
    synthese: str


def to_float(valeur: str) -> float:
    return float(valeur.replace(",", "."))


def calculer_imc(poids_kg: float, taille_cm: float) -> float:
    taille_m = taille_cm / 100
    return poids_kg / (taille_m**2)


def categorie_imc(imc: float) -> str:
    if imc < 18.5:
        return "Insuffisance pondérale"
    if imc < 25:
        return "Corpulence normale"
    if imc < 30:
        return "Surpoids"
    if imc < 35:
        return "Obésité classe I"
    if imc < 40:
        return "Obésité classe II"
    return "Obésité classe III"


def calculer_whtr(tour_taille_cm: float, taille_cm: float) -> float:
    return tour_taille_cm / taille_cm


def categorie_whtr(whtr: float) -> str:
    if whtr < 0.5:
        return "Risque métabolique faible"
    if whtr < 0.6:
        return "Risque métabolique intermédiaire"
    return "Risque métabolique élevé"


def add_points(condition: bool, points: int, libelle: str, details: List[str]) -> int:
    if condition:
        details.append(f"+{points} : {libelle}")
        return points
    return 0


def score_cardio(reponses: Dict[str, str], imc: float, whtr: float) -> tuple[int, List[str], List[str]]:
    score = 0
    details: List[str] = []
    alertes: List[str] = []

    age = int(reponses["age"])
    sexe = reponses["sexe"]

    if (sexe == "homme" and age >= 65) or (sexe == "femme" and age >= 75):
        score += add_points(True, 3, "âge très à risque", details)
    elif (sexe == "homme" and age >= 55) or (sexe == "femme" and age >= 65):
        score += add_points(True, 2, "âge à risque", details)
    elif (sexe == "homme" and age >= 45) or (sexe == "femme" and age >= 55):
        score += add_points(True, 1, "âge intermédiaire", details)

    score += add_points(reponses["tabac"] == "oui", 3, "tabagisme actif", details)
    score += add_points(reponses["hypertension"] == "oui", 3, "hypertension connue", details)
    score += add_points(reponses["diabete"] == "oui", 4, "diabète", details)
    score += add_points(reponses["cholesterol"] == "oui", 2, "cholestérol élevé connu", details)
    score += add_points(
        reponses["antecedents_cardio"] == "oui", 2, "antécédents cardio familiaux précoces", details
    )
    score += add_points(reponses["activite_physique"] == "non", 2, "sédentarité", details)

    alcool = reponses["alcool"]
    if alcool == "excessif":
        score += add_points(True, 2, "alcool excessif", details)
    elif alcool == "modere":
        score += add_points(True, 1, "alcool modéré", details)

    if imc >= 35:
        score += add_points(True, 3, "IMC >= 35", details)
    elif imc >= 30:
        score += add_points(True, 2, "IMC 30-34.9", details)
    elif imc >= 25:
        score += add_points(True, 1, "IMC 25-29.9", details)

    if (sexe == "homme" and to_float(reponses["tour_taille"]) >= 102) or (
        sexe == "femme" and to_float(reponses["tour_taille"]) >= 88
    ):
        score += add_points(True, 2, "obésité abdominale", details)

    if whtr >= 0.6:
        score += add_points(True, 2, "ratio tour de taille/taille élevé", details)
    elif whtr >= 0.5:
        score += add_points(True, 1, "ratio tour de taille/taille intermédiaire", details)

    if reponses["symptomes_cardio"] == "oui":
        score += add_points(True, 5, "symptômes d'alerte cardiovasculaire", details)
        alertes.append("Présence de symptômes cardiovasculaires d'alerte: orientation médicale rapide.")

    if not details:
        details.append("0 : aucun facteur majeur identifié au questionnaire")

    return score, details, alertes


def niveau_cardio(score: int) -> str:
    if score <= 4:
        return "Faible"
    if score <= 8:
        return "Modéré"
    if score <= 13:
        return "Élevé"
    return "Très élevé"


def score_colon(reponses: Dict[str, str]) -> tuple[int, str, List[str], List[str]]:
    score = 0
    details: List[str] = []
    alertes: List[str] = []

    age = int(reponses["age"])
    score += add_points(age >= 60, 3, "âge >= 60 ans", details)
    if age < 60:
        score += add_points(age >= 50, 2, "âge entre 50 et 59 ans", details)

    score += add_points(reponses["antecedents_colon"] == "oui", 3, "antécédents familiaux de cancer colorectal", details)
    score += add_points(reponses["symptomes_digestifs"] == "oui", 3, "troubles digestifs persistants", details)

    if reponses["sang_selles"] == "oui":
        score += add_points(True, 5, "sang dans les selles", details)
        alertes.append("Sang dans les selles déclaré: avis médical prioritaire.")

    depistage = reponses["depistage_colon"]
    if depistage == "jamais":
        score += add_points(True, 3, "pas de dépistage antérieur", details)
    elif depistage == "plus_2_ans":
        score += add_points(True, 2, "dépistage à actualiser", details)

    score += add_points(reponses["fibres"] == "non", 1, "alimentation pauvre en fibres", details)
    score += add_points(reponses["viandes_transformees"] == "oui", 1, "consommation régulière de viandes transformées", details)

    if score <= 3:
        niveau = "Bas"
    elif score <= 7:
        niveau = "Intermédiaire"
    elif score <= 11:
        niveau = "Élevé"
    else:
        niveau = "Très élevé"

    if not details:
        details.append("0 : pas de facteur significatif repéré")

    return score, niveau, details, alertes


def plan_actions(reponses: Dict[str, str], niveau_c: str, niveau_colon_r: str) -> List[str]:
    actions: List[str] = []

    if reponses["tabac"] == "oui":
        actions.append("Plan sevrage tabagique sur 4 à 8 semaines avec accompagnement médical/pharmaceutique.")
    if reponses["activite_physique"] == "non":
        actions.append("Objectif progressif: 150 minutes d'activité physique modérée par semaine.")
    if reponses["fibres"] == "non":
        actions.append("Augmenter les fibres: légumes, fruits, légumineuses, céréales complètes.")
    if reponses["viandes_transformees"] == "oui":
        actions.append("Réduire la fréquence des charcuteries/viandes transformées au minimum.")
    if reponses["hypertension"] == "oui" or reponses["diabete"] == "oui" or reponses["cholesterol"] == "oui":
        actions.append("Suivi trimestriel tension-glycémie-lipides avec le médecin traitant.")

    if niveau_c in {"Élevé", "Très élevé"}:
        actions.append("Programmer un bilan cardiovasculaire médical dans les prochaines semaines.")

    if niveau_colon_r in {"Élevé", "Très élevé"}:
        actions.append("Discuter rapidement du dépistage colorectal (test immunologique/coloscopie selon indication).")

    if not actions:
        actions.append("Maintenir les habitudes protectrices et refaire l'évaluation dans 6 à 12 mois.")

    return actions


def construire_synthese(resultat: AnalyseResultat) -> str:
    return (
        f"IMC {resultat.imc:.1f} ({resultat.categorie_imc}), WHtR {resultat.whtr:.2f} "
        f"({resultat.categorie_whtr}). Risque cardiovasculaire {resultat.niveau_cardio} "
        f"(score {resultat.score_cardio}) et risque colorectal {resultat.niveau_colon} "
        f"(score {resultat.score_colon})."
    )


def analyser_donnees(formulaire: Dict[str, str]) -> AnalyseResultat:
    poids = to_float(formulaire["poids"])
    taille = to_float(formulaire["taille"])
    tour_taille = to_float(formulaire["tour_taille"])

    imc = calculer_imc(poids, taille)
    whtr = calculer_whtr(tour_taille, taille)

    score_c, details_c, alertes_c = score_cardio(formulaire, imc, whtr)
    niveau_c = niveau_cardio(score_c)

    score_colon_r, niveau_colon_r, details_colon_r, alertes_colon = score_colon(formulaire)

    alertes = alertes_c + alertes_colon
    actions = plan_actions(formulaire, niveau_c, niveau_colon_r)

    nom = formulaire["nom_patient"].strip() or "Patient"
    resultat = AnalyseResultat(
        nom_patient=nom,
        age=int(formulaire["age"]),
        sexe=formulaire["sexe"],
        date_analyse=datetime.now().strftime("%d/%m/%Y %H:%M"),
        imc=round(imc, 1),
        categorie_imc=categorie_imc(imc),
        whtr=round(whtr, 2),
        categorie_whtr=categorie_whtr(whtr),
        score_cardio=score_c,
        niveau_cardio=niveau_c,
        score_colon=score_colon_r,
        niveau_colon=niveau_colon_r,
        alertes=alertes,
        details_cardio=details_c,
        details_colon=details_colon_r,
        plan_actions=actions,
        synthese="",
    )
    resultat.synthese = construire_synthese(resultat)
    return resultat


def champs_formulaire() -> List[str]:
    return [
        "nom_patient",
        "age",
        "sexe",
        "poids",
        "taille",
        "tour_taille",
        "tabac",
        "hypertension",
        "diabete",
        "cholesterol",
        "antecedents_cardio",
        "activite_physique",
        "alcool",
        "symptomes_cardio",
        "antecedents_colon",
        "symptomes_digestifs",
        "sang_selles",
        "depistage_colon",
        "fibres",
        "viandes_transformees",
    ]


def collecter_donnees_form(form: Dict[str, str]) -> Dict[str, str]:
    return {champ: form.get(champ, "").strip() for champ in champs_formulaire()}


def valider_donnees(donnees: Dict[str, str]) -> None:
    obligatoires = [c for c in champs_formulaire() if c != "nom_patient"]
    if any(not donnees[c] for c in obligatoires):
        raise ValueError("Formulaire incomplet")

    age = int(donnees["age"])
    poids = to_float(donnees["poids"])
    taille = to_float(donnees["taille"])
    tour_taille = to_float(donnees["tour_taille"])

    if age <= 0 or poids <= 0 or taille <= 0 or tour_taille <= 0:
        raise ValueError("Valeur non valide")


@app.route("/", methods=["GET"])
def index() -> str:
    return render_template("index.html", resultat=None, erreur=None, donnees={})


@app.route("/analyser", methods=["POST"])
def analyser() -> str:
    donnees = collecter_donnees_form(request.form)
    try:
        valider_donnees(donnees)
        resultat = analyser_donnees(donnees)
        return render_template("index.html", resultat=resultat, erreur=None, donnees=donnees)
    except (ValueError, KeyError):
        erreur = "Merci de remplir correctement toutes les données (âge, poids, taille, tour de taille...)."
        return render_template("index.html", resultat=None, erreur=erreur, donnees=donnees)


@app.route("/rapport/imprimable", methods=["POST"])
def rapport_imprimable() -> str:
    donnees = collecter_donnees_form(request.form)
    try:
        valider_donnees(donnees)
        resultat = analyser_donnees(donnees)
        return render_template("report.html", resultat=resultat, export_mode=False)
    except (ValueError, KeyError):
        return render_template("index.html", resultat=None, erreur="Impossible de générer la fiche imprimable.", donnees=donnees)


@app.route("/export/pdf", methods=["POST"])
def export_pdf() -> Response:
    donnees = collecter_donnees_form(request.form)
    try:
        valider_donnees(donnees)
        resultat = analyser_donnees(donnees)
    except (ValueError, KeyError):
        return Response("Données invalides pour export PDF.", status=400, mimetype="text/plain")

    try:
        from xhtml2pdf import pisa
    except Exception:
        return Response(
            "La bibliothèque xhtml2pdf est absente. Lancez: pip install -r requirements.txt",
            status=500,
            mimetype="text/plain",
        )

    html = render_template("report.html", resultat=resultat, export_mode=True)
    buffer = BytesIO()
    pdf_status = pisa.CreatePDF(src=html, dest=buffer, encoding="utf-8")
    if pdf_status.err:
        return Response("Erreur pendant la génération du PDF.", status=500, mimetype="text/plain")

    nom_fichier = f"fiche_patient_{resultat.nom_patient.replace(' ', '_')}.pdf"
    buffer.seek(0)

    return Response(
        buffer.getvalue(),
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={nom_fichier}"},
    )


if __name__ == "__main__":
    app.run(debug=True)

"""Online skill catalog — searchable by agents at runtime.

Each entry includes a minimal but functional SKILL.md template. When an agent
installs a skill via ``skill_manage(action="install", name="...")``, the
template is written to ``skills/custom/{name}/SKILL.md`` and becomes
immediately available.
"""

from __future__ import annotations

from dataclasses import dataclass

# ── Catalog entries ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SkillCatalogEntry:
    """A skill available for installation from the online catalog."""

    name: str
    description: str
    icon: str
    category: str  # research, creation, analysis, dev, design
    content: str  # SKILL.md content


SKILL_CATALOG: list[SkillCatalogEntry] = [
    SkillCatalogEntry(
        name="deep-research",
        description="Recherche web multi-angle avec vérification adverse. Pour toute question nécessitant des sources fiables.",
        icon="🔍",
        category="research",
        content="""---
name: deep-research
description: Recherche web multi-angle avec vérification adverse.
allowed-tools: [web_search, web_fetch, read_file, write_file]
---

# Deep Research

## Vue d'ensemble
Recherche approfondie multi-angle avec vérification croisée des sources.

## Quand l'utiliser
- Questions nécessitant des sources fiables et multiples
- Sujets complexes demandant une analyse contradictoire
- Recherche documentaire structurée

## Instructions
1. Identifier les angles de recherche complémentaires
2. Pour chaque angle, chercher au moins 3 sources indépendantes
3. Croiser les informations et identifier les contradictions
4. Synthétiser avec niveau de confiance par affirmation
5. Présenter les résultats avec sources citées
""",
    ),
    SkillCatalogEntry(
        name="academic-paper-review",
        description="Révision académique structurée : méthodes, résultats, biais, qualité des citations.",
        icon="📄",
        category="research",
        content="""---
name: academic-paper-review
description: Révision académique structurée d'articles scientifiques.
allowed-tools: [read_file, write_file, web_search]
---

# Academic Paper Review

## Vue d'ensemble
Révision structurée d'articles académiques selon les standards de peer review.

## Quand l'utiliser
- Évaluation d'un article scientifique
- Préparation d'une revue de littérature
- Analyse critique de méthodologies

## Instructions
1. Résumer l'article : problématique, méthode, résultats, conclusion
2. Évaluer la méthodologie (validité interne/externe)
3. Identifier les biais potentiels
4. Vérifier la qualité et pertinence des citations
5. Produire un rapport structuré avec recommandations
""",
    ),
    SkillCatalogEntry(
        name="systematic-literature-review",
        description="Revue systématique de littérature : recherche exhaustive, synthèse, méta-analyse.",
        icon="📚",
        category="research",
        content="""---
name: systematic-literature-review
description: Revue systématique de littérature avec synthèse et méta-analyse.
allowed-tools: [web_search, web_fetch, write_file, read_file]
---

# Systematic Literature Review

## Vue d'ensemble
Revue systématique suivant la méthodologie PRISMA : recherche, sélection, extraction, synthèse.

## Quand l'utiliser
- État de l'art sur un sujet
- Méta-analyse quantitative ou qualitative
- Identification de gaps dans la littérature

## Instructions
1. Définir la question de recherche (PICO/PICOS)
2. Établir les critères d'inclusion/exclusion
3. Rechercher sur multiples bases de données avec mots-clés
4. Sélectionner les études (screening par titre/résumé puis texte intégral)
5. Extraire les données dans une matrice structurée
6. Synthétiser et évaluer la qualité des preuves (GRADE)
7. Rédiger selon le format PRISMA
""",
    ),
    SkillCatalogEntry(
        name="github-deep-research",
        description="Exploration approfondie de repos GitHub : structure, code, historiques, PRs.",
        icon="🐙",
        category="research",
        content="""---
name: github-deep-research
description: Exploration approfondie de dépôts GitHub.
allowed-tools: [read_file, web_search, web_fetch, write_file]
---

# GitHub Deep Research

## Vue d'ensemble
Analyse structurée de dépôts GitHub : architecture, qualité du code, activité, communauté.

## Quand l'utiliser
- Évaluation d'une bibliothèque open-source
- Audit de code et de sécurité
- Analyse de l'activité et de la communauté d'un projet

## Instructions
1. Analyser la structure du dépôt (arborescence, langages, taille)
2. Examiner les métriques : stars, forks, contributeurs, fréquence de commits
3. Lire les issues ouvertes et PRs récentes pour évaluer la réactivité
4. Analyser la qualité du code (tests, documentation, CI/CD)
5. Vérifier les dépendances et leur fraîcheur
6. Produire un rapport avec score global et recommandations
""",
    ),
    SkillCatalogEntry(
        name="data-analysis",
        description="Analyse de données Excel/CSV avec DuckDB : statistiques, SQL, visualisations.",
        icon="📊",
        category="analysis",
        content="""---
name: data-analysis
description: Analyse de données avec requêtes SQL et visualisations.
allowed-tools: [bash, read_file, write_file, present_files]
---

# Data Analysis

## Vue d'ensemble
Analyse de données tabulaires (CSV, Excel, Parquet) avec DuckDB/SQL et visualisations.

## Quand l'utiliser
- Exploration et nettoyage de données
- Analyses statistiques descriptives
- Création de visualisations et rapports

## Instructions
1. Charger et inspecter les données (head, describe, info)
2. Nettoyer : valeurs manquantes, doublons, types, outliers
3. Explorer : distributions, corrélations, segmentations
4. Analyser : requêtes SQL ciblées, tests statistiques
5. Visualiser : graphiques pertinents (distribution, tendance, comparaison)
6. Documenter les conclusions avec recommandations
""",
    ),
    SkillCatalogEntry(
        name="consulting-analysis",
        description="Cadre d'analyse consulting : structuration, hypothèses, recommandations, slides.",
        icon="📈",
        category="analysis",
        content="""---
name: consulting-analysis
description: Cadre d'analyse de type consulting stratégique.
allowed-tools: [write_file, read_file, web_search]
---

# Consulting Analysis

## Vue d'ensemble
Analyse structurée de problèmes business selon les standards du conseil en stratégie.

## Quand l'utiliser
- Analyse de marché ou de concurrence
- Due diligence stratégique
- Plan de transformation ou d'amélioration

## Instructions
1. Structurer le problème (issue tree, MECE)
2. Formuler des hypothèses testables
3. Collecter et analyser les données pertinentes
4. Tester les hypothèses et affiner
5. Développer des recommandations actionnables
6. Structurer la restitution (executive summary, slide deck)
""",
    ),
    SkillCatalogEntry(
        name="chart-visualization",
        description="Création de graphiques et visualisations de données interactives.",
        icon="📉",
        category="creation",
        content="""---
name: chart-visualization
description: Création de graphiques et visualisations de données.
allowed-tools: [bash, write_file, present_files, read_file]
---

# Chart Visualization

## Vue d'ensemble
Création de visualisations de données claires et impactantes avec matplotlib/plotly/echarts.

## Quand l'utiliser
- Visualisation de données quantitatives
- Création de dashboards et rapports
- Communication de tendances et insights

## Instructions
1. Identifier le type de données et le message à communiquer
2. Choisir le type de graphique approprié (bar, line, scatter, pie, heatmap...)
3. Préparer les données (agrégation, tri, format)
4. Créer le graphique avec titres, légendes, annotations
5. Appliquer une palette de couleurs cohérente et accessible
6. Exporter en PNG/SVG/HTML interactif
""",
    ),
    SkillCatalogEntry(
        name="image-generation",
        description="Génération et édition d'images via IA : prompts détaillés, styles, itérations.",
        icon="🎨",
        category="creation",
        content="""---
name: image-generation
description: Génération et édition d'images assistée par IA.
allowed-tools: [write_file, read_file, present_files]
---

# Image Generation

## Vue d'ensemble
Crédation d'images via des modèles de génération IA avec prompts optimisés.

## Quand l'utiliser
- Création d'illustrations, logos, icônes
- Design conceptuel et moodboards
- Retouche et variation d'images existantes

## Instructions
1. Définir le brief visuel : sujet, style, composition, ambiance
2. Rédiger un prompt détaillé (sujet, style, éclairage, couleur, format)
3. Itérer : générer, évaluer, raffiner le prompt
4. Varier les styles pour explorer les possibilités
5. Sélectionner et justifier le meilleur résultat
""",
    ),
    SkillCatalogEntry(
        name="frontend-design",
        description="Design d'interfaces web : composants, mise en page, animations, accessibilité.",
        icon="🖌️",
        category="design",
        content="""---
name: frontend-design
description: Design et implémentation d'interfaces web modernes.
allowed-tools: [write_file, read_file, bash, present_files]
---

# Frontend Design

## Vue d'ensemble
Conception et réalisation d'interfaces web avec composants réutilisables et design system.

## Quand l'utiliser
- Création de pages web ou applications
- Refonte d'interface utilisateur
- Création de composants UI réutilisables

## Instructions
1. Définir la direction visuelle : style, palette, typographie
2. Structurer la mise en page (hiérarchie, grille, responsive)
3. Créer les composants (boutons, cartes, formulaires, navigation)
4. Ajouter les interactions (hover, focus, transitions, animations)
5. Vérifier l'accessibilité (contraste, keyboard nav, aria)
6. Tester sur les breakpoints (mobile, tablette, desktop)
""",
    ),
    SkillCatalogEntry(
        name="web-design-guidelines",
        description="Directives de design web : typographie, couleurs, responsive, accessibilité.",
        icon="🎯",
        category="design",
        content="""---
name: web-design-guidelines
description: Guide de référence pour les bonnes pratiques de design web.
allowed-tools: [read_file, write_file]
---

# Web Design Guidelines

## Vue d'ensemble
Référence de bonnes pratiques pour le design web : accessibilité, performance, UX.

## Quand l'utiliser
- Audit de design d'un site existant
- Définition de guidelines pour une équipe
- Validation d'une interface avant mise en production

## Instructions
1. Vérifier la hiérarchie visuelle et la clarté du message
2. Contrôler la typographie (lisibilité, échelle, contraste)
3. Valider la palette de couleurs (harmonie, accessibilité WCAG AA)
4. Tester la navigation et le flux utilisateur
5. Vérifier la performance (Core Web Vitals, images, fonts)
6. Produire un rapport avec recommandations priorisées
""",
    ),
    SkillCatalogEntry(
        name="code-documentation",
        description="Documentation de code automatique : JSDoc, README, diagrammes d'architecture.",
        icon="📝",
        category="dev",
        content="""---
name: code-documentation
description: Génération et mise à jour de documentation technique.
allowed-tools: [read_file, write_file, bash]
---

# Code Documentation

## Vue d'ensemble
Documentation automatique de code source : docstrings, README, diagrammes d'architecture.

## Quand l'utiliser
- Documenter un nouveau module ou projet
- Mettre à jour une documentation obsolète
- Générer des diagrammes d'architecture

## Instructions
1. Analyser la structure du code (modules, classes, fonctions publiques)
2. Générer les docstrings (JSDoc, Python docstrings, etc.)
3. Rédiger ou mettre à jour le README.md
4. Créer des diagrammes d'architecture (Mermaid)
5. Ajouter des exemples d'utilisation
6. Vérifier la cohérence et l'exhaustivité
""",
    ),
    SkillCatalogEntry(
        name="skill-creator",
        description="Assistant de création de skills DeerFlow : structure, métadonnées, bonnes pratiques.",
        icon="🛠️",
        category="dev",
        content="""---
name: skill-creator
description: Guide pour créer des skills DeerFlow efficaces.
allowed-tools: [write_file, read_file]
---

# Skill Creator

## Vue d'ensemble
Assistant de création de skills DeerFlow : structure optimale, métadonnées, bonnes pratiques.

## Quand l'utiliser
- Créer un nouveau skill personnalisé
- Améliorer un skill existant
- Auditer la qualité d'un skill

## Instructions
1. Définir le scope précis du skill (quoi, quand, comment)
2. Rédiger le frontmatter YAML (name, description, allowed-tools)
3. Structurer le corps : Vue d'ensemble, Quand l'utiliser, Instructions
4. Lister les outils nécessaires dans allowed-tools
5. Ajouter des exemples concrets d'utilisation
6. Tester le skill sur un cas réel et itérer
""",
    ),
    SkillCatalogEntry(
        name="ppt-generation",
        description="Génération de présentations PowerPoint structurées à partir de contenu.",
        icon="🖼️",
        category="creation",
        content="""---
name: ppt-generation
description: Création de présentations PowerPoint professionnelles.
allowed-tools: [bash, write_file, read_file, present_files]
---

# PPT Generation

## Vue d'ensemble
Génération de présentations PowerPoint structurées avec python-pptx.

## Quand l'utiliser
- Création de slides pour une réunion
- Rapport visuel à présenter
- Pitch deck ou présentation commerciale

## Instructions
1. Structurer le contenu : titre, agenda, sections, conclusion
2. Définir le design : template, couleurs, polices
3. Créer les slides une par une (titre, contenu, visuels)
4. Ajouter des graphiques ou tableaux si pertinent
5. Vérifier la cohérence visuelle et le flux narratif
6. Exporter le fichier .pptx
""",
    ),
    SkillCatalogEntry(
        name="newsletter-generation",
        description="Création de newsletters : curation, rédaction, mise en page, ton adapté.",
        icon="📧",
        category="creation",
        content="""---
name: newsletter-generation
description: Création de newsletters professionnelles.
allowed-tools: [web_search, write_file, read_file]
---

# Newsletter Generation

## Vue d'ensemble
Création de newsletters : curation de contenu, rédaction, mise en forme.

## Quand l'utiliser
- Newsletter régulière (hebdo, mensuelle)
- Campagne d'email marketing
- Bulletin interne d'entreprise

## Instructions
1. Définir le thème, le public cible et le ton
2. Curer le contenu : articles, actualités, ressources
3. Rédiger les sections : édito, articles, calls-to-action
4. Structurer pour la lisibilité (titres, sous-titres, listes)
5. Adapter le format selon le support (email, web, PDF)
6. Relire et optimiser les lignes de sujet
""",
    ),
    SkillCatalogEntry(
        name="podcast-generation",
        description="Génération de scripts de podcast : structure, timing, dialogues, narration.",
        icon="🎙️",
        category="creation",
        content="""---
name: podcast-generation
description: Création de scripts de podcast structurés.
allowed-tools: [web_search, write_file, read_file]
---

# Podcast Generation

## Vue d'ensemble
Écriture de scripts de podcast : structure narrative, dialogues, timing.

## Quand l'utiliser
- Préparation d'un épisode de podcast
- Script pour contenu audio éducatif
- Narration audio pour storytelling

## Instructions
1. Définir le format : interview, solo, panel, narratif
2. Structurer l'épisode : intro, segments, conclusion, CTA
3. Rédiger le script avec indications de timing
4. Ajouter des notes de production (musique, sound design)
5. Préparer les questions ou points de discussion
6. Estimer la durée et ajuster le contenu
""",
    ),
    SkillCatalogEntry(
        name="video-generation",
        description="Création de scripts vidéo : storyboard, narration, timing, visuels.",
        icon="🎬",
        category="creation",
        content="""---
name: video-generation
description: Création de scripts vidéo et storyboards.
allowed-tools: [write_file, read_file, web_search]
---

# Video Generation

## Vue d'ensemble
Écriture de scripts vidéo avec storyboard et indications visuelles.

## Quand l'utiliser
- Script pour vidéo YouTube ou formation
- Storyboard pour production vidéo
- Contenu pour réseaux sociaux (TikTok, Reels, Shorts)

## Instructions
1. Définir le format et la durée cible
2. Structurer le script : hook, corps, call-to-action
3. Rédiger la narration avec indications de rythme
4. Créer le storyboard : descriptions visuelles par scène
5. Ajouter des notes de production (musique, texte à l'écran)
6. Adapter le ton à la plateforme cible
""",
    ),
    SkillCatalogEntry(
        name="music-generation",
        description="Composition musicale assistée : styles, structures, instruments, paroles.",
        icon="🎵",
        category="creation",
        content="""---
name: music-generation
description: Composition musicale assistée et analyse.
allowed-tools: [write_file, read_file, web_search]
---

# Music Generation

## Vue d'ensemble
Aide à la composition musicale : structures, paroles, analyse harmonique.

## Quand l'utiliser
- Écriture de paroles de chanson
- Analyse de structure musicale
- Idéation créative pour composition

## Instructions
1. Définir le style musical et les références
2. Structurer le morceau (couplet, refrain, pont, outro)
3. Écrire les paroles avec schéma de rimes
4. Suggérer une progression d'accords
5. Proposer des idées d'arrangement et d'instrumentation
6. Itérer sur les versions et affiner
""",
    ),
    SkillCatalogEntry(
        name="surprise-me",
        description="Mode découverte : suggestion aléatoire de skills selon le contexte.",
        icon="🎲",
        category="creation",
        content="""---
name: surprise-me
description: Découverte aléatoire de skills et fonctionnalités.
allowed-tools: [read_file, write_file]
---

# Surprise Me

## Vue d'ensemble
Mode découverte : explore de nouvelles capacités et approches créatives.

## Quand l'utiliser
- Explorer des possibilités inattendues
- Sortir des sentiers battus
- Trouver l'inspiration

## Instructions
1. Analyser le contexte de la conversation
2. Proposer une approche créative ou un angle inattendu
3. Suggérer des skills ou outils pertinents que l'utilisateur ne connaît peut-être pas
4. Expliquer pourquoi cette approche pourrait être intéressante
5. Laisser l'utilisateur choisir d'explorer ou non
""",
    ),
]

# ── Lookup helpers ───────────────────────────────────────────────────────────


def search_catalog(query: str = "", category: str | None = None) -> list[SkillCatalogEntry]:
    """Search the skill catalog by name, description, or category.

    Args:
        query: Free-text search across name and description.
        category: Optional category filter (research, creation, analysis, dev, design).

    Returns:
        Matching catalog entries, sorted by relevance.
    """
    q = query.lower().strip()
    results = SKILL_CATALOG

    if category:
        results = [e for e in results if e.category == category]

    if q:
        scored: list[tuple[int, SkillCatalogEntry]] = []
        for entry in results:
            score = 0
            if q in entry.name.lower():
                score += 3
            if q in entry.description.lower():
                score += 1
            if score > 0:
                scored.append((score, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored]

    return list(results)


def get_catalog_entry(name: str) -> SkillCatalogEntry | None:
    """Get a single catalog entry by exact name match."""
    for entry in SKILL_CATALOG:
        if entry.name == name:
            return entry
    return None


def get_catalog_names() -> list[str]:
    """Return all catalog skill names."""
    return [e.name for e in SKILL_CATALOG]

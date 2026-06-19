---
name: superpowers-context-optimization
description: Optimise la consommation de tokens, compacte le contexte au seuil de 45%, nettoie entre sessions, et maintient un memo projet automatique. Use when the session context grows large, when switching projects, or when ending a session. Trigger on "compacte le contexte", "optimise les tokens", "nettoie la session", "memo projet", "fin de session".
---

# Context Optimization (Superpowers)

## Overview

Gère le cycle de vie du contexte de session agentique : surveillance du remplissage, compaction automatique au seuil de 45%, nettoyage inter-session, et persistance de l'état projet via un memo automatique.

## Core Principle

**Un contexte saturé dégrade les décisions.** Ce qui n'est pas compacté sera oublié. Ce qui n'est pas sauvegardé sera perdu.

## Les 4 piliers

### 1. Surveillance et compaction automatique (seuil 45%)

**Déclenchement :** Quand le contexte de session atteint 45% de sa capacité totale. Le seuil de 45% est calculé sur la taille max du contexte supporté par le modèle actif.

**Méthode de compaction :**
- Conserver : décisions prises, faits établis, état courant du projet, variables d'environnement
- Résumer fortement : historique de debugging, explorations abandonnées, erreurs résolues
- Supprimer : répétitions, reformulations, commandes dont la sortie n'a pas influencé les décisions
- Format de sortie : section `## Session Compactée` avec sous-sections `Décisions`, `Faits`, `État`, `Erreurs résolues`

**Signal au moment du compact :**
```
⚠️ Contexte à 45% — compaction automatique déclenchée.
Résumé de ce qui est conservé : [X décisions, Y faits, Z éléments d'état]
Ce qui est supprimé : [résumé en une phrase]
```

### 2. Nettoyage inter-session (clear)

**Déclenchement :** Changement explicite de projet, ou commande `clear session`.

**Procédure :**
1. Sauvegarder le memo projet AVANT de clearer (voir pilier 3)
2. Signaler ce qui va être perdu
3. Demander confirmation
4. Vider le contexte — ne garder que le SOUL et les skills essentiels
5. Confirmer : `✅ Session nettoyée. Memo sauvegardé. Contexte réinitialisé.`

### 3. Memo automatique de projet

**Déclenchement :** Fin de session, changement de projet, ou commande explicite `memo projet`.

**Contenu du memo (`MEMO.md` dans le dossier du projet) :**
```markdown
# Memo Projet — [NOM_DU_PROJET]
Dernière mise à jour : [DATE]

## État actuel
- [Ce qui est en cours, bloqué, ou terminé]

## Décisions clés
- [Décision 1] — [date] — [raison courte]
- [Décision 2] — [date] — [raison courte]

## Configuration active
- Environnement : [venv path, Python version]
- Services : [Docker, DB, etc.]
- Variables critiques : [sans secrets]

## Fichiers modifiés récemment
- [fichier] — [dernière modification]

## Prochaine session
- [Ce qu'il faut faire en premier]
```

**Règle :** Le memo est réinjecté automatiquement en début de session suivante via le `<memory>` system prompt.

### 4. Optimisation continue des tokens

**Principes appliqués en permanence :**
- Réponse directe d'abord (1-2 phrases), développement seulement si nécessaire
- Pas de reformulation de la question posée
- Pas de récapitulatif post-action
- Distinguer fait établi / hypothèse / opinion — mais sans verbosité
- Pour les recherches : citations inline, pas de blocs de texte redondants

**Vérification périodique (tous les ~20 échanges) :**
- Ai-je répété quelque chose déjà dit plus tôt dans la session ?
- Puis-je répondre en 2 phrases au lieu de 5 ?
- Un tableau résumerait-il mieux qu'un paragraphe ?

## Workflow complet

```
Début de session
  → Charger MEMO.md si existant
  → Injecter dans le contexte initial
  ↓
Pendant la session
  → Optimisation continue des tokens (pilier 4)
  → Surveillance du taux de remplissage
  → Si 45% atteint → Compaction (pilier 1)
  ↓
Changement de projet / fin de session
  → Sauvegarder MEMO.md (pilier 3)
  → Nettoyer le contexte (pilier 2)
```

## Anti-patterns

- ❌ Laisser le contexte saturer sans compacter — les décisions se dégradent
- ❌ Clear sans sauvegarder le memo — perte d'état irrécupérable
- ❌ Memo trop verbeux — un memo n'est pas un journal, c'est un état
- ❌ Compacter trop tôt (avant 45%) — gaspille du temps de traitement pour peu de gain

## Announcement

Compaction : "⚠️ Contexte à 45%, compaction en cours..."
Clear : "🧹 Nettoyage de session. Sauvegarde du memo d'abord."
Memo : "📝 Memo projet mis à jour — prêt pour la prochaine session."

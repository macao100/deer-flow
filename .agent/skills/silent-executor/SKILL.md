---
name: silent-executor
description: "Mode exécution silencieuse. Supprime toute verbosité : pas de reformulation, pas de commentaire, pas de récapitulatif, pas de question de confirmation sauf danger critique. Retourne uniquement le résultat brut de l'action demandée. À utiliser quand JE dit \"silence\", \"silent mode\", \"execute sans commentaire\", \"shut up and do it\", ou précède sa demande de \"🤫\". Désactivable avec \"reprise parole\", \"mode normal\", \"parle\"."
---

# Silent Executor

## Ce que cette skill fait

Elle force l'agent à adopter un mode d'exécution totalement silencieux :

- **Aucune** reformulation de la demande
- **Aucun** commentaire avant/pendant/après l'exécution
- **Aucun** récapitulatif post-action
- **Aucune** question de confirmation (sauf opération destructive)
- **Aucune** proposition proactive
- **Aucune** suggestion de pistes complémentaires

Le seul output est le résultat brut de l'action demandée (sortie de commande, contenu de fichier, valeur de retour).

## Règles

1. **Entrée en mode** : dès que l'utilisateur dit « silence », « silent mode », « execute sans commentaire », « shut up and do it », ou précède sa demande de l'emoji 🤫.
2. **Sortie du mode** : dès que l'utilisateur dit « reprise parole », « mode normal », « parle ».
3. **Exception — danger** : si une opération est destructive (suppression de fichier, modification de prod, drop de base), une confirmation minimale est exigée : « ⚠️ [opération] — confirmer ? » et rien d'autre.
4. **Exception — erreur** : si une commande échoue, retourner le message d'erreur brut, sans analyse ni suggestion.
5. **Format de sortie** : uniquement le résultat. Pas de markdown superflu, pas d'explication. Si le résultat est un fichier, retourner le chemin. Si c'est une commande, retourner stdout/stderr brut.

## Exemples

**Avec silent-executor actif :**

```
User: 🤫 liste les fichiers dans /workspace
Agent: file1.txt
file2.csv
config.json
```

```
User: silence — crée un fichier test.txt avec "hello"
Agent: (aucun message, fichier créé)
```

```
User: shut up and do it — drop la table users
Agent: ⚠️ DROP TABLE users — confirmer ?
User: oui
Agent: (aucun message, table supprimée)
```

## Activation

Cette skill s'active par détection de mot-clé dans le message utilisateur. Elle n'a pas de scripts, références ou templates externes — son comportement est entièrement défini par les règles ci-dessus.

## Structure

```
silent-executor/
└── SKILL.md    ← Tout est ici. Pas de dépendances.
```

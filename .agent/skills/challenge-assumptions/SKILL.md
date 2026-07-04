---
name: challenge-assumptions
description: "Force l'agent à lister et challenger ses hypothèses implicites avant d'exécuter une tâche. Activé par /challenge ou \"challenge tes hypothèses\"."
---

# Challenge Assumptions

## Ce que cette skill fait

Avant d'exécuter une tâche, l'agent doit explicitement lister et questionner ses hypothèses implicites. Cette skill force un moment de recul critique qui évite les erreurs par précipitation.

## Règles

1. **Déclenchement** : quand l'utilisateur tape `/challenge` ou dit « challenge tes hypothèses », « qu'est-ce que tu supposes ? », « vérifie tes prémisses ».
2. **Processus en 3 étapes** :
   - **Lister** : énumérer 3 hypothèses implicites que l'agent fait sur la tâche
   - **Questionner** : pour chaque hypothèse, indiquer ce qui la confirmerait ET ce qui l'invaliderait
   - **Décider** : confirmer quelles hypothèses sont fiables, lesquelles sont fragiles, et ajuster le plan en conséquence
3. **Format de sortie** :
   ```
   🔍 Hypothèses identifiées :
   1. [hypothèse] — ✅ fiable car [raison] / ⚠️ fragile car [raison]
   2. ...
   
   ▶️ Plan ajusté : [action suivante]
   ```
4. **Ne pas bloquer** : si après 3 hypothèses listées aucune n'est fragile, exécuter normalement. Le but est la vigilance, pas la paralysie.

## Exemple

```
User: /challenge — refactor le système d'auth
Agent:
🔍 Hypothèses identifiées :
1. Le système actuel utilise JWT — ✅ fiable car config.yaml:45 mentionne pyjwt
2. Les tests d'auth couvrent tous les flux — ⚠️ fragile car pas vérifié dans test_auth.py
3. Le refactoring ne casse pas l'API Gateway — ⚠️ fragile car le routeur /api/auth est couplé

▶️ Plan ajusté : lire test_auth.py d'abord, puis cartographier les dépendances du routeur /api/auth avant de modifier.
```
